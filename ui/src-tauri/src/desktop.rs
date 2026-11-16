//! Картина рабочего стола для «Сопровождения» (Этап 23, ADR-0045): окна, на которые можно сесть,
//! открытые участки их верхних краёв, активное окно, монитор и полный экран. По образцу Capri
//! (`app/Ledges.cs`): опрос `EnumWindows`, рамка — по DWM без тени, «облачные» окна и оболочка
//! Windows отсеиваются, край окна — минус участки, закрытые окнами выше по z-порядку.

use std::mem::size_of;

use serde::Serialize;
use windows_sys::core::BOOL;
use windows_sys::Win32::Foundation::{HWND, LPARAM, POINT, RECT};
use windows_sys::Win32::Graphics::Dwm::{
    DwmGetWindowAttribute, DWMWA_CLOAKED, DWMWA_EXTENDED_FRAME_BOUNDS,
};
use windows_sys::Win32::Graphics::Gdi::{
    GetMonitorInfoW, MonitorFromPoint, MONITORINFO, MONITOR_DEFAULTTOPRIMARY,
};
use windows_sys::Win32::UI::Shell::SHQueryUserNotificationState;
use windows_sys::Win32::UI::WindowsAndMessaging::{
    EnumWindows, GetAncestor, GetClassNameW, GetCursorPos, GetForegroundWindow, GetWindowLongPtrW,
    GetWindowRect, GetWindowThreadProcessId, IsIconic, IsWindowVisible, IsZoomed, GA_ROOT,
    GWL_EXSTYLE, WS_EX_APPWINDOW, WS_EX_LAYERED, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW,
    WS_EX_TRANSPARENT,
};

/// Меньше — не садимся (как у Capri: 120×60).
const MIN_W: i32 = 120;
const MIN_H: i32 = 60;
/// Окна оболочки: рабочий стол, панель задач, меню.
const SHELL: [&str; 6] = [
    "Progman",
    "WorkerW",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "#32768",
    "tooltips_class32",
];
const DESKTOP: [&str; 4] = [
    "Progman",
    "WorkerW",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
];

#[derive(Serialize, Clone, Copy, PartialEq, Debug)]
pub struct Rect {
    pub x: i32,
    pub y: i32,
    pub w: i32,
    pub h: i32,
}

impl Rect {
    fn of(r: RECT) -> Self {
        Self {
            x: r.left,
            y: r.top,
            w: r.right - r.left,
            h: r.bottom - r.top,
        }
    }

    fn covers(&self, other: &Rect) -> bool {
        self.x <= other.x
            && self.y <= other.y
            && self.x + self.w >= other.x + other.w
            && self.y + self.h >= other.y + other.h
    }

    fn intersects(&self, other: &Rect) -> bool {
        self.x < other.x + other.w
            && other.x < self.x + self.w
            && self.y < other.y + other.h
            && other.y < self.y + self.h
    }
}

/// Окно, на верхний край которого можно сесть; `open` — свободные от других окон участки края.
#[derive(Serialize, Clone, PartialEq, Debug)]
pub struct Seat {
    pub id: i64,
    pub rect: Rect,
    pub open: Vec<(i32, i32)>,
}

/// Что сейчас активно: окно из `seats`, развёрнутое окно, рабочий стол или что-то ещё.
#[derive(Serialize, Clone, PartialEq, Debug)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub enum Focus {
    Window { id: i64 },
    Maximized,
    Desktop,
    Other,
}

/// Картина основного монитора в физических пикселях экрана.
#[derive(Serialize, Clone, PartialEq, Debug)]
pub struct World {
    pub monitor: Rect,
    pub work: Rect,
    pub seats: Vec<Seat>,
    pub focus: Focus,
    pub fullscreen: bool,
}

struct Seen {
    hwnd: HWND,
    rect: Rect,
    zoomed: bool,
}

fn class_of(hwnd: HWND) -> String {
    let mut buf = [0u16; 64];
    // SAFETY: буфер на 64 символа, функция пишет не больше длины буфера.
    let len = unsafe { GetClassNameW(hwnd, buf.as_mut_ptr(), buf.len() as i32) };
    String::from_utf16_lossy(&buf[..len.max(0) as usize])
}

fn frame(hwnd: HWND) -> Option<Rect> {
    let mut r = RECT {
        left: 0,
        top: 0,
        right: 0,
        bottom: 0,
    };
    // SAFETY: указатель на RECT и его размер; DWM пишет только в него.
    let ok = unsafe {
        DwmGetWindowAttribute(
            hwnd,
            DWMWA_EXTENDED_FRAME_BOUNDS as u32,
            (&mut r as *mut RECT).cast(),
            size_of::<RECT>() as u32,
        )
    };
    // SAFETY: GetWindowRect пишет в тот же RECT; окно может исчезнуть — тогда 0.
    if ok != 0 && unsafe { GetWindowRect(hwnd, &mut r) } == 0 {
        return None;
    }
    Some(Rect::of(r))
}

fn cloaked(hwnd: HWND) -> bool {
    let mut value: u32 = 0;
    // SAFETY: атрибут DWMWA_CLOAKED — u32.
    let ok = unsafe {
        DwmGetWindowAttribute(
            hwnd,
            DWMWA_CLOAKED as u32,
            (&mut value as *mut u32).cast(),
            size_of::<u32>() as u32,
        )
    };
    ok == 0 && value != 0
}

fn pid_of(hwnd: HWND) -> u32 {
    let mut pid = 0u32;
    // SAFETY: функция пишет только pid.
    unsafe { GetWindowThreadProcessId(hwnd, &mut pid) };
    pid
}

/// Видимое окно чужой программы, не оболочка и не служебное; иначе — `None`.
fn seen(hwnd: HWND, own: u32) -> Option<Seen> {
    // SAFETY: проверки состояния окна по дескриптору; неверный дескриптор даёт 0.
    let (visible, iconic) = unsafe { (IsWindowVisible(hwnd) != 0, IsIconic(hwnd) != 0) };
    if !visible || iconic || cloaked(hwnd) || pid_of(hwnd) == own {
        return None;
    }
    // SAFETY: чтение расширенного стиля окна.
    let ex = unsafe { GetWindowLongPtrW(hwnd, GWL_EXSTYLE) } as u32;
    let tool = ex & WS_EX_TOOLWINDOW != 0 && ex & WS_EX_APPWINDOW == 0;
    let ghost = ex & WS_EX_TRANSPARENT != 0
        || ex & (WS_EX_NOACTIVATE | WS_EX_LAYERED) == (WS_EX_NOACTIVATE | WS_EX_LAYERED);
    if tool || ghost || SHELL.contains(&class_of(hwnd).as_str()) {
        return None;
    }
    // SAFETY: проверка развёрнутости по дескриптору.
    let zoomed = unsafe { IsZoomed(hwnd) } != 0;
    frame(hwnd).map(|rect| Seen { hwnd, rect, zoomed })
}

unsafe extern "system" fn collect(hwnd: HWND, data: LPARAM) -> BOOL {
    // SAFETY: `data` — указатель на Vec, переданный в `top_level`, живой на время EnumWindows.
    let list = unsafe { &mut *(data as *mut Vec<HWND>) };
    list.push(hwnd);
    1
}

/// Окна верхнего уровня сверху вниз по z-порядку.
fn top_level() -> Vec<HWND> {
    let mut list: Vec<HWND> = Vec::new();
    // SAFETY: обратный вызов пишет только в `list`, который живёт до конца вызова.
    unsafe { EnumWindows(Some(collect), &mut list as *mut Vec<HWND> as LPARAM) };
    list
}

/// Участки `[x0, x1)`, оставшиеся от `span` после вычитания `cuts`.
pub fn subtract(span: (i32, i32), cuts: &[(i32, i32)]) -> Vec<(i32, i32)> {
    let mut parts = vec![span];
    for &(c0, c1) in cuts {
        parts = parts
            .into_iter()
            .flat_map(|(a, b)| {
                let mut left = Vec::new();
                if c0 > a {
                    left.push((a, c0.min(b)));
                }
                if c1 < b {
                    left.push((c1.max(a), b));
                }
                if c1 <= a || c0 >= b {
                    left = vec![(a, b)];
                }
                left
            })
            .filter(|(a, b)| b - a >= 24)
            .collect();
    }
    parts
}

fn primary() -> (Rect, Rect) {
    let mut info: MONITORINFO = MONITORINFO {
        cbSize: size_of::<MONITORINFO>() as u32,
        rcMonitor: RECT {
            left: 0,
            top: 0,
            right: 0,
            bottom: 0,
        },
        rcWork: RECT {
            left: 0,
            top: 0,
            right: 0,
            bottom: 0,
        },
        dwFlags: 0,
    };
    // SAFETY: точка (0,0) лежит на основном мониторе; структура с правильным cbSize.
    unsafe {
        let monitor = MonitorFromPoint(POINT { x: 0, y: 0 }, MONITOR_DEFAULTTOPRIMARY);
        GetMonitorInfoW(monitor, &mut info);
    }
    (Rect::of(info.rcMonitor), Rect::of(info.rcWork))
}

fn busy() -> bool {
    let mut state = 0;
    // SAFETY: функция пишет состояние в `state`.
    let ok = unsafe { SHQueryUserNotificationState(&mut state) };
    // 3 — игра D3D на весь экран, 4 — презентация. «Занят» (2) Windows ставит и развёрнутому окну при
    // скрытой панели задач, поэтому полноэкранные окна без D3D ловит проверка «окно на весь монитор».
    ok == 0 && matches!(state, 3 | 4)
}

/// Корневое активное окно, если оно не наше.
pub fn foreground(own: u32) -> Option<HWND> {
    // SAFETY: дескриптор активного окна и его корня; 0 — нет активного окна.
    let hwnd = unsafe { GetAncestor(GetForegroundWindow(), GA_ROOT) };
    (!hwnd.is_null() && pid_of(hwnd) != own).then_some(hwnd)
}

fn focus_of(hwnd: Option<HWND>, seats: &[Seat], monitor: &Rect, own: u32) -> Focus {
    let Some(hwnd) = hwnd else {
        return Focus::Other;
    };
    if DESKTOP.contains(&class_of(hwnd).as_str()) {
        return Focus::Desktop;
    }
    let id = hwnd as isize as i64;
    if seats.iter().any(|seat| seat.id == id) {
        return Focus::Window { id };
    }
    match seen(hwnd, own) {
        Some(one) if one.zoomed || one.rect.covers(monitor) => Focus::Maximized,
        _ => Focus::Other,
    }
}

/// Полная картина: раз в секунду и при смене активного окна.
pub fn scan(own: u32) -> World {
    let (monitor, work) = primary();
    let windows: Vec<Seen> = top_level()
        .into_iter()
        .filter_map(|h| seen(h, own))
        .collect();
    let mut seats = Vec::new();
    for (i, one) in windows.iter().enumerate() {
        let r = one.rect;
        let fits = !one.zoomed && r.w >= MIN_W && r.h >= MIN_H && !r.covers(&monitor);
        if !fits || !r.intersects(&monitor) {
            continue;
        }
        let cuts: Vec<(i32, i32)> = windows[..i]
            .iter()
            .filter(|above| above.rect.y <= r.y && r.y < above.rect.y + above.rect.h)
            .map(|above| (above.rect.x, above.rect.x + above.rect.w))
            .collect();
        seats.push(Seat {
            id: one.hwnd as isize as i64,
            rect: r,
            open: subtract((r.x, r.x + r.w), &cuts),
        });
    }
    let fg = foreground(own);
    let focus = focus_of(fg, &seats, &monitor, own);
    // Развёрнутое окно при скрытой панели задач тоже закрывает весь монитор — это не полный экран.
    let covering = fg
        .and_then(|h| seen(h, own))
        .is_some_and(|one| !one.zoomed && one.rect.covers(&monitor));
    World {
        monitor,
        work,
        seats,
        focus,
        fullscreen: busy() || covering,
    }
}

/// Рамка одного окна (быстро, для следования за окном-хозяином); исчезло или свёрнуто — `None`.
pub fn rect_of(id: i64, own: u32) -> Option<Rect> {
    seen(id as isize as HWND, own)
        .filter(|one| !one.zoomed)
        .map(|one| one.rect)
}

/// Курсор в физических пикселях экрана.
pub fn cursor() -> (i32, i32) {
    let mut p = POINT { x: 0, y: 0 };
    // SAFETY: функция пишет координаты в `p`.
    unsafe { GetCursorPos(&mut p) };
    (p.x, p.y)
}

#[cfg(test)]
mod tests {
    use super::subtract;

    #[test]
    fn covered_parts_of_the_edge_are_cut_out() {
        assert_eq!(subtract((0, 100), &[]), vec![(0, 100)]);
        assert_eq!(subtract((0, 100), &[(30, 60)]), vec![(0, 30), (60, 100)]);
        assert_eq!(subtract((0, 100), &[(-10, 110)]), vec![]);
        assert_eq!(subtract((0, 100), &[(200, 300)]), vec![(0, 100)]);
        // Обрезки уже 24 px — не место, чтобы сесть.
        assert_eq!(subtract((0, 100), &[(10, 90)]), vec![]);
    }
}

#[cfg(test)]
mod live {
    #[test]
    #[ignore = "смотрит на настоящие окна этой машины"]
    fn print_scan() {
        let world = super::scan(0);
        println!("{world:#?}");
        for hwnd in super::top_level().into_iter().take(400) {
            let class = super::class_of(hwnd);
            if class.contains("Notepad") || class.contains("RichEdit") {
                use windows_sys::Win32::UI::WindowsAndMessaging::*;
                let (vis, icon, ex) = unsafe {
                    (
                        IsWindowVisible(hwnd),
                        IsIconic(hwnd),
                        GetWindowLongPtrW(hwnd, GWL_EXSTYLE),
                    )
                };
                println!(
                    "{class} {hwnd:?} vis={vis} icon={icon} cloaked={} ex={ex:#x} frame={:?} seen={:?}",
                    super::cloaked(hwnd),
                    super::frame(hwnd),
                    super::seen(hwnd, 0).map(|s| s.rect)
                );
            }
        }
    }
}
