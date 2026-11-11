//! Фоновый режим (ADR-0041): окно живёт в трее, слушает микрофон и открывается, когда зовут по имени.
//! Старт с Windows — строка в `HKCU\...\Run` через `reg.exe`: плагин автозапуска был бы новой
//! зависимостью ради двух команд реестра.

use std::env;
use std::os::windows::process::CommandExt;
use std::process::Command;

use tauri::menu::{CheckMenuItem, Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Emitter, Manager, WebviewWindow};

const CREATE_NO_WINDOW: u32 = 0x0800_0000;
const RUN_KEY: &str = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run";
const RUN_VALUE: &str = "AI VTuber";
const MAIN: &str = "main";
/// Событие окну: показано (`true`) или спрятано. WebView2 скрытое окно видимым и считает, поэтому
/// `visibilitychange` не приходит, а ядру надо знать: из трея персонаж сам не заговаривает (S-15.1).
const SHOWN_EVENT: &str = "window-shown";

/// Спрятать окно в трей (крестик): витюбер продолжает слушать.
pub fn hide(window: &WebviewWindow) {
    let _ = window.hide();
    let _ = window.emit(SHOWN_EVENT, false);
}

/// Запуск «в фон»: окно не показывается, пока не позовут (`--background` или от лаунчера).
pub fn requested() -> bool {
    env::var("VTUBER_BACKGROUND").is_ok_and(|v| v == "1")
        || env::args().any(|arg| arg == "--background")
}

/// Чем Windows запустит приложение при входе. В разработке строку даёт лаунчер (`launch.ps1`):
/// без него запускать нечего, и пункт меню выключен.
fn autostart_command() -> Option<String> {
    if let Ok(command) = env::var("VTUBER_AUTOSTART_COMMAND") {
        if !command.is_empty() {
            return Some(command);
        }
    }
    if cfg!(debug_assertions) {
        return None;
    }
    let exe = env::current_exe().ok()?;
    Some(format!("\"{}\" --background", exe.display()))
}

fn reg(args: &[&str]) -> bool {
    Command::new("reg.exe")
        .args(args)
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .is_ok_and(|out| out.status.success())
}

fn autostart_enabled() -> bool {
    reg(&["query", RUN_KEY, "/v", RUN_VALUE])
}

fn set_autostart(enabled: bool) -> bool {
    match (enabled, autostart_command()) {
        (true, Some(command)) => reg(&[
            "add", RUN_KEY, "/v", RUN_VALUE, "/t", "REG_SZ", "/d", &command, "/f",
        ]),
        (true, None) => false,
        (false, _) => reg(&["delete", RUN_KEY, "/v", RUN_VALUE, "/f"]),
    }
}

/// Показать окно. `force = false` — только если оно скрыто или свёрнуто: открытое окно на зов
/// не выдёргивается поверх того, чем человек занят.
pub fn reveal(app: &AppHandle, force: bool) {
    let Some(window) = app.get_webview_window(MAIN) else {
        return;
    };
    let hidden = !window.is_visible().unwrap_or(true);
    let minimized = window.is_minimized().unwrap_or(false);
    if force || hidden || minimized {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
        let _ = window.emit(SHOWN_EVENT, true);
    }
}

/// Значок в трее: «Открыть», «Запускать вместе с Windows», «Выход»; клик — открыть окно.
pub fn tray(app: &tauri::App) -> tauri::Result<()> {
    let open = MenuItem::with_id(app, "open", "Открыть", true, None::<&str>)?;
    let can_autostart = autostart_command().is_some();
    let autostart = CheckMenuItem::with_id(
        app,
        "autostart",
        "Запускать вместе с Windows",
        can_autostart,
        autostart_enabled(),
        None::<&str>,
    )?;
    let quit = MenuItem::with_id(app, "quit", "Выход", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&open, &autostart, &quit])?;
    let mut builder = TrayIconBuilder::with_id(MAIN)
        .tooltip("Умник — слушает, зовите по имени")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(move |app, event| match event.id.as_ref() {
            "open" => reveal(app, true),
            "autostart" => {
                // Галочка уже переключена меню; реестр не дался — вернуть как было.
                let wanted = autostart.is_checked().unwrap_or(false);
                if !set_autostart(wanted) {
                    let _ = autostart.set_checked(autostart_enabled());
                }
            }
            "quit" => app.exit(0),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                reveal(tray.app_handle(), true);
            }
        });
    if let Some(icon) = app.default_window_icon() {
        builder = builder.icon(icon.clone());
    }
    builder.build(app)?;
    Ok(())
}

/// Запущено ли окно в фоне: UI пропускает экран выбора и включает микрофон.
#[tauri::command]
pub fn background_mode() -> bool {
    requested()
}

/// Позвали по имени (`input.barge_in`): скрытое или свёрнутое окно открывается.
#[tauri::command]
pub fn window_reveal(app: AppHandle) {
    reveal(&app, false);
}
