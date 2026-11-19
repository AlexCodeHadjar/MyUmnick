use serde::{Deserialize, Serialize};

#[derive(Deserialize, Serialize)]
pub struct Keepsake {
    name: String,
    icon: String,
}

/// Recent shell links supply display metadata. No target is opened or launched.
#[tauri::command]
pub async fn companion_recent(window: tauri::WebviewWindow) -> Option<Keepsake> {
    if window.label() != crate::companion::LABEL {
        return None;
    }
    tauri::async_runtime::spawn_blocking(read_recent)
        .await
        .ok()
        .flatten()
}

#[cfg(windows)]
fn read_recent() -> Option<Keepsake> {
    use std::os::windows::process::CommandExt;
    // Чтение метаданных не должно показывать консоль поверх спутника.
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    let output = std::process::Command::new("powershell.exe")
        .args([
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            include_str!("recent.ps1"),
        ])
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .ok()?;
    if !output.status.success() || output.stdout.len() > 64000 {
        return None;
    }
    let raw = std::str::from_utf8(&output.stdout).ok()?.trim();
    let (name, icon) = raw.split_once('\n')?;
    Some(Keepsake {
        name: name.trim().chars().take(160).collect(),
        icon: icon.trim().into(),
    })
}
#[cfg(not(windows))]
fn read_recent() -> Option<Keepsake> {
    None
}
