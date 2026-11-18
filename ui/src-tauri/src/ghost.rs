//! «Не мешать кликам» (ADR-0045, дополнение 2026-11-18): клики идут сквозь персонажа, слой их не видит.
//! Чтобы вернуть обычный режим, хватит двойного щелчка по персонажу: поток спутника опрашивает левую кнопку
//! мыши и узнаёт два нажатия подряд над прямоугольником персонажа. Сам щелчок при этом уходит окну под ним.

use std::time::{Duration, Instant};

use windows_sys::Win32::UI::Input::KeyboardAndMouse::{
    GetAsyncKeyState, GetDoubleClickTime, VK_LBUTTON,
};

/// Левая кнопка мыши нажата сейчас.
pub fn left_down() -> bool {
    // SAFETY: функция только читает состояние клавиши.
    let state = unsafe { GetAsyncKeyState(i32::from(VK_LBUTTON)) };
    state < 0
}

/// Окно двойного щелчка из настроек Windows.
pub fn double_click_time() -> Duration {
    // SAFETY: функция без аргументов, только читает настройку.
    Duration::from_millis(u64::from(unsafe { GetDoubleClickTime() }))
}

/// Два нажатия левой кнопки над персонажем подряд, не дольше окна двойного щелчка.
#[derive(Default)]
pub struct DoubleClick {
    down: bool,
    first: Option<Instant>,
}

impl DoubleClick {
    /// Шаг опроса: вернёт `true` на втором нажатии двойного щелчка над персонажем.
    pub fn step(&mut self, pressed: bool, over: bool, now: Instant, window: Duration) -> bool {
        let edge = pressed && !self.down;
        self.down = pressed;
        if !edge {
            return false;
        }
        if !over {
            self.first = None;
            return false;
        }
        if self.first.is_some_and(|t| now.duration_since(t) <= window) {
            self.first = None;
            return true;
        }
        self.first = Some(now);
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const WINDOW: Duration = Duration::from_millis(500);

    fn press(d: &mut DoubleClick, over: bool, at: Instant) -> bool {
        let hit = d.step(true, over, at, WINDOW);
        d.step(false, over, at + Duration::from_millis(30), WINDOW);
        hit
    }

    #[test]
    fn two_quick_presses_over_the_character() {
        let t = Instant::now();
        let mut d = DoubleClick::default();
        assert!(!press(&mut d, true, t));
        assert!(press(&mut d, true, t + Duration::from_millis(200)));
    }

    #[test]
    fn slow_presses_are_not_a_double_click() {
        let t = Instant::now();
        let mut d = DoubleClick::default();
        assert!(!press(&mut d, true, t));
        assert!(!press(&mut d, true, t + Duration::from_millis(800)));
    }

    #[test]
    fn a_press_elsewhere_breaks_the_pair() {
        let t = Instant::now();
        let mut d = DoubleClick::default();
        assert!(!press(&mut d, true, t));
        assert!(!press(&mut d, false, t + Duration::from_millis(100)));
        assert!(!press(&mut d, true, t + Duration::from_millis(200)));
    }

    #[test]
    fn holding_the_button_is_one_press() {
        let t = Instant::now();
        let mut d = DoubleClick::default();
        assert!(!d.step(true, true, t, WINDOW));
        assert!(!d.step(true, true, t + Duration::from_millis(100), WINDOW));
    }
}
