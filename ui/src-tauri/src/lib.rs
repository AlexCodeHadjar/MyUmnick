//! Оболочка окна. Логики здесь нет: UI говорит с ядром напрямую по WebSocket (ADR-0002).
//! В релизной сборке окно запускает ядро рядом с собой (ADR-0019); в разработке ядро запускают сами.

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
    pub struct CoreProcess(pub Mutex<Option<Child>>);

    pub fn start(app: &tauri::App) -> tauri::Result<()> {
        let root = app.path().resource_dir()?.join("core");
        let child = Command::new(root.join("vtuber-core.exe"))
            .args(["serve", "--root"])
            .arg(&root)
            .current_dir(&root)
            .stdin(Stdio::piped())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .creation_flags(CREATE_NO_WINDOW)
            .spawn()?;
        app.manage(CoreProcess(Mutex::new(Some(child))));
        Ok(())
    }

    /// Закрывает ядро и ждёт его выхода: иначе новое ядро не получит порт шлюза.
    pub fn stop(core: &CoreProcess) {
        let Some(mut child) = core.0.lock().ok().and_then(|mut slot| slot.take()) else {
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

/// После установки моделей мастером: они подхватываются при старте ядра (S-13.2).
#[tauri::command]
fn restart_app(app: tauri::AppHandle) {
    #[cfg(not(debug_assertions))]
    {
        use tauri::Manager;
        if let Some(core) = app.try_state::<core_process::CoreProcess>() {
            core_process::stop(&core);
        }
    }
    app.restart();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![restart_app])
        .setup(|_app| {
            #[cfg(not(debug_assertions))]
            core_process::start(_app)?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("не удалось запустить окно Tauri");
}
