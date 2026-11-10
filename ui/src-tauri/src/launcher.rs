//! Выбор издания между запусками (Этап 20, ADR-0032): `launcher.json` в папке настроек приложения.
//! Окно хранит строку JSON как есть: разбирает и проверяет её UI (`parseLauncher`), поэтому serde
//! и новые зависимости здесь не нужны.

use std::fs;

use tauri::Manager;

const FILE: &str = "launcher.json";
/// Больше — не наш файл: не читаем, UI получит умолчания.
const MAX_BYTES: u64 = 4096;

/// Сохранённый выбор как JSON-строка; нет файла или он чужой — `null` (умолчания в UI).
#[tauri::command]
pub fn launcher_load(app: tauri::AppHandle) -> String {
    let Ok(dir) = app.path().app_config_dir() else {
        return "null".into();
    };
    let path = dir.join(FILE);
    match fs::metadata(&path) {
        Ok(meta) if meta.len() <= MAX_BYTES => {
            fs::read_to_string(path).unwrap_or_else(|_| "null".into())
        }
        _ => "null".into(),
    }
}

/// Записать выбор: UI передаёт строку JSON уже проверенного состояния.
#[tauri::command]
pub fn launcher_save(app: tauri::AppHandle, json: String) -> Result<(), String> {
    if json.len() as u64 > MAX_BYTES {
        return Err("состояние окна слишком большое".into());
    }
    let dir = app.path().app_config_dir().map_err(|e| e.to_string())?;
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    fs::write(dir.join(FILE), json).map_err(|e| e.to_string())
}
