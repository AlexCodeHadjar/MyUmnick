/**
 * Реакция аватара из состояния разговора. «Думаю» включается в том же кадре, что и отправка
 * (T-17, NFR-03): реплика пользователя попадает в store сразу, ещё до ответа ядра.
 */
import type { ConnectionState, Role, TurnPhase } from "../../core";
import type { AvatarReaction } from "./AvatarRenderer";

export interface ConversationView {
  phase: TurnPhase;
  connection: ConnectionState;
  lastRole: Role | null;
  hasError: boolean;
}

export function reactionOf(view: ConversationView): AvatarReaction {
  if (view.phase === "thinking") {
    return "thinking";
  }
  // Реплика ушла, ход ещё не начат: ждём ответа. Нет связи или ядро ответило ошибкой —
  // ждать нечего, иначе аватар «думал» бы вечно.
  const waiting =
    view.phase === "idle" &&
    view.lastRole === "user" &&
    view.connection === "open" &&
    !view.hasError;
  return waiting ? "thinking" : "idle";
}
