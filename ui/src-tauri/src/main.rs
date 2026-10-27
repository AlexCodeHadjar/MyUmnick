// Без консольного окна в релизной сборке Windows; в отладке консоль нужна для логов.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    vtuber_ui_lib::run();
}
