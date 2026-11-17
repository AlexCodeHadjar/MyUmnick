//! «Сопровождение» (Этап 23, ADR-0045): второе окно — прозрачный слой на весь основной монитор, поверх всех,
//! без фокуса и без кнопки в панели задач. Клики идут сквозь слой везде, кроме персонажа: проверку делает
//! этот поток по прямоугольнику, который присылает UI. Он же раз в секунду (и сразу при смене активного
//! окна) собирает картину рабочего стола (`desktop.rs`) и шлёт её окну спутника.

use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use tauri::{
    AppHandle, Emitter, Manager, PhysicalPosition, PhysicalSize, WebviewUrl, WebviewWindow,
    WebviewWindowBuilder,
};
use windows_sys::Win32::Foundation::HWND;
use windows_sys::Win32::UI::WindowsAndMessaging::{
    GetWindowLongPtrW, SetWindowLongPtrW, SetWindowPos, GWL_EXSTYLE, HWND_TOPMOST, SWP_NOACTIVATE,
    SWP_NOMOVE, SWP_NOSIZE, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW,
};

use crate::desktop::{self, Rect, World};

pub const LABEL: &str = "companion";
const TICK: Duration = Duration::from_millis(16);
/// Активное окно — 20 раз в секунду, полная картина — раз в секунду (как у Capri).
const FOCUS_EVERY: u32 = 3;
const SCAN_EVERY: u32 = 60;
/// Курсор — 15 раз в секунду: спутник поворачивается к мыши (просьба пользователя 2026-11-17).
const CURSOR_EVERY: u32 = 4;
/// Раз в 0,5 с (и сразу при смене активного окна) слой снова встаёт поверх всех: другие окна «поверх всех» не прячут облачко
/// (просьба пользователя 2026-11-17).
const TOPMOST_EVERY: u32 = 30;

/// Прямоугольник персонажа в CSS-пикселях окна спутника.
#[derive(Deserialize, Clone, Copy, Debug)]
pub struct Hit {
    pub x: f64,
    pub y: f64,
    pub w: f64,
    pub h: f64,
}

#[derive(Default)]
struct Shared {
    hit: Option<Hit>,
    /// Персонажа держат мышью: клики не отпускаем, даже если курсор убежал за прямоугольник.
    capture: bool,
    host: Option<i64>,
    world: Option<World>,
}

#[derive(Default, Clone)]
pub struct CompanionState(Arc<Mutex<Shared>>);

/// Главное окно для спутника: показано ли и где оно (портал при сворачивании).
#[derive(Serialize, Clone, PartialEq, Debug)]
struct MainState {
    shown: bool,
    /// Окно в фокусе: переключились на другую программу — спутник выходит из портала.
    focused: bool,
    rect: Rect,
}

fn no_activate(window: &WebviewWindow) {
    let Ok(hwnd) = window.hwnd() else { return };
    let hwnd = hwnd.0 as HWND;
    // SAFETY: дескриптор нашего окна; меняем только расширенный стиль: без фокуса, не в Alt+Tab.
    unsafe {
        let ex = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
        SetWindowLongPtrW(
            hwnd,
            GWL_EXSTYLE,
            ex | (WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW) as isize,
        );
    }
}

/// Поднимает слой над другими окнами «поверх всех», не забирая фокус.
fn raise(window: &WebviewWindow) {
    let Ok(hwnd) = window.hwnd() else { return };
    // SAFETY: дескриптор нашего окна; только порядок окон, без сдвига, размера и активации.
    unsafe {
        SetWindowPos(
            hwnd.0 as HWND,
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        );
    }
}

/// Слой создаётся скрытым при старте; показывает его UI спутника (`companion_set`).
pub fn create(app: &tauri::App) -> tauri::Result<()> {
    let window = WebviewWindowBuilder::new(app, LABEL, WebviewUrl::default())
        .title("AI VTuber — companion")
        .transparent(true)
        .decorations(false)
        .shadow(false)
        .always_on_top(true)
        .skip_taskbar(true)
        .resizable(false)
        .focused(false)
        .visible(false)
        .disable_drag_drop_handler()
        // Те же аргументы, что у главного окна: среда WebView2 одна на приложение.
        .additional_browser_args(
            "--disable-features=msWebOOUI,msPdfOOUI,msSmartScreenProtection --use-fake-ui-for-media-stream",
        )
        .build()?;
    no_activate(&window);
    window.set_ignore_cursor_events(true)?;
    let state = CompanionState::default();
    app.manage(state.clone());
    let handle = app.handle().clone();
    thread::spawn(move || watch(&handle, &state));
    Ok(())
}

fn place(window: &WebviewWindow, monitor: &Rect) {
    let _ = window.set_position(PhysicalPosition::new(monitor.x, monitor.y));
    let _ = window.set_size(PhysicalSize::new(monitor.w as u32, monitor.h as u32));
}

/// Поток спутника: клики сквозь слой, картина рабочего стола, окно-хозяин, главное окно.
fn watch(app: &AppHandle, state: &CompanionState) {
    let own = std::process::id();
    let mut tick: u32 = 0;
    let mut passing = true;
    let mut last_fg = None;
    let mut last_host = None;
    let mut last_main = None;
    let mut last_cursor = (f64::NAN, f64::NAN);
    loop {
        thread::sleep(TICK);
        tick = tick.wrapping_add(1);
        let Some(window) = app.get_webview_window(LABEL) else {
            continue;
        };
        if window.is_visible().unwrap_or(false) {
            passing = hit_test(&window, state, passing);
            if tick % CURSOR_EVERY == 0 {
                last_cursor = publish_cursor(app, &window, last_cursor);
            }
            if tick % TOPMOST_EVERY == 0 {
                raise(&window);
            }
        }
        if tick % FOCUS_EVERY == 0 {
            let fg = desktop::foreground(own).map(|h| h as isize);
            if fg != last_fg || tick % SCAN_EVERY == 0 {
                // Новое активное окно могло встать поверх всех — поднимаемся над ним сразу.
                if fg != last_fg && window.is_visible().unwrap_or(false) {
                    raise(&window);
                }
                last_fg = fg;
                publish_world(app, &window, state, own);
            }
            // Раз в секунду — и без изменений: слой, загрузившийся позже события (перезапуск окна, ожидание
            // сборки), иначе считал бы главное окно открытым и не появлялся (проверено вживую 2026-11-17).
            let again = if tick % SCAN_EVERY == 0 {
                None
            } else {
                last_main
            };
            last_main = publish_main(app, again);
        }
        last_host = publish_host(app, state, own, last_host);
    }
}

/// Курсор в CSS-пикселях слоя; шлётся, только если сдвинулся заметно (больше 3 px).
fn publish_cursor(app: &AppHandle, window: &WebviewWindow, last: (f64, f64)) -> (f64, f64) {
    let scale = window.scale_factor().unwrap_or(1.0);
    let origin = window.outer_position().unwrap_or_default();
    let (cx, cy) = desktop::cursor();
    let now = (
        f64::from(cx - origin.x) / scale,
        f64::from(cy - origin.y) / scale,
    );
    let moved = (now.0 - last.0).abs() > 3.0 || (now.1 - last.1).abs() > 3.0 || last.0.is_nan();
    if !moved {
        return last;
    }
    let _ = app.emit_to(LABEL, "companion-cursor", now);
    now
}

fn hit_test(window: &WebviewWindow, state: &CompanionState, passing: bool) -> bool {
    let (hit, capture) = match state.0.lock() {
        Ok(shared) => (shared.hit, shared.capture),
        Err(_) => return passing,
    };
    let scale = window.scale_factor().unwrap_or(1.0);
    let origin = window.outer_position().unwrap_or_default();
    let (cx, cy) = desktop::cursor();
    let x = f64::from(cx - origin.x) / scale;
    let y = f64::from(cy - origin.y) / scale;
    let over = hit.is_some_and(|h| x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h);
    let pass = !(over || capture);
    if pass != passing {
        let _ = window.set_ignore_cursor_events(pass);
    }
    pass
}

fn publish_world(app: &AppHandle, window: &WebviewWindow, state: &CompanionState, own: u32) {
    let world = desktop::scan(own);
    let Ok(mut shared) = state.0.lock() else {
        return;
    };
    if shared.world.as_ref() == Some(&world) {
        return;
    }
    if shared.world.as_ref().map(|w| w.monitor) != Some(world.monitor) {
        place(window, &world.monitor);
    }
    let _ = app.emit_to(LABEL, "companion-world", &world);
    shared.world = Some(world);
}

fn publish_host(
    app: &AppHandle,
    state: &CompanionState,
    own: u32,
    last: Option<Option<Rect>>,
) -> Option<Option<Rect>> {
    let host = state.0.lock().ok().and_then(|shared| shared.host);
    let id = host?;
    let rect = desktop::rect_of(id, own);
    if last != Some(rect) {
        let _ = app.emit_to(LABEL, "companion-host", (id, rect));
    }
    Some(rect)
}

fn publish_main(app: &AppHandle, last: Option<MainState>) -> Option<MainState> {
    let main = app.get_webview_window("main")?;
    let shown = main.is_visible().unwrap_or(false) && !main.is_minimized().unwrap_or(false);
    let pos = main.outer_position().unwrap_or_default();
    let size = main.outer_size().unwrap_or_default();
    let rect = Rect {
        x: pos.x,
        y: pos.y,
        w: size.width as i32,
        h: size.height as i32,
    };
    let focused = main.is_focused().unwrap_or(false);
    let state = MainState {
        shown,
        focused,
        rect,
    };
    if last.as_ref() != Some(&state) {
        let _ = app.emit_to(LABEL, "companion-main", &state);
    }
    Some(state)
}

/// Показан ли слой спутника: при показе зов по имени отвечает спутник, а не главное окно.
pub fn visible(app: &AppHandle) -> bool {
    app.get_webview_window(LABEL)
        .and_then(|w| w.is_visible().ok())
        .unwrap_or(false)
}

/// Показать или спрятать слой; при показе — картина рабочего стола сразу.
#[tauri::command]
pub fn companion_set(app: AppHandle, state: tauri::State<'_, CompanionState>, visible: bool) {
    let Some(window) = app.get_webview_window(LABEL) else {
        return;
    };
    if visible {
        let _ = window.show();
        no_activate(&window);
        publish_world(&app, &window, &state, std::process::id());
    } else {
        let _ = window.hide();
    }
}

/// Где персонаж (CSS-пиксели слоя) и держат ли его мышью.
#[tauri::command]
pub fn companion_hit(state: tauri::State<'_, CompanionState>, hit: Option<Hit>, capture: bool) {
    if let Ok(mut shared) = state.0.lock() {
        shared.hit = hit;
        shared.capture = capture;
    }
}

/// На каком окне сидит персонаж: его рамка приходит быстро (`companion-host`), окно можно двигать.
#[tauri::command]
pub fn companion_attach(state: tauri::State<'_, CompanionState>, host: Option<i64>) {
    if let Ok(mut shared) = state.0.lock() {
        shared.host = host;
    }
}

/// Последняя картина рабочего стола (окно спутника перезагрузилось).
#[tauri::command]
pub fn companion_world(state: tauri::State<'_, CompanionState>) -> Option<World> {
    state.0.lock().ok().and_then(|shared| shared.world.clone())
}

/// Что играет в системе (ADR-0052) — в отдельном потоке: ожидание WinRT блокирует.
#[tauri::command]
pub async fn companion_media() -> Vec<crate::media::Media> {
    tauri::async_runtime::spawn_blocking(crate::media::now)
        .await
        .unwrap_or_default()
}

/// Что можно «потыкать» в активном окне или на рабочем столе (ADR-0048). Обход UI Automation —
/// в отдельном потоке: он блокирует, а окно и поток слежения не должны ждать.
#[tauri::command]
pub async fn companion_targets() -> Vec<crate::uia::Target> {
    let own = std::process::id();
    let world = desktop::scan(own);
    let hwnd = match world.focus {
        desktop::Focus::Desktop => 0,
        desktop::Focus::Window { id, .. } => id as isize,
        _ => match desktop::foreground(own) {
            Some(h) => h as isize,
            None => return Vec::new(),
        },
    };
    // Только видимое: элементы, закрытые окнами выше, спутник не «видит» (ADR-0052).
    let covers = desktop::covering((hwnd != 0).then_some(hwnd), own);
    tauri::async_runtime::spawn_blocking(move || crate::uia::targets(hwnd, &covers))
        .await
        .unwrap_or_default()
}
