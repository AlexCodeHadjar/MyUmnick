/**
 * Экран выбора издания (Этап 20, ADR-0032): плитки, фокус, клавиши, запомненный выбор.
 * Логика здесь, разметка — в `EditionPicker.svelte` (компоненты не тестируются автоматически).
 */
import type { Lang } from "../../core";

export type EditionId = "ru" | "en";

export interface Edition {
  id: EditionId;
  lang: Lang;
  name: string;
  caption: string;
  badge: string | null;
  /** Нужно ли разовое подтверждение возраста перед первым запуском. */
  adult: boolean;
}

/** Порядок плиток; новое издание — строка здесь и файл `config/editions/<id>.toml`. */
export const EDITIONS: readonly Edition[] = [
  { id: "ru", lang: "ru", name: "Умник", caption: "Русский", badge: null, adult: false },
  {
    id: "en",
    lang: "en",
    name: "Umnik",
    caption: "English · Uncensored",
    badge: "18+",
    adult: true,
  },
];

/** Что окно помнит между запусками (`launcher.json` в папке настроек приложения). */
export interface LauncherState {
  last: EditionId;
  remember: boolean;
  /** Дата подтверждения 18+ (ISO) или пусто. */
  adultConfirmed: string;
}

export const DEFAULT_LAUNCHER: LauncherState = { last: "ru", remember: false, adultConfirmed: "" };

export function isEditionId(value: unknown): value is EditionId {
  return value === "ru" || value === "en";
}

const RU_EDITION: Edition = {
  id: "ru",
  lang: "ru",
  name: "Умник",
  caption: "Русский",
  badge: null,
  adult: false,
};

export function editionById(id: EditionId): Edition {
  return EDITIONS.find((edition) => edition.id === id) ?? RU_EDITION;
}

/** Плитка по номеру; номер вне ряда — первая плитка. */
export function editionAt(index: number): Edition {
  return EDITIONS[index] ?? RU_EDITION;
}

function field(raw: object, key: string): unknown {
  return new Map<string, unknown>(Object.entries(raw)).get(key);
}

/** Разбор сохранённого состояния: битое или чужое — умолчания, а не сбой запуска. */
export function parseLauncher(raw: unknown): LauncherState {
  if (typeof raw !== "object" || raw === null) return DEFAULT_LAUNCHER;
  const last = field(raw, "last");
  const confirmed = field(raw, "adultConfirmed");
  return {
    last: isEditionId(last) ? last : DEFAULT_LAUNCHER.last,
    remember: field(raw, "remember") === true,
    adultConfirmed: typeof confirmed === "string" ? confirmed : "",
  };
}

/** Показывать ли экран: при «запоминать» — нет, если не попросили сменить издание явно. */
export function needsPicker(state: LauncherState, forced: boolean): boolean {
  return forced || !state.remember;
}

/** Нужно ли подтверждение возраста для выбранного издания. */
export function needsAgeGate(edition: Edition, state: LauncherState): boolean {
  return edition.adult && state.adultConfirmed === "";
}

export type PickerAction =
  { kind: "focus"; index: number } | { kind: "start"; index: number } | null;

/** Клавиши экрана: ←/→ — фокус по кругу, Enter/Пробел — запуск, 1…9 — сразу плитка. */
export function keyAction(key: string, focused: number, count: number): PickerAction {
  if (key === "ArrowRight") return { kind: "focus", index: (focused + 1) % count };
  if (key === "ArrowLeft") return { kind: "focus", index: (focused - 1 + count) % count };
  if (key === "Enter" || key === " ") return { kind: "start", index: focused };
  const digit = Number.parseInt(key, 10);
  if (Number.isInteger(digit) && digit >= 1 && digit <= count) {
    return { kind: "start", index: digit - 1 };
  }
  return null;
}

/** Состояние после выбора: издание запоминается как последнее, подтверждение — с датой. */
export function afterPick(
  state: LauncherState,
  edition: Edition,
  remember: boolean,
  today: string,
): LauncherState {
  const adultConfirmed =
    edition.adult && state.adultConfirmed === "" ? today : state.adultConfirmed;
  return { last: edition.id, remember, adultConfirmed };
}
