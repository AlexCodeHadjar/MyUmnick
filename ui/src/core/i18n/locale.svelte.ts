/**
 * Язык интерфейса (Этап 20, ADR-0032). Выставляется по выбранному изданию до подключения к ядру —
 * интерфейс не мигает русским; затем сверяется с `app.edition` ядра.
 */
import { en } from "./en";
import { ru, type Messages } from "./ru";

export type Lang = "ru" | "en";

const DICTIONARIES: Record<Lang, Messages> = { ru, en };

export function isLang(value: unknown): value is Lang {
  return value === "ru" || value === "en";
}

class Locale {
  lang = $state<Lang>("ru");

  /** Словарь текущего языка; чтение в разметке подписывает компонент на смену языка. */
  get t(): Messages {
    return DICTIONARIES[this.lang];
  }

  set(lang: Lang): void {
    this.lang = lang;
    // В тестах (vitest без DOM) документа нет: язык страницы — только в окне.
    if (typeof document !== "undefined") document.documentElement.lang = lang;
  }
}

/** Один на приложение: язык — свойство издания, а не отдельной панели. */
export const locale = new Locale();

/** Словарь языка без реактивности — для тестов и чистых функций. */
export function messagesFor(lang: Lang): Messages {
  return DICTIONARIES[lang];
}
