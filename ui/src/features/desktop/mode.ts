/**
 * Режим «персонаж поверх рабочего стола» (S-15.2): что включено и как это пережить перезапуск.
 * Окно — за портом: логика проверяется без Tauri, а в браузере режима просто нет.
 */
import { messagesFor } from "../../core";

const STORAGE_KEY = "vtuber.desktop";

/** Размер небольшого окна с моделью, CSS-пиксели: модель видна целиком и не занимает экран. */
export const OVERLAY_SIZE = { width: 360, height: 560 } as const;

export interface DesktopState {
  overlay: boolean;
  pinned: boolean;
}

export interface Point {
  x: number;
  y: number;
}

/** Что режиму нужно от окна. Все вызовы асинхронны: это обращения к оболочке. */
export interface WindowPort {
  enterOverlay(pinned: boolean): Promise<void>;
  leaveOverlay(): Promise<void>;
  setPinned(pinned: boolean): Promise<void>;
  /** Клики идут сквозь окно. */
  passClicks(pass: boolean): Promise<void>;
  startDrag(): Promise<void>;
  /** Курсор относительно окна, CSS-пиксели. */
  cursor(): Promise<Point>;
}

/** Нужное от localStorage: в тестах — словарь. */
export interface DesktopStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

const OFF: DesktopState = { overlay: false, pinned: true };

/** Запись могла испортиться или устареть: тогда обычное окно, а не сюрприз при запуске. */
export function loadDesktop(storage: DesktopStorage | undefined): DesktopState {
  const raw = storage?.getItem(STORAGE_KEY);
  if (raw === null || raw === undefined) {
    return { ...OFF };
  }
  try {
    const saved: unknown = JSON.parse(raw);
    if (typeof saved !== "object" || saved === null) {
      return { ...OFF };
    }
    const overlay = "overlay" in saved && saved.overlay === true;
    const pinned = !("pinned" in saved) || saved.pinned !== false;
    return { overlay, pinned };
  } catch {
    return { ...OFF };
  }
}

export function saveDesktop(storage: DesktopStorage | undefined, state: DesktopState): void {
  storage?.setItem(STORAGE_KEY, JSON.stringify(state));
}

/** Хоткей: окно без рамки, а кнопка может оказаться за краем экрана. */
export function isDesktopHotkey(event: {
  code: string;
  ctrlKey: boolean;
  shiftKey: boolean;
  altKey: boolean;
}): boolean {
  return event.code === "KeyO" && event.ctrlKey && event.shiftKey && !event.altKey;
}

export const DESKTOP_HOTKEY_LABEL = messagesFor("ru").desktop.hotkey;
