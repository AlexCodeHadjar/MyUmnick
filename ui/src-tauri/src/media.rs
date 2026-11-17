//! Что играет в системе (ADR-0052): сеансы мультимедиа Windows (System Media Transport Controls). Браузеры
//! и плееры сами сообщают, что воспроизводят и на паузе ли. По этому спутник понимает, что вы смотрите
//! фильм, даже на незнакомом сайте. Название приложения-источника — для решения «видео или музыка»;
//! название трека наружу не уходит и нигде не хранится.

use serde::Serialize;
use windows::core::Interface;
use windows::Media::Control::{
    GlobalSystemMediaTransportControlsSession as Session,
    GlobalSystemMediaTransportControlsSessionManager as Manager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status,
};
use windows::Win32::Media::Audio::{
    eConsole, eRender, AudioSessionStateActive, IAudioSessionControl2, IAudioSessionManager2,
    IMMDeviceEnumerator, MMDeviceEnumerator,
};
use windows::Win32::System::Com::{
    CoCreateInstance, CoInitializeEx, CLSCTX_ALL, COINIT_MULTITHREADED,
};

use crate::desktop;

#[derive(Serialize, Clone, Debug, Default, PartialEq)]
pub struct Media {
    /// `playing` или `paused`.
    pub state: &'static str,
    /// Источник в нижнем регистре (AUMID): `chrome.exe`, `msedge`, `spotify.exe`…
    pub app: String,
}

fn state_of(session: &Session) -> Option<&'static str> {
    let status = session
        .GetPlaybackInfo()
        .and_then(|info| info.PlaybackStatus())
        .ok()?;
    match status {
        Status::Playing => Some("playing"),
        Status::Paused => Some("paused"),
        _ => None,
    }
}

/// Все источники звука: сеансы мультимедиа Windows и аудиосеансы (Core Audio) — на случай, если
/// источник о себе не сообщает (Яндекс Браузер — проверено 2026-11-17). Какой из них видео, решает слой
/// спутника по имени программы. Вызывать не из потока окна: ждёт WinRT и COM.
pub fn now() -> Vec<Media> {
    // SAFETY: COM/WinRT в этом потоке; повторная инициализация безвредна (S_FALSE).
    let _ = unsafe { CoInitializeEx(None, COINIT_MULTITHREADED) };
    let mut all = sessions();
    all.extend(audible());
    all
}

/// Аудиосеансы устройства вывода: активный — «играет», есть, но молчит — «пауза».
fn audible() -> Vec<Media> {
    // SAFETY: COM-вызовы к живым объектам Core Audio; любая ошибка — пустой список.
    let found = unsafe {
        let enumerator: windows::core::Result<IMMDeviceEnumerator> =
            CoCreateInstance(&MMDeviceEnumerator, None, CLSCTX_ALL);
        enumerator
            .and_then(|e| e.GetDefaultAudioEndpoint(eRender, eConsole))
            .and_then(|device| device.Activate::<IAudioSessionManager2>(CLSCTX_ALL, None))
            .and_then(|manager| manager.GetSessionEnumerator())
    };
    let Ok(list) = found else { return Vec::new() };
    let own = std::process::id();
    let mut out = Vec::new();
    // SAFETY: см. выше.
    let count = unsafe { list.GetCount() }.unwrap_or(0);
    for i in 0..count {
        // SAFETY: см. выше.
        let Ok(control) = (unsafe { list.GetSession(i) }) else {
            continue;
        };
        let Ok(control2) = control.cast::<IAudioSessionControl2>() else {
            continue;
        };
        // SAFETY: см. выше.
        let (pid, state) = unsafe { (control2.GetProcessId(), control.GetState()) };
        let (Ok(pid), Ok(state)) = (pid, state) else {
            continue;
        };
        if pid == 0 || pid == own {
            continue;
        }
        let state = if state == AudioSessionStateActive {
            "playing"
        } else {
            "paused"
        };
        out.push(Media {
            state,
            app: desktop::exe_of(pid),
        });
    }
    out
}

/// Сеансы мультимедиа Windows (SMTC).
fn sessions() -> Vec<Media> {
    let Ok(sessions) = Manager::RequestAsync()
        .and_then(|op| op.join())
        .and_then(|manager| manager.GetSessions())
    else {
        return Vec::new();
    };
    let mut out = Vec::new();
    for i in 0..sessions.Size().unwrap_or(0) {
        let Ok(session) = sessions.GetAt(i) else {
            continue;
        };
        let Some(state) = state_of(&session) else {
            continue;
        };
        let app = session
            .SourceAppUserModelId()
            .map(|id| id.to_string().to_lowercase())
            .unwrap_or_default();
        out.push(Media { state, app });
    }
    out
}

#[cfg(test)]
mod live {
    #[test]
    #[ignore = "смотрит на настоящие сеансы мультимедиа этой машины"]
    fn print_media() {
        println!("{:?}", super::now());
    }
}
