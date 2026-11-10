// Публичный API редактора памяти (R-63).
import { messagesFor } from "../../core";
export { default as MemoryPanel } from "./MemoryPanel.svelte";

type KeyInfo = Pick<KeyboardEvent, "code" | "ctrlKey" | "shiftKey" | "altKey" | "metaKey">;

export const MEMORY_HOTKEY_LABEL = messagesFor("ru").memory.hotkey;

/** По `code`, а не `key`: в русской раскладке `key` для этой клавиши — «Н». */
export function isMemoryHotkey(event: KeyInfo): boolean {
  return (
    event.code === "KeyY" && event.ctrlKey && event.shiftKey && !event.altKey && !event.metaKey
  );
}
