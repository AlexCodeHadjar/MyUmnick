/** Клавиши поля ввода: Enter — отправить, Shift+Enter — перенос строки, Esc — остановить ответ. */

type KeyInfo = Pick<KeyboardEvent, "key" | "shiftKey" | "isComposing">;

/** Enter во время набора через IME (выбор иероглифа и т. п.) подтверждает ввод, а не отправляет. */
export function isSendKey(event: KeyInfo): boolean {
  return event.key === "Enter" && !event.shiftKey && !event.isComposing;
}

export function isStopKey(event: KeyInfo): boolean {
  return event.key === "Escape" && !event.isComposing;
}
