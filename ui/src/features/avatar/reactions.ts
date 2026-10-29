/**
 * Реакция аватара из состояния разговора (S-8.2). Мгновенный отклик — кивок на `turn.started`
 * (T-17, NFR-03); «думаю» — только если ответа нет дольше порога: быстрый ответ задумчивости не
 * показывает. С голосом ответ «пришёл», когда зазвучал, а не когда пошёл текст.
 */
import type { ConnectionState, Role, TurnPhase } from "../../core";

/** Порог «думаю», мс: бюджет TTFA (NFR-02) — ответ медленнее нормы виден по лицу. */
export const THINKING_AFTER_MS = 800;

export interface ConversationView {
  phase: TurnPhase;
  connection: ConnectionState;
  lastRole: Role | null;
  hasError: boolean;
  /** Голос включён (TTS готов): ждём звука, а не текста. */
  voiceExpected: boolean;
  /** Звук текущего хода уже зазвучал. */
  voiceStarted: boolean;
}

/** Реплика ушла, а ответа ещё не слышно (без голоса — не видно). */
export function isWaiting(view: ConversationView): boolean {
  if (view.phase === "thinking") {
    return true;
  }
  if (view.phase === "speaking") {
    return view.voiceExpected && !view.voiceStarted;
  }
  // Ход ещё не начат. Нет связи или ядро ответило ошибкой — ждать нечего, иначе аватар
  // «думал» бы вечно.
  return view.lastRole === "user" && view.connection === "open" && !view.hasError;
}
