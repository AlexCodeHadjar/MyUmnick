/**
 * Горячая клавиша панели метрик (FR-15): Ctrl+Shift+M. F12 занят инструментами разработчика
 * WebView2, одиночные буквы — полем ввода чата.
 */
import { messagesFor } from "../../core";
export const METRICS_HOTKEY_LABEL = messagesFor("ru").metrics.hotkey;

type KeyInfo = Pick<KeyboardEvent, "code" | "ctrlKey" | "shiftKey" | "altKey" | "metaKey">;

/** По `code`, а не `key`: в русской раскладке `key` для этой клавиши — «Ь». */
export function isMetricsHotkey(event: KeyInfo): boolean {
  return (
    event.code === "KeyM" && event.ctrlKey && event.shiftKey && !event.altKey && !event.metaKey
  );
}
