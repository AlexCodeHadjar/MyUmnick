//! Где пользователь печатает (просьба пользователя 2026-11-18): спутник отходит от поля ввода в любой
//! программе — блокноте, браузере, мессенджере, — чтобы его не приходилось отодвигать.
//!
//! Набор текста узнаётся без перехвата клавиатуры: время последнего ввода (`GetLastInputInfo`) сдвинулось,
//! а мышь не двигалась и кнопки не нажаты — значит, ввод с клавиатуры. Клавиши не читаются и не хранятся.
//! Место — системная каретка активного окна (`GetGUIThreadInfo`); программы без неё (часть браузеров и
//! мессенджеров) — рамка поля в фокусе из UI Automation. Свой поток: UI Automation может ждать.

use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Emitter};
use windows_sys::Win32::Foundation::POINT;
use windows_sys::Win32::Graphics::Gdi::ClientToScreen;
use windows_sys::Win32::UI::Input::KeyboardAndMouse::{
    GetAsyncKeyState, GetLastInputInfo, LASTINPUTINFO, VK_LBUTTON, VK_MBUTTON, VK_RBUTTON,
};
use windows_sys::Win32::UI::WindowsAndMessaging::{GetGUIThreadInfo, GUITHREADINFO};

use crate::companion::LABEL;
use crate::desktop::{self, Rect};

const TICK: Duration = Duration::from_millis(250);
/// Печатает, если клавиатура была не раньше стольких секунд назад.
const TYPING_FOR: Duration = Duration::from_millis(2500);

/// Узнаёт ввод с клавиатуры по времени последнего ввода и неподвижной мыши.
#[derive(Default)]
pub struct Keys {
    last_input: u32,
    last_cursor: (i32, i32),
    keys_at: Option<Instant>,
}

impl Keys {
    /// Шаг: `input` — время последнего ввода Windows, `cursor` — курсор, `buttons` — нажата ли кнопка мыши.
    pub fn step(&mut self, input: u32, cursor: (i32, i32), buttons: bool, now: Instant) -> bool {
        let fresh = input != self.last_input && self.last_input != 0;
        let still = cursor == self.last_cursor;
        if fresh && still && !buttons {
            self.keys_at = Some(now);
        }
        self.last_input = input;
        self.last_cursor = cursor;
        self.keys_at
            .is_some_and(|at| now.duration_since(at) <= TYPING_FOR)
    }
}

fn last_input() -> u32 {
    let mut info = LASTINPUTINFO {
        cbSize: size_of::<LASTINPUTINFO>() as u32,
        dwTime: 0,
    };
    // SAFETY: функция пишет время в `info`.
    unsafe { GetLastInputInfo(&mut info) };
    info.dwTime
}

fn mouse_buttons() -> bool {
    // SAFETY: функция только читает состояние клавиш.
    [VK_LBUTTON, VK_RBUTTON, VK_MBUTTON]
        .iter()
        .any(|&key| unsafe { GetAsyncKeyState(i32::from(key)) } < 0)
}

/// Системная каретка активного окна в пикселях экрана.
fn caret() -> Option<Rect> {
    // SAFETY: нулевая структура с размером — так требует функция; поток 0 — активный.
    let mut info: GUITHREADINFO = unsafe { std::mem::zeroed() };
    info.cbSize = size_of::<GUITHREADINFO>() as u32;
    if unsafe { GetGUIThreadInfo(0, &mut info) } == 0 || info.hwndCaret.is_null() {
        return None;
    }
    let r = info.rcCaret;
    let mut origin = POINT {
        x: r.left,
        y: r.top,
    };
    // SAFETY: окно каретки живо — его только что вернула система.
    if unsafe { ClientToScreen(info.hwndCaret, &mut origin) } == 0 {
        return None;
    }
    Some(Rect {
        x: origin.x,
        y: origin.y,
        w: (r.right - r.left).max(2),
        h: (r.bottom - r.top).max(12),
    })
}

/// Поток: раз в 0,25 с — печатает ли пользователь и где; слою — только при изменении.
pub fn watch(app: AppHandle) {
    let mut keys = Keys::default();
    let mut last: Option<Rect> = None;
    loop {
        thread::sleep(TICK);
        let typing = keys.step(
            last_input(),
            desktop::cursor(),
            mouse_buttons(),
            Instant::now(),
        );
        let place = if typing {
            caret().or_else(crate::uia::focused_rect)
        } else {
            None
        };
        if place != last {
            let _ = app.emit_to(LABEL, "companion-typing", place);
            last = place;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keys_without_mouse_movement_are_typing() {
        let t = Instant::now();
        let mut keys = Keys::default();
        assert!(!keys.step(100, (5, 5), false, t));
        assert!(keys.step(140, (5, 5), false, t + Duration::from_millis(250)));
        assert!(keys.step(140, (5, 5), false, t + Duration::from_secs(2)));
        assert!(!keys.step(140, (5, 5), false, t + Duration::from_secs(4)));
    }

    #[test]
    fn mouse_input_is_not_typing() {
        let t = Instant::now();
        let mut keys = Keys::default();
        keys.step(100, (5, 5), false, t);
        assert!(!keys.step(140, (60, 5), false, t + Duration::from_millis(250)));
        assert!(!keys.step(180, (60, 5), true, t + Duration::from_millis(500)));
    }
}
