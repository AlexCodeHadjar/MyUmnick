/**
 * Звук компьютера для сферы (Этап 22, ADR-0039): оболочка Tauri слушает выход по умолчанию (WASAPI loopback)
 * и присылает громкость басов, середины и верхов. Здесь — сглаживание и включатель. Значения читает цикл
 * аватара каждый кадр, мимо реактивности Svelte (R-66).
 */
import { invoke, isTauri } from "@tauri-apps/api/core";

export interface AmbientBands {
  bass: number;
  mid: number;
  high: number;
}

export const SILENCE: AmbientBands = { bass: 0, mid: 0, high: 0 };

/** Громкость в полосе мала даже на громкой музыке: усиление до 0…1 с мягким потолком. */
const GAIN: AmbientBands = { bass: 4, mid: 6, high: 10 };
/** Подъём — быстро (удар баса виден сразу), спад — плавно. */
const RISE = 0.6;
const FALL = 0.12;

export function shape(raw: AmbientBands, previous: AmbientBands): AmbientBands {
  const one = (key: keyof AmbientBands): number => {
    const target = 1 - Math.exp(-raw[key] * GAIN[key]);
    const rate = target > previous[key] ? RISE : FALL;
    return previous[key] + (target - previous[key]) * rate;
  };
  return { bass: one("bass"), mid: one("mid"), high: one("high") };
}

function isBands(value: unknown): value is AmbientBands {
  if (typeof value !== "object" || value === null) return false;
  const fields = new Map<string, unknown>(Object.entries(value));
  return ["bass", "mid", "high"].every((key) => typeof fields.get(key) === "number");
}

/** Слушатель звука компьютера; вне Tauri (Vite в браузере) недоступен. */
export class SystemAudio {
  #bands: AmbientBands = SILENCE;
  #unlisten: (() => void) | null = null;

  static get supported(): boolean {
    return isTauri();
  }

  /** Сглаженные полосы последнего тика; выключено — тишина. */
  get bands(): AmbientBands {
    return this.#bands;
  }

  async start(): Promise<void> {
    if (!isTauri() || this.#unlisten !== null) return;
    const { listen } = await import("@tauri-apps/api/event");
    this.#unlisten = await listen<unknown>("system-audio", (event) => {
      if (isBands(event.payload)) this.#bands = shape(event.payload, this.#bands);
    });
    try {
      await invoke("system_audio_start");
    } catch (error) {
      this.#unlisten();
      this.#unlisten = null;
      throw error;
    }
  }

  async stop(): Promise<void> {
    this.#unlisten?.();
    this.#unlisten = null;
    this.#bands = SILENCE;
    if (isTauri()) await invoke("system_audio_stop");
  }
}

const ENABLED_KEY = "vtuber.ambient";

export function readAmbientEnabled(storage: Storage | undefined): boolean {
  try {
    return storage?.getItem(ENABLED_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeAmbientEnabled(storage: Storage | undefined, enabled: boolean): void {
  try {
    storage?.setItem(ENABLED_KEY, enabled ? "1" : "0");
  } catch {
    // Хранилище недоступно — выбор просто не запомнится.
  }
}
