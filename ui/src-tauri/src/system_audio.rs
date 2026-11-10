//! Звук компьютера для сферы (Этап 22, ADR-0039): WASAPI loopback выхода по умолчанию через cpal.
//! В окно уходят только три числа — громкость басов, середины и верхов — около 30 раз в секунду;
//! сам звук никуда не пишется и не покидает процесс окна.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use tauri::{AppHandle, Emitter, Manager};

const EVENT: &str = "system-audio";
const TICK: Duration = Duration::from_millis(33);
const BASS_HZ: f32 = 150.0;
const MID_HZ: f32 = 2000.0;

/// Полосы громкости 0…1 (RMS) для одного тика.
#[derive(Clone, Copy, serde::Serialize)]
struct Bands {
    bass: f32,
    mid: f32,
    high: f32,
}

/// Фильтры и суммы квадратов за тик: колбэк звука копит, поток тиков забирает.
struct Analyzer {
    low: f32,
    upper: f32,
    low_k: f32,
    upper_k: f32,
    sums: [f32; 3],
    count: u32,
}

impl Analyzer {
    fn new(rate: f32) -> Self {
        let k = |cutoff: f32| 1.0 - (-2.0 * std::f32::consts::PI * cutoff / rate).exp();
        Self {
            low: 0.0,
            upper: 0.0,
            low_k: k(BASS_HZ),
            upper_k: k(MID_HZ),
            sums: [0.0; 3],
            count: 0,
        }
    }

    /// Один моно-отсчёт: одно-полюсные фильтры делят его на басы, середину и верха.
    fn push(&mut self, sample: f32) {
        self.low += self.low_k * (sample - self.low);
        self.upper += self.upper_k * (sample - self.upper);
        let bands = [self.low, self.upper - self.low, sample - self.upper];
        for (sum, value) in self.sums.iter_mut().zip(bands) {
            *sum += value * value;
        }
        self.count += 1;
    }

    fn take(&mut self) -> Bands {
        let n = self.count.max(1) as f32;
        let rms = |sum: f32| (sum / n).sqrt().min(1.0);
        let bands = Bands {
            bass: rms(self.sums[0]),
            mid: rms(self.sums[1]),
            high: rms(self.sums[2]),
        };
        self.sums = [0.0; 3];
        self.count = 0;
        bands
    }
}

/// Работающий захват: флаг остановки потока, который держит поток cpal.
#[derive(Default)]
pub struct SystemAudio(Mutex<Option<Arc<AtomicBool>>>);

/// Начать слушать звук компьютера; уже слушает — ничего не делает.
#[tauri::command]
pub fn system_audio_start(app: AppHandle) -> Result<(), String> {
    let state = app.state::<SystemAudio>();
    let mut slot = state.0.lock().map_err(|e| e.to_string())?;
    if slot.is_some() {
        return Ok(());
    }
    let stop = Arc::new(AtomicBool::new(false));
    let (ready_tx, ready_rx) = std::sync::mpsc::channel::<Result<(), String>>();
    let handle = app.clone();
    let thread_stop = Arc::clone(&stop);
    // cpal::Stream не Send: поток создаёт его, держит и сам отпускает по флагу.
    thread::spawn(move || {
        let result = capture(&handle, &thread_stop);
        if let Err(problem) = result {
            let _ = ready_tx.send(Err(problem));
        }
    });
    match ready_rx.recv_timeout(Duration::from_millis(500)) {
        Ok(Err(problem)) => Err(problem),
        _ => {
            *slot = Some(stop);
            Ok(())
        }
    }
}

/// Перестать слушать.
#[tauri::command]
pub fn system_audio_stop(app: AppHandle) {
    if let Ok(mut slot) = app.state::<SystemAudio>().0.lock() {
        if let Some(stop) = slot.take() {
            stop.store(true, Ordering::Relaxed);
        }
    }
}

fn capture(app: &AppHandle, stop: &AtomicBool) -> Result<(), String> {
    let device = cpal::default_host()
        .default_output_device()
        .ok_or("нет устройства вывода звука")?;
    let config = device.default_output_config().map_err(|e| e.to_string())?;
    let channels = usize::from(config.channels()).max(1);
    let analyzer = Arc::new(Mutex::new(Analyzer::new(config.sample_rate().0 as f32)));
    let feed = Arc::clone(&analyzer);
    // WASAPI: входной поток на устройстве вывода — это loopback (то, что сейчас звучит).
    let stream = device
        .build_input_stream(
            &config.into(),
            move |data: &[f32], _: &cpal::InputCallbackInfo| {
                if let Ok(mut analyzer) = feed.lock() {
                    for frame in data.chunks(channels) {
                        analyzer.push(frame.iter().sum::<f32>() / frame.len() as f32);
                    }
                }
            },
            |error| eprintln!("system audio: {error}"),
            None,
        )
        .map_err(|e| e.to_string())?;
    stream.play().map_err(|e| e.to_string())?;
    while !stop.load(Ordering::Relaxed) {
        thread::sleep(TICK);
        let bands = analyzer
            .lock()
            .map(|mut a| a.take())
            .map_err(|e| e.to_string())?;
        let _ = app.emit(EVENT, bands);
    }
    Ok(())
}
