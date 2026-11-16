/**
 * Палитра окна из цветового круга (ADR-0047): три цвета — основной, «значения», «акценты» — и глубина
 * фона дают все переменные `theme.css`. Чистые функции: проверяются тестами, применяются за кадр.
 */

/** Точка на круге: оттенок 0…360 и насыщенность 0…1. */
export interface Swatch {
  h: number;
  s: number;
}

export interface Theme {
  main: Swatch;
  value: Swatch;
  hot: Swatch;
  /** 0 — фон почти чёрный, 1 — заметно светлее. */
  depth: number;
}

export interface Preset {
  name: string;
  theme: Theme;
  /** Встроенные не удаляются; их `name` — ключ подписи в словаре (`theme.presets`). */
  builtIn: boolean;
}

/** «Ночь Умника» — палитра по умолчанию (ADR-0046). */
export const DEFAULT_THEME: Theme = {
  main: { h: 247, s: 1 },
  value: { h: 155, s: 0.85 },
  hot: { h: 36, s: 1 },
  depth: 0.2,
};

export const BUILT_IN: readonly Preset[] = [
  { name: "night", theme: DEFAULT_THEME, builtIn: true },
  {
    name: "neon",
    theme: { main: { h: 320, s: 1 }, value: { h: 185, s: 1 }, hot: { h: 55, s: 1 }, depth: 0.15 },
    builtIn: true,
  },
  {
    name: "emerald",
    theme: {
      main: { h: 160, s: 0.8 },
      value: { h: 95, s: 0.8 },
      hot: { h: 45, s: 1 },
      depth: 0.25,
    },
    builtIn: true,
  },
  {
    name: "sunset",
    theme: {
      main: { h: 18, s: 0.95 },
      value: { h: 45, s: 1 },
      hot: { h: 330, s: 0.9 },
      depth: 0.2,
    },
    builtIn: true,
  },
  {
    name: "graphite",
    theme: {
      main: { h: 220, s: 0.15 },
      value: { h: 200, s: 0.6 },
      hot: { h: 40, s: 0.8 },
      depth: 0.3,
    },
    builtIn: true,
  },
];

function hsl(h: number, s: number, l: number, alpha?: number): string {
  const sat = Math.round(Math.min(100, Math.max(0, s)));
  const tail = alpha === undefined ? "" : ` / ${String(alpha)}%`;
  return `hsl(${String(Math.round(h))} ${String(sat)}% ${String(Math.round(l))}%${tail})`;
}

/** Все переменные темы. Насыщенность основного цвета тянет за собой фон, рамки и текст. */
export function themeVars(theme: Theme): Record<string, string> {
  const { h, s } = theme.main;
  const d = Math.min(1, Math.max(0, theme.depth));
  return {
    "--ground": hsl(h, s * 30, 3.5 + d * 8),
    "--glow": hsl(h, s * 60, 17 + d * 12),
    "--band": hsl(h, s * 35, 7 + d * 6),
    "--panel": hsl(h, s * 32, 6 + d * 7, 96),
    "--well": hsl(h, s * 30, 5 + d * 6),
    "--plate": hsl(h, s * 40, 13 + d * 6),
    "--hover": hsl(h, s * 42, 19 + d * 6),
    "--pressed": hsl(h, s * 45, 26 + d * 6),
    "--edge": hsl(h, s * 35, 33),
    "--rule": hsl(h, s * 100, 68),
    "--rule-dim": hsl(h, s * 35, 20 + d * 4),
    "--title": hsl(h, s * 100, 84),
    "--accent": hsl(h, s * 100, 70),
    "--text": hsl(h, s * 25, 93),
    "--faint": hsl(h, s * 12, 61),
    "--value": hsl(theme.value.h, theme.value.s * 100, 65),
    "--hot": hsl(theme.hot.h, theme.hot.s * 100, 64),
  };
}

/** Применить к корню документа: переменные `theme.css` перекрываются инлайн-стилем. */
export function applyTheme(theme: Theme, root: HTMLElement = document.documentElement): void {
  for (const [name, value] of Object.entries(themeVars(theme))) root.style.setProperty(name, value);
}

/** Точка круга → оттенок и насыщенность; красный сверху, по часовой стрелке (как `conic-gradient`). */
export function swatchAt(dx: number, dy: number, radius: number): Swatch {
  const angle = (Math.atan2(dx, -dy) * 180) / Math.PI;
  return { h: (angle + 360) % 360, s: Math.min(1, Math.hypot(dx, dy) / radius) };
}

/** Оттенок и насыщенность → смещение маркера от центра круга. */
export function pointOf(swatch: Swatch, radius: number): { x: number; y: number } {
  const rad = (swatch.h * Math.PI) / 180;
  return { x: Math.sin(rad) * swatch.s * radius, y: -Math.cos(rad) * swatch.s * radius };
}

/** Цвет маркера (яркость 60%) в `#rrggbb`: показ и ручной ввод в поле. */
export function toHex(swatch: Swatch, lightness = 0.6): string {
  const { h, s } = swatch;
  const a = s * Math.min(lightness, 1 - lightness);
  const channel = (n: number): string => {
    const k = (n + h / 30) % 12;
    const c = lightness - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
    return Math.round(c * 255)
      .toString(16)
      .padStart(2, "0");
  };
  return `#${channel(0)}${channel(8)}${channel(4)}`;
}

/** `#rrggbb` → оттенок и насыщенность (яркость задаёт роль цвета); не цвет — `null`. */
export function fromHex(hex: string): Swatch | null {
  const match = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (match === null) return null;
  const value = Number.parseInt(match[1] ?? "0", 16);
  const r = ((value >> 16) & 255) / 255;
  const g = ((value >> 8) & 255) / 255;
  const b = (value & 255) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  const l = (max + min) / 2;
  const s = delta === 0 ? 0 : delta / (1 - Math.abs(2 * l - 1));
  let h = 0;
  if (delta !== 0) {
    if (max === r) h = 60 * (((g - b) / delta) % 6);
    else if (max === g) h = 60 * ((b - r) / delta + 2);
    else h = 60 * ((r - g) / delta + 4);
  }
  return { h: (h + 360) % 360, s: Math.min(1, s) };
}

/** Ключ текущей темы: другое окно (спутник) узнаёт о смене по событию `storage`. */
export const THEME_KEY = "vtuber.theme";
const PRESETS_KEY = "vtuber.theme.presets";

function swatchOf(raw: unknown): Swatch | null {
  if (typeof raw !== "object" || raw === null) return null;
  const map = new Map<string, unknown>(Object.entries(raw));
  const h = map.get("h");
  const s = map.get("s");
  if (typeof h !== "number" || typeof s !== "number") return null;
  return { h: ((h % 360) + 360) % 360, s: Math.min(1, Math.max(0, s)) };
}

/** Разбор сохранённой темы; чужое или битое — `null`. */
export function parseTheme(raw: unknown): Theme | null {
  if (typeof raw !== "object" || raw === null) return null;
  const map = new Map<string, unknown>(Object.entries(raw));
  const main = swatchOf(map.get("main"));
  const value = swatchOf(map.get("value"));
  const hot = swatchOf(map.get("hot"));
  const depth = map.get("depth");
  if (main === null || value === null || hot === null || typeof depth !== "number") return null;
  return { main, value, hot, depth: Math.min(1, Math.max(0, depth)) };
}

function read(storage: Storage | undefined, key: string): unknown {
  try {
    const text = storage?.getItem(key) ?? null;
    return text === null ? null : JSON.parse(text);
  } catch {
    return null;
  }
}

function write(storage: Storage | undefined, key: string, value: unknown): void {
  try {
    storage?.setItem(key, JSON.stringify(value));
  } catch {
    // Не запомнится — тема работает до перезапуска.
  }
}

export function loadTheme(storage: Storage | undefined): Theme {
  return parseTheme(read(storage, THEME_KEY)) ?? DEFAULT_THEME;
}

export function saveTheme(storage: Storage | undefined, theme: Theme): void {
  write(storage, THEME_KEY, theme);
}

/** Встроенные палитры и свои сохранённые. */
export function loadPresets(storage: Storage | undefined): Preset[] {
  const raw = read(storage, PRESETS_KEY);
  const own: Preset[] = [];
  if (Array.isArray(raw)) {
    const items: unknown[] = raw;
    for (const item of items) {
      if (typeof item !== "object" || item === null) continue;
      const map = new Map<string, unknown>(Object.entries(item));
      const name = map.get("name");
      const theme = parseTheme(map.get("theme"));
      if (typeof name === "string" && name.trim() !== "" && theme !== null) {
        own.push({ name: name.trim().slice(0, 40), theme, builtIn: false });
      }
    }
  }
  return [...BUILT_IN, ...own];
}

function writeOwn(storage: Storage | undefined, own: readonly Preset[]): void {
  write(
    storage,
    PRESETS_KEY,
    own.map((p) => ({ name: p.name, theme: p.theme })),
  );
}

/** Сохранить свою палитру; то же имя — заменить. */
export function savePreset(storage: Storage | undefined, name: string, theme: Theme): Preset[] {
  const clean = name.trim().slice(0, 40);
  const own = loadPresets(storage).filter((p) => !p.builtIn && p.name !== clean);
  writeOwn(storage, clean === "" ? own : [...own, { name: clean, theme, builtIn: false }]);
  return loadPresets(storage);
}

export function deletePreset(storage: Storage | undefined, name: string): Preset[] {
  writeOwn(
    storage,
    loadPresets(storage).filter((p) => !p.builtIn && p.name !== name),
  );
  return loadPresets(storage);
}
