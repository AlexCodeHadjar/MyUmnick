// Публичный API оформления (ADR-0047; R-63): панель с цветовым кругом и применение темы при старте.
export { default as ThemePanel } from "./ThemePanel.svelte";
export { applyTheme, loadTheme, THEME_KEY } from "./palette";

type KeyInfo = Pick<KeyboardEvent, "code" | "ctrlKey" | "shiftKey" | "altKey" | "metaKey">;

/** Ctrl+Shift+L («look») по `code`: в русской раскладке `key` у этой клавиши — «Д». */
export function isThemeHotkey(event: KeyInfo): boolean {
  return (
    event.code === "KeyL" && event.ctrlKey && event.shiftKey && !event.altKey && !event.metaKey
  );
}
