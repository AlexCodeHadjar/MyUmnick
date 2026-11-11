//! Оболочка окна. Логики здесь нет: UI говорит с ядром напрямую по WebSocket (ADR-0002).
//! В релизной сборке окно запускает ядро рядом с собой (ADR-0019) в выбранном издании (ADR-0032);
//! в разработке ядро запускают сами (`python -m vtuber serve --edition <id>`).

use tauri::Manager;

mod background;
mod launcher;
mod system_audio;

#[cfg(not(debug_assertions))]
mod core_process {
    use std::os::windows::process::CommandExt;
    use std::process::{Child, Command, Stdio};
    use std::sync::Mutex;
    use std::thread::sleep;
    use std::time::{Duration, Instant};

    use tauri::Manager;

    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    const STOP_TIMEOUT: Duration = Duration::from_secs(10);

    /// Ядро живёт, пока открыт его stdin: окно закрылось или упало — pipe закрыт, ядро выходит.
    /// Рядом — издание, в котором оно запущено: выбор того же издания не перезапускает ядро.
    pub struct CoreProcess(pub Mutex<Option<(Child, String)>>);

    pub fn manage(app: &tauri::App) {
        app.manage(CoreProcess(Mutex::new(None)));
    }

    /// Ядро издания `edition`; то же издание уже запущено — ничего не делает (предзапуск).
    pub fn start(app: &tauri::AppHandle, edition: &str) -> Result<(), String> {
        let core = app.state::<CoreProcess>();
        if let Ok(slot) = core.0.lock() {
            if matches!(slot.as_ref(), Some((_, running)) if running == edition) {
                return Ok(());
            }
        }
        stop(&core);
        let root = app
            .path()
            .resource_dir()
            .map_err(|e| e.to_string())?
            .join("core");
        let child = Command::new(root.join("vtuber-core.exe"))
            .args(["serve", "--edition", edition, "--root"])
            .arg(&root)
            .current_dir(&root)
            .stdin(Stdio::piped())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .creation_flags(CREATE_NO_WINDOW)
            .spawn()
            .map_err(|e| e.to_string())?;
        if let Ok(mut slot) = core.0.lock() {
            *slot = Some((child, edition.to_owned()));
        }
        Ok(())
    }

    /// Закрывает ядро и ждёт его выхода: иначе новое ядро не получит порт шлюза и видеопамять.
    pub fn stop(core: &CoreProcess) {
        let Some((mut child, _)) = core.0.lock().ok().and_then(|mut slot| slot.take()) else {
            return;
        };
        drop(child.stdin.take());
        let started = Instant::now();
        while started.elapsed() < STOP_TIMEOUT {
            if matches!(child.try_wait(), Ok(Some(_))) {
                return;
            }
            sleep(Duration::from_millis(100));
        }
        let _ = child.kill();
        let _ = child.wait();
    }
}

/// Издания, которые знает окно: чужое значение из UI ядру не передаётся.
const EDITIONS: [&str; 2] = ["ru", "en"];

/// Ядро нужного издания (экран выбора, Этап 20). В разработке ядро запускают руками.
#[tauri::command]
fn core_start(_app: tauri::AppHandle, edition: String) -> Result<(), String> {
    if !EDITIONS.contains(&edition.as_str()) {
        return Err(format!("неизвестное издание {edition}"));
    }
    #[cfg(not(debug_assertions))]
    core_process::start(&_app, &edition)?;
    Ok(())
}

/// Остановить ядро перед сменой издания из строки статуса.
#[tauri::command]
fn core_stop(_app: tauri::AppHandle) {
    #[cfg(not(debug_assertions))]
    {
        if let Some(core) = _app.try_state::<core_process::CoreProcess>() {
            core_process::stop(&core);
        }
    }
}

/// После установки моделей мастером: они подхватываются при старте ядра (S-13.2).
#[tauri::command]
fn restart_app(app: tauri::AppHandle) {
    core_stop(app.clone());
    app.restart();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(system_audio::SystemAudio::default())
        .invoke_handler(tauri::generate_handler![
            restart_app,
            core_start,
            core_stop,
            background::background_mode,
            background::window_reveal,
            launcher::launcher_load,
            launcher::launcher_save,
            system_audio::system_audio_start,
            system_audio::system_audio_stop
        ])
        // Крестик прячет окно в трей: витюбер продолжает слушать, выход — из меню значка (ADR-0041).
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                if let Some(webview) = window.app_handle().get_webview_window(window.label()) {
                    background::hide(&webview);
                }
            }
        })
        .setup(|app| {
            #[cfg(not(debug_assertions))]
            core_process::manage(app);
            background::tray(app)?;
            // Окно создаётся скрытым (tauri.conf.json): в фоне его откроет зов по имени.
            if !background::requested() {
                background::reveal(app.handle(), true);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("не удалось запустить окно Tauri");
}
