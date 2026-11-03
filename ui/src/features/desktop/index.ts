// Публичный API режима «персонаж поверх рабочего стола» (S-15.2).
export { default as DesktopOverlay } from "./DesktopOverlay.svelte";
export {
  DESKTOP_HOTKEY_LABEL,
  isDesktopHotkey,
  loadDesktop,
  saveDesktop,
  type DesktopState,
  type Point,
  type WindowPort,
} from "./mode";
export { tauriWindow } from "./tauriWindow";
