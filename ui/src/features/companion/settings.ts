/**
 * Настройки «Сопровождения» (Этап 23, ADR-0045): общие для главного окна и слоя спутника через
 * localStorage (одно происхождение; событие `storage` доходит до другого окна).
 */
export type CompanionWhen = "off" | "minimized" | "always";
export type CompanionBehavior = "follow" | "stay" | "wander";

export interface CompanionSettings {
  /** Когда спутник на экране: выключен, когда окно свёрнуто или в трее, всегда. */
  when: CompanionWhen;
  behavior: CompanionBehavior;
  /** Рост на экране, CSS-пиксели (решение пользователя — 280). */
  height: number;
  /** «Не мешать кликам»: клики всегда проходят сквозь персонажа. */
  hologram: boolean;
  /** «Спокойнее» (ADR-0052): реже гуляет и говорит, не тычет — просто рядом. */
  calm: boolean;
}

export const DESKTOP_REACTIONS = {
  duration: 1800,
  download: { chance: 0.65, cooldown: 45_000 },
  // Ctrl+S и Win+D — действия, на которые пользователь ждёт ответа: почти всегда (просьба 2026-11-18).
  paste: { chance: 1, cooldown: 2500 },
  copy: { chance: 1, cooldown: 2500 },
  screenshot: { chance: 0.65, cooldown: 45_000 },
  close: { chance: 1, cooldown: 2500 },
  desktop: { chance: 1, cooldown: 2500 },
  /** Win+D уносит окно из-под ног — реакция ждёт приземления, мс. */
  landWaitMs: 5000,
};

export const KEEPSAKE_TIMING = {
  findMs: 160_000,
  findChance: 0.45,
  recallChance: 0.25,
  inspectMs: 4000,
  /** Последняя секунда находки — финал: в карман, обратно или в корзину (кадры FRAMES-6). */
  endingMs: 1000,
  /** Бросил в корзину — потом отряхивает руки. */
  throwMs: 700,
  dustMs: 900,
  /** Сцены постройки и записок (`build_1…4`, `note_put_1…3`, `note_take_1…3`), секунды. */
  buildS: 2.2,
  noteS: 1.4,
  noteMs: 30 * 60_000,
  noteChance: 0.45,
  accountMs: 10000,
  activeMs: 60000,
  stepSecs: 900,
};

export const COMPANION_KEY = "vtuber.companion";
export const DIVERSION = {
  idleMs: 30000,
  cooldown: 65000,
  chance: 0.6,
  tripChance: 0.015,
  /** Споткнулся, упал, сел (`trip_1…4`, FRAMES-6): кадры по разу и пауза на последнем. */
  tripMs: 1600,
} as const;
export const TOUCH = {
  gapMs: 350,
  windowMs: 1300,
  turns: 3,
  petCooldown: 3500,
  reachCooldown: 14000,
  reachChance: 0.55,
} as const;
export const HEIGHTS: readonly number[] = [200, 280, 380];
export const DEFAULT_SETTINGS: CompanionSettings = {
  when: "minimized",
  behavior: "follow",
  height: 280,
  hologram: false,
  calm: false,
};

function field(raw: object, key: string): unknown {
  return new Map<string, unknown>(Object.entries(raw)).get(key);
}

/** Разбор сохранённого: чужое или битое — умолчания. */
export function parseSettings(text: string | null): CompanionSettings {
  let raw: unknown;
  try {
    raw = text === null ? null : JSON.parse(text);
  } catch {
    raw = null;
  }
  if (typeof raw !== "object" || raw === null) return DEFAULT_SETTINGS;
  const when = field(raw, "when");
  const behavior = field(raw, "behavior");
  const height = field(raw, "height");
  return {
    when:
      when === "off" || when === "always" || when === "minimized" ? when : DEFAULT_SETTINGS.when,
    behavior:
      behavior === "stay" || behavior === "wander" || behavior === "follow"
        ? behavior
        : DEFAULT_SETTINGS.behavior,
    height:
      typeof height === "number" && height >= 120 && height <= 600
        ? height
        : DEFAULT_SETTINGS.height,
    hologram: field(raw, "hologram") === true,
    calm: field(raw, "calm") === true,
  };
}

export function loadSettings(storage: Storage | undefined): CompanionSettings {
  try {
    return parseSettings(storage?.getItem(COMPANION_KEY) ?? null);
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(storage: Storage | undefined, settings: CompanionSettings): void {
  try {
    storage?.setItem(COMPANION_KEY, JSON.stringify(settings));
  } catch {
    // Не запомнится — работает до перезапуска.
  }
}

/**
 * Виден ли спутник. Полный экран его больше не прячет (просьба пользователя 2026-11-17: виден всегда, в
 * любой программе) — там он садится в угол: смотрит видео вместе или тихо сидит.
 */
export function shouldShow(settings: CompanionSettings, mainShown: boolean): boolean {
  if (settings.when === "off") return false;
  return settings.when === "always" || !mainShown;
}
