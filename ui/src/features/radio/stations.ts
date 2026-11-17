/**
 * Станции и настройки радио (ADR-0049, BEHAVIOR §8): список по умолчанию, свои станции пользователя,
 * выбранная станция и громкость — в localStorage. Чистые функции — проверяются тестами.
 */
export interface Station {
  name: string;
  url: string;
}

/** Проверены 2026-11-17: отвечают браузеру потоком MP3/AAC. */
export const DEFAULT_STATIONS: readonly Station[] = [
  { name: "Radio Record", url: "https://radiorecord.hostingradio.ru/rr_main96.aacp" },
  { name: "Record Chillout", url: "https://radiorecord.hostingradio.ru/chil96.aacp" },
  { name: "Record Lo-Fi", url: "https://radiorecord.hostingradio.ru/lofi96.aacp" },
  { name: "Record Synthwave", url: "https://radiorecord.hostingradio.ru/synth96.aacp" },
  { name: "SomaFM Groove Salad", url: "https://ice1.somafm.com/groovesalad-128-mp3" },
  { name: "SomaFM Lush", url: "https://ice2.somafm.com/lush-128-mp3" },
  { name: "Radio Paradise", url: "https://stream.radioparadise.com/mp3-128" },
];

export interface RadioSettings {
  index: number;
  /** 0…1. */
  volume: number;
  custom: Station[];
}

export const RADIO_KEY = "vtuber.radio";
const DEFAULTS: RadioSettings = { index: 0, volume: 0.6, custom: [] };

/** Что играет радио — для спутника и таблички. */
export type RadioMode = "off" | "loading" | "playing" | "paused" | "failed";

export interface RadioFeed {
  mode: RadioMode;
  title: string;
  /** Громкость 0…1 — рот поёт по ней. */
  level: number;
}

export type RadioCommand = "toggle" | "next" | "prev" | "off";

export function isRadioCommand(value: unknown): value is RadioCommand {
  return value === "toggle" || value === "next" || value === "prev" || value === "off";
}

/** Своя станция: только `https:` и непустое имя до 60 знаков; иначе `null`. */
export function station(name: string, url: string): Station | null {
  const title = name.trim().slice(0, 60);
  let parsed: URL;
  try {
    parsed = new URL(url.trim());
  } catch {
    return null;
  }
  if (parsed.protocol !== "https:" || title === "") return null;
  return { name: title, url: parsed.href };
}

export function stationsOf(settings: RadioSettings): Station[] {
  return [...DEFAULT_STATIONS, ...settings.custom];
}

/** Следующая (`+1`) или предыдущая (`-1`) станция по кругу. */
export function step(index: number, delta: number, count: number): number {
  if (count <= 0) return 0;
  return (((index + delta) % count) + count) % count;
}

function field(raw: object, key: string): unknown {
  return new Map<string, unknown>(Object.entries(raw)).get(key);
}

export function parseRadio(text: string | null): RadioSettings {
  let raw: unknown;
  try {
    raw = text === null ? null : JSON.parse(text);
  } catch {
    raw = null;
  }
  if (typeof raw !== "object" || raw === null) return DEFAULTS;
  const list = field(raw, "custom");
  const custom = (Array.isArray(list) ? list : []).flatMap((one: unknown) => {
    if (typeof one !== "object" || one === null) return [];
    const name = field(one, "name");
    const url = field(one, "url");
    const made = typeof name === "string" && typeof url === "string" ? station(name, url) : null;
    return made === null ? [] : [made];
  });
  const index = field(raw, "index");
  const volume = field(raw, "volume");
  const count = DEFAULT_STATIONS.length + custom.length;
  return {
    index: typeof index === "number" && index >= 0 && index < count ? Math.floor(index) : 0,
    volume: typeof volume === "number" && volume >= 0 && volume <= 1 ? volume : DEFAULTS.volume,
    custom,
  };
}

export function loadRadio(storage: Storage | undefined): RadioSettings {
  try {
    return parseRadio(storage?.getItem(RADIO_KEY) ?? null);
  } catch {
    return DEFAULTS;
  }
}

export function saveRadio(storage: Storage | undefined, settings: RadioSettings): void {
  try {
    storage?.setItem(RADIO_KEY, JSON.stringify(settings));
  } catch {
    // Не запомнится — работает до перезапуска.
  }
}
