/** Режимы микрофона (S-11.3): всегда слушать или только пока нажата клавиша. */

import { messagesFor, type Messages } from "../../core";

export type MicMode = "off" | "always" | "push";

export const MIC_MODE_VALUES: readonly MicMode[] = ["off", "always", "push"];

/** Режимы с подписями на языке издания. */
export function micModes(t: Messages = messagesFor("ru")): { value: MicMode; label: string }[] {
  return MIC_MODE_VALUES.map((value) => ({ value, label: t.mic[value] }));
}

/** Тишина после отпускания клавиши: чуть дольше паузы конца фразы в ядре — фраза закрывается сразу. */
export const TRAILING_SILENCE_MS = 1000;

export function parseMode(value: string | null): MicMode {
  return MIC_MODE_VALUES.find((mode) => mode === value) ?? "off";
}

export function isPushToTalk(event: { code: string }): boolean {
  return event.code === "F9";
}
