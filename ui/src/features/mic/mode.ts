/** Режимы микрофона (S-11.3): всегда слушать или только пока нажата клавиша. */

export type MicMode = "off" | "always" | "push";

export const MIC_MODES: readonly { value: MicMode; label: string }[] = [
  { value: "off", label: "выключен" },
  { value: "always", label: "всегда слушать" },
  { value: "push", label: "пока нажата F9" },
];

/** Тишина после отпускания клавиши: чуть дольше паузы конца фразы в ядре — фраза закрывается сразу. */
export const TRAILING_SILENCE_MS = 1000;

export function parseMode(value: string | null): MicMode {
  return MIC_MODES.find((mode) => mode.value === value)?.value ?? "off";
}

export function isPushToTalk(event: { code: string }): boolean {
  return event.code === "F9";
}
