/**
 * Команды чата после «/» (просьба пользователя 2026-11-18): приватный режим и очистка памяти — не кнопки
 * в настройках, а команды. Пока пишется «/слово», под полем — подсказки подходящих команд.
 */

export type CommandId = "private" | "clear";

export interface Command {
  id: CommandId;
  /** Как пишется, без «/». */
  name: string;
  hint: string;
}

/** Подсказки к набранному: только пока в поле одно «/слово» без пробела. */
export function suggest(text: string, commands: readonly Command[]): Command[] {
  const typed = text.trimStart();
  if (!typed.startsWith("/") || /\s/u.test(typed)) return [];
  const word = typed.slice(1).toLowerCase();
  return commands.filter((one) => one.name.startsWith(word));
}

/** Команда, которую набрали целиком (`/private`), или null — обычная реплика. */
export function commandOf(text: string, commands: readonly Command[]): Command | null {
  const typed = text.trim().toLowerCase();
  if (!typed.startsWith("/")) return null;
  return commands.find((one) => `/${one.name}` === typed) ?? null;
}
