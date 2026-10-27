/**
 * Горячая клавиша панели метрик (FR-15): Ctrl+Shift+M. F12 занят инструментами разработчика
 * WebView2, одиночные буквы — полем ввода чата.
 */
export const METRICS_HOTKEY_LABEL = "Ctrl+Shift+M — метрики";

type KeyInfo = Pick<KeyboardEvent, "code" | "ctrlKey" | "shiftKey" | "altKey" | "metaKey">;

/** По `code`, а не `key`: в русской раскладке `key` для этой клавиши — «Ь». */
export function isMetricsHotkey(event: KeyInfo): boolean {
  return (
    event.code === "KeyM" && event.ctrlKey && event.shiftKey && !event.altKey && !event.metaKey
  );
}
