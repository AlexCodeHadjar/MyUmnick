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
}

export const COMPANION_KEY = "vtuber.companion";
export const HEIGHTS: readonly number[] = [200, 280, 380];
export const DEFAULT_SETTINGS: CompanionSettings = {
  when: "minimized",
  behavior: "follow",
  height: 280,
  hologram: false,
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

/** Виден ли спутник: полный экран прячет его всегда. */
export function shouldShow(
  settings: CompanionSettings,
  mainShown: boolean,
  fullscreen: boolean,
): boolean {
  if (fullscreen || settings.when === "off") return false;
  return settings.when === "always" || !mainShown;
}
