//! Оболочка окна. Логики здесь нет: UI говорит с ядром напрямую по WebSocket (ADR-0002).
//! В релизной сборке окно запускает ядро рядом с собой (ADR-0019); в разработке ядро запускают сами.

#[cfg(not(debug_assertions))]
mod core_process {
    use std::os::windows::process::CommandExt;
    use std::process::{Child, Command, Stdio};

    use tauri::Manager;

    const CREATE_NO_WINDOW: u32 = 0x0800_0000;

    /// Ядро живёт, пока открыт его stdin: окно закрылось или упало — pipe закрыт, ядро выходит.
    pub struct CoreProcess(#[allow(dead_code)] pub Child);

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
        app.manage(CoreProcess(child));
        Ok(())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|_app| {
            #[cfg(not(debug_assertions))]
            core_process::start(_app)?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("не удалось запустить окно Tauri");
}
