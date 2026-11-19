//! Эфемерные сигналы для визуальных реакций (ADR-0055).
use super::LABEL;
use std::{collections::HashMap, ffi::OsString, fs, path::Path, thread, time::Duration};
use tauri::{AppHandle, Emitter, Manager};
use windows_sys::Win32::UI::Input::KeyboardAndMouse::{
    GetAsyncKeyState, VK_CONTROL, VK_LWIN, VK_MENU, VK_RWIN, VK_SHIFT,
};
use windows_sys::Win32::UI::WindowsAndMessaging::IsWindow;

#[link(name = "user32")]
extern "system" {
    fn GetClipboardSequenceNumber() -> u32;
    fn IsClipboardFormatAvailable(format: u32) -> i32;
}

const PERIOD: Duration = Duration::from_secs(2);
const MAX_FILES: usize = 512;
const UNICODE_TEXT: u32 = 13;
const BITMAP: u32 = 2;
const DIB: u32 = 8;
const DIB_V5: u32 = 17;
type Files = HashMap<OsString, u64>;

#[derive(Clone, serde::Serialize)]
struct Event {
    kind: &'static str,
    size: u64,
}

fn emit(app: &AppHandle, kind: &'static str, size: u64) {
    let _ = app.emit_to(LABEL, "companion-desktop-event", Event { kind, size });
}

fn files(dir: &Path) -> Option<Files> {
    let mut entries = Files::new();
    let listing = match fs::read_dir(dir) {
        Ok(listing) => listing,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Some(entries),
        Err(_) => return None,
    };
    for (index, entry) in listing.enumerate() {
        if index >= MAX_FILES {
            return None;
        }
        let entry = entry.ok()?;
        if entry.file_type().ok()?.is_file() {
            entries.insert(entry.file_name(), entry.metadata().ok()?.len());
        }
    }
    Some(entries)
}

#[derive(Default)]
struct Downloads {
    last: Option<Files>,
    fresh: Files,
}

impl Downloads {
    fn sample(&mut self, next: Option<Files>) -> Option<u64> {
        let mut growth = None;
        if let (Some(previous), Some(current)) = (&self.last, &next) {
            self.fresh.retain(|name, _| current.contains_key(name));
            for (name, &size) in current {
                if !previous.contains_key(name) {
                    self.fresh.insert(name.clone(), size);
                } else if self.fresh.get(name).is_some_and(|&first| size > first) {
                    growth = Some(growth.unwrap_or(0).max(size));
                    self.fresh.remove(name);
                }
            }
        } else {
            self.fresh.clear();
        }
        self.last = next;
        growth
    }
}

/// Only two shortcut states, without a keyboard hook, text capture or input interception.
#[derive(Default)]
pub(super) struct Actions {
    paste_down: bool,
    desktop_down: bool,
    desktop_check: Option<std::time::Instant>,
    seen: std::collections::HashSet<isize>,
}

impl Actions {
    pub(super) fn shortcuts(&mut self, app: &AppHandle) {
        let down = |key: u16| unsafe { GetAsyncKeyState(i32::from(key)) < 0 };
        let win = down(VK_LWIN) || down(VK_RWIN);
        let ctrl = down(VK_CONTROL);
        let plain = !down(VK_MENU) && !down(VK_SHIFT);
        let paste = plain && !win && ctrl && down(b'V'.into());
        let desktop = plain && win && !ctrl && down(b'D'.into());
        if paste && !self.paste_down && unsafe { IsClipboardFormatAvailable(UNICODE_TEXT) } != 0 {
            emit(app, "paste", 0);
        }
        if desktop && !self.desktop_down {
            self.desktop_check = Some(std::time::Instant::now());
        }
        if self
            .desktop_check
            .is_some_and(|start| start.elapsed() >= Duration::from_millis(250))
        {
            self.desktop_check = None;
            if crate::desktop::desktop_foreground() {
                emit(app, "desktop", 0);
            }
        }
        self.paste_down = paste;
        self.desktop_down = desktop;
    }

    pub(super) fn windows(&mut self, app: &AppHandle, foreground: Option<isize>) {
        self.seen.extend(foreground);
        self.seen.retain(|&id| {
            let exists = unsafe { IsWindow(id as _) } != 0;
            if !exists {
                emit(app, "close", 0);
            }
            exists
        });
    }
}
#[derive(Default)]
struct Watch {
    clip: Option<u32>,
    downloads: Downloads,
    shots: Option<Files>,
}

impl Watch {
    fn clipboard(&mut self, app: &AppHandle) {
        // SAFETY: ни открытия буфера, ни чтения данных; только поколение и доступность формата.
        let seq = unsafe { GetClipboardSequenceNumber() };
        if seq != 0
            && self.clip.replace(seq).is_some_and(|last| last != seq)
            && unsafe { IsClipboardFormatAvailable(UNICODE_TEXT) } != 0
            && ![BITMAP, DIB, DIB_V5]
                .iter()
                .any(|&kind| unsafe { IsClipboardFormatAvailable(kind) } != 0)
        {
            emit(app, "copy", 0);
        }
    }
}

pub(super) fn watch(app: AppHandle) {
    let downloads = app.path().download_dir().ok();
    let shots = app.path().picture_dir().ok().map(|p| p.join("Screenshots"));
    let mut watch = Watch::default();
    let mut download_stamp = None;
    let mut shots_stamp = None;
    loop {
        thread::sleep(PERIOD);
        if !super::visible(&app) {
            watch = Watch::default();
            download_stamp = None;
            shots_stamp = None;
            continue;
        }

        watch.clipboard(&app);
        if let Some(dir) = downloads.as_deref() {
            let stamp = fs::metadata(dir).and_then(|m| m.modified()).ok();
            let growth = if stamp != download_stamp {
                download_stamp = stamp;
                watch.downloads.sample(files(dir))
            } else {
                let mut growth = None;
                watch.downloads.fresh.retain(|name, first| {
                    let Ok(meta) = dir.join(name).symlink_metadata() else {
                        return false;
                    };
                    if !meta.is_file() {
                        return false;
                    }
                    if meta.len() <= *first {
                        return true;
                    }
                    growth = Some(growth.unwrap_or(0u64).max(meta.len()));
                    false
                });
                growth
            };
            if let Some(size) = growth {
                emit(&app, "download", size);
            }
        }
        let stamp = shots
            .as_deref()
            .and_then(|dir| fs::metadata(dir).and_then(|m| m.modified()).ok());
        if stamp == shots_stamp && watch.shots.is_some() {
            continue;
        }
        shots_stamp = stamp;
        let next = shots.as_deref().and_then(files);
        if let (Some(old), Some(current)) = (&watch.shots, &next) {
            if current.keys().any(|n| {
                !old.contains_key(n)
                    && Path::new(n)
                        .extension()
                        .is_some_and(|v| v.eq_ignore_ascii_case("png"))
            }) {
                emit(&app, "screenshot", 0);
            }
        }
        watch.shots = next;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample(entries: &[(&str, u64)]) -> Option<Files> {
        Some(
            entries
                .iter()
                .map(|(n, s)| (OsString::from(n), *s))
                .collect(),
        )
    }

    #[test]
    fn new_download_must_grow_after_discovery_and_only_fires_once() {
        let mut watch = Downloads::default();
        assert_eq!(watch.sample(sample(&[("old", 8)])), None);
        assert_eq!(watch.sample(sample(&[("old", 16), ("part", 4)])), None);
        assert_eq!(watch.sample(sample(&[("part", 20)])), Some(20));
        assert_eq!(watch.sample(sample(&[("part", 29)])), None);
        assert_eq!(watch.sample(None), None);
        assert_eq!(watch.sample(sample(&[("part", 42)])), None);
    }
}
