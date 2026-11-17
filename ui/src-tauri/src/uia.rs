//! Что на экране можно «потыкать» (просьба пользователя 2026-11-17, ADR-0048): кнопки, ссылки, вкладки,
//! пункты списков активного окна и значки рабочего стола — через UI Automation Windows. Это не зрение
//! и не OCR: названия и рамки отдаёт сама система, быстро и офлайн. Спутник ничего не нажимает —
//! только подлетает к элементу и комментирует его название.

use std::collections::VecDeque;
use std::time::{Duration, Instant};

use serde::Serialize;
use windows::core::BSTR;
use windows::Win32::Foundation::HWND;
use windows::Win32::System::Com::{
    CoCreateInstance, CoInitializeEx, CLSCTX_INPROC_SERVER, COINIT_MULTITHREADED,
};
use windows::Win32::UI::Accessibility::{
    CUIAutomation, IUIAutomation, IUIAutomationElement, IUIAutomationSelectionItemPattern,
    IUIAutomationTreeWalker, UIA_ButtonControlTypeId, UIA_HyperlinkControlTypeId,
    UIA_ListItemControlTypeId, UIA_MenuItemControlTypeId, UIA_SelectionItemPatternId,
    UIA_TabItemControlTypeId, UIA_CONTROLTYPE_ID,
};
use windows::Win32::UI::WindowsAndMessaging::{FindWindowExW, FindWindowW};

use crate::desktop::Rect;

/// Сколько элементов обойти и сколько времени тратить: браузер с сотней вкладок не должен тормозить.
const VISIT_LIMIT: usize = 900;
const BUDGET: Duration = Duration::from_millis(350);
const MAX_TARGETS: usize = 40;
const MAX_DEPTH: usize = 14;

/// Элемент, к которому можно подлететь: название и рамка в физических пикселях экрана.
#[derive(Serialize, Clone, Debug)]
pub struct Target {
    pub name: String,
    pub rect: Rect,
    pub kind: &'static str,
    /// Выбранная вкладка: по её названию спутник понимает, что идёт видео («смотрим вместе»).
    pub selected: bool,
}

/// Выбрана ли вкладка (шаблон SelectionItem); нет шаблона — нет.
fn selected(element: &IUIAutomationElement) -> bool {
    // SAFETY: COM-вызовы к живому элементу; ошибка — «не выбрана».
    unsafe {
        element
            .GetCurrentPatternAs::<IUIAutomationSelectionItemPattern>(UIA_SelectionItemPatternId)
            .and_then(|pattern| pattern.CurrentIsSelected())
            .is_ok_and(|yes| yes.as_bool())
    }
}

fn kind_of(control: UIA_CONTROLTYPE_ID) -> Option<&'static str> {
    match control {
        c if c == UIA_ButtonControlTypeId => Some("button"),
        c if c == UIA_HyperlinkControlTypeId => Some("link"),
        c if c == UIA_TabItemControlTypeId => Some("tab"),
        c if c == UIA_MenuItemControlTypeId => Some("menu"),
        c if c == UIA_ListItemControlTypeId => Some("item"),
        _ => None,
    }
}

/// Элемент как цель: видимый, с названием, разумного размера.
fn target(element: &IUIAutomationElement) -> Option<Target> {
    // SAFETY: COM-вызовы к живому элементу; ошибки — просто «не цель».
    unsafe {
        let kind = kind_of(element.CurrentControlType().ok()?)?;
        if element.CurrentIsOffscreen().ok()?.as_bool() {
            return None;
        }
        let name: BSTR = element.CurrentName().ok()?;
        let name = name.to_string().trim().to_owned();
        let r = element.CurrentBoundingRectangle().ok()?;
        let rect = Rect {
            x: r.left,
            y: r.top,
            w: r.right - r.left,
            h: r.bottom - r.top,
        };
        let sized = (8..=600).contains(&rect.w) && (8..=300).contains(&rect.h);
        let ok = sized && !name.is_empty() && name.chars().count() <= 60;
        ok.then(|| Target {
            name,
            rect,
            kind,
            selected: kind == "tab" && selected(element),
        })
    }
}

/// Обход дерева в ширину с ограничением по числу узлов, глубине и времени.
fn walk(walker: &IUIAutomationTreeWalker, root: IUIAutomationElement) -> Vec<Target> {
    let started = Instant::now();
    let mut found = Vec::new();
    let mut queue = VecDeque::from([(root, 0usize)]);
    let mut visited = 0;
    while let Some((element, depth)) = queue.pop_front() {
        visited += 1;
        if visited > VISIT_LIMIT || started.elapsed() > BUDGET || found.len() >= MAX_TARGETS {
            break;
        }
        if let Some(one) = target(&element) {
            found.push(one);
        }
        if depth >= MAX_DEPTH {
            continue;
        }
        // SAFETY: обход детей через walker; конец списка — ошибка или пустой результат.
        let mut child = unsafe { walker.GetFirstChildElement(&element) }.ok();
        while let Some(current) = child {
            child = unsafe { walker.GetNextSiblingElement(&current) }.ok();
            queue.push_back((current, depth + 1));
        }
    }
    found
}

/// Список значков рабочего стола (`Progman` → `SHELLDLL_DefView` → `SysListView32`).
fn desktop_icons() -> Option<HWND> {
    // SAFETY: поиск окон оболочки по классам; нет окна — ошибка.
    unsafe {
        let progman = FindWindowW(windows::core::w!("Progman"), None).ok()?;
        let view = FindWindowExW(
            Some(progman),
            None,
            windows::core::w!("SHELLDLL_DefView"),
            None,
        )
        .ok()?;
        FindWindowExW(Some(view), None, windows::core::w!("SysListView32"), None).ok()
    }
}

/// Цели в окне `hwnd` (0 — значки рабочего стола), видимые на экране: центр цели не закрыт ни одним из
/// окон `covers` (окна выше по z-порядку). Вызывать не из потока окна: обход блокирует.
pub fn targets(hwnd: isize, covers: &[Rect]) -> Vec<Target> {
    // SAFETY: COM в этом потоке; повторная инициализация безвредна (S_FALSE).
    let _ = unsafe { CoInitializeEx(None, COINIT_MULTITHREADED) };
    let window = if hwnd == 0 {
        desktop_icons()
    } else {
        Some(HWND(hwnd as *mut _))
    };
    let Some(window) = window else {
        return Vec::new();
    };
    // SAFETY: создание UI Automation и корня по дескриптору окна.
    let automation: windows::core::Result<IUIAutomation> =
        unsafe { CoCreateInstance(&CUIAutomation, None, CLSCTX_INPROC_SERVER) };
    let Ok(automation) = automation else {
        return Vec::new();
    };
    let (Ok(root), Ok(walker)) = (unsafe { automation.ElementFromHandle(window) }, unsafe {
        automation.ControlViewWalker()
    }) else {
        return Vec::new();
    };
    let visible = |one: &Target| {
        let (cx, cy) = (one.rect.x + one.rect.w / 2, one.rect.y + one.rect.h / 2);
        !covers.iter().any(|r| r.contains(cx, cy))
    };
    walk(&walker, root).into_iter().filter(visible).collect()
}

#[cfg(test)]
mod live {
    #[test]
    #[ignore = "смотрит на настоящий рабочий стол этой машины"]
    fn print_desktop_targets() {
        let found = super::targets(0, &[]);
        println!("{} targets", found.len());
        for one in found.iter().take(8) {
            println!("{one:?}");
        }
    }
}
