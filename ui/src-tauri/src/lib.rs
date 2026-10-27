//! Оболочка окна. Логики здесь нет: UI говорит с ядром напрямую по WebSocket (ADR-0002),
//! запуск ядра как sidecar — S-13.1 (ADR-0009).

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("не удалось запустить окно Tauri");
}
