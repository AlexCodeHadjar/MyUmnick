// Публичный API оформления (ADR-0047; R-63): панель с цветовым кругом и применение темы при старте.
export { default as ThemePanel } from "./ThemePanel.svelte";
export { applyTheme, loadTheme, THEME_KEY } from "./palette";
