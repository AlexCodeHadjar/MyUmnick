//! Хронометраж запуска (ускорение запуска, 2026-11-19): когда процесс стартовал, когда открылось окно,
//! появился персонаж, ядро вышло на связь и бэкенды готовы. Без замера «до и после» ускорение не
//! принимается (AGENTS.md: «Изменение → замер до/после»).
//!
//! Метки — в `startup.log` папки настроек приложения: миллисекунды от клика по ярлыку (скрипт запуска
//! передаёт время в `AI_VTUBER_LAUNCH_AT`) и от старта процесса. Каждая метка — один раз за запуск.

use std::collections::HashSet;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::{Mutex, OnceLock};
use std::time::{SystemTime, UNIX_EPOCH};

use tauri::Manager;

const FILE: &str = "startup.log";
/// Больше — файл начинается заново: журнал только для замеров.
const MAX_BYTES: u64 = 256 * 1024;

struct Clock {
    process_ms: u128,
    launch_ms: Option<u128>,
    seen: Mutex<HashSet<String>>,
}

static CLOCK: OnceLock<Clock> = OnceLock::new();

fn now_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or_default()
}

/// Самое начало `run()`: время старта процесса.
pub fn begin() {
    let launch_ms = std::env::var("AI_VTUBER_LAUNCH_AT")
        .ok()
        .and_then(|raw| raw.trim().parse::<u128>().ok());
    let _ = CLOCK.set(Clock {
        process_ms: now_ms(),
        launch_ms,
        seen: Mutex::new(HashSet::new()),
    });
}

fn path(app: &tauri::AppHandle) -> Option<PathBuf> {
    let dir = app.path().app_config_dir().ok()?;
    fs::create_dir_all(&dir).ok()?;
    Some(dir.join(FILE))
}

/// Записать метку `name` (один раз за запуск).
pub fn mark(app: &tauri::AppHandle, name: &str) {
    let Some(clock) = CLOCK.get() else {
        return;
    };
    let first = clock
        .seen
        .lock()
        .map(|mut seen| seen.insert(name.to_owned()))
        .unwrap_or(false);
    let Some(path) = path(app).filter(|_| first) else {
        return;
    };
    let now = now_ms();
    let from_launch = clock
        .launch_ms
        .map(|at| format!("{:>6}", now.saturating_sub(at)))
        .unwrap_or_else(|| "     —".into());
    let line = format!(
        "{now} {from_launch} ms from shortcut {:>6} ms from process  {name}\n",
        now.saturating_sub(clock.process_ms)
    );
    if fs::metadata(&path).is_ok_and(|meta| meta.len() > MAX_BYTES) {
        let _ = fs::remove_file(&path);
    }
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
        let _ = file.write_all(line.as_bytes());
    }
}

/// Метка из окна: страница загрузилась, персонаж на экране, ядро на связи и т. п.
#[tauri::command]
pub fn startup_mark(app: tauri::AppHandle, name: String) {
    let name: String = name.chars().take(60).collect();
    mark(&app, &name);
}
