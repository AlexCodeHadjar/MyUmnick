// Публичный API фичи ресурсов: панель и её горячая клавиша (R-63).
import { messagesFor } from "../../core";
export { default as ResourcesPanel } from "./ResourcesPanel.svelte";

type KeyInfo = Pick<KeyboardEvent, "code" | "ctrlKey" | "shiftKey" | "altKey" | "metaKey">;

export const RESOURCES_HOTKEY_LABEL = messagesFor("ru").resources.hotkey;

/** По `code`, а не `key`: в русской раскладке `key` для этой клавиши — «Г». */
export function isResourcesHotkey(event: KeyInfo): boolean {
  return (
    event.code === "KeyU" && event.ctrlKey && event.shiftKey && !event.altKey && !event.metaKey
  );
}
