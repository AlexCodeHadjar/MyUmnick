/**
 * Режим субтитров (S-8.2): текст ответа появляется вместе с голосом, а не раньше него (текст
 * генерируется в разы быстрее речи). Привязки слов ко времени протокол не даёт, поэтому доля
 * текста = доле звука: пока ход идёт — по темпу речи, когда звук хода получен весь — точно по
 * доле сыгранного. Показанное не убывает: субтитр не «отматывается» при смене оценки.
 */
import type { ChatMessage, SpeechProgress } from "../../core";

/** Темп речи до конца хода, символов на секунду звука: Silero `xenia` — ≈ 18 (замер S-7.6). */
export const SPEECH_CHARS_PER_S = 16;
/** Ключ настройки в localStorage. */
export const SUBTITLES_KEY = "vtuber.chat.subtitles";

/** Нужное от localStorage: в тестах — словарь. */
export type SettingStorage = Pick<Storage, "getItem" | "setItem">;

export interface SubtitleView {
  /** Режим включён и голос есть (TTS готов). */
  enabled: boolean;
  speech: SpeechProgress | null;
}

/** Сколько символов сообщения показать; null — всё сообщение (не субтитр). */
export function revealedLength(message: ChatMessage, view: SubtitleView): number | null {
  if (!view.enabled || message.role !== "assistant") {
    return null;
  }
  const speech = view.speech;
  if (speech?.turn !== message.turn) {
    // Звук этого хода ещё не зазвучал: пока ответ идёт — ждём голос; ход кончился без звука
    // (сбой TTS, отмена) — показать текст.
    return message.status === "streaming" ? 0 : null;
  }
  // Звук смолк: ход кончился — текст целиком; ход идёт (LLM медленнее речи, буфер опустел) —
  // субтитр ждёт продолжения голоса.
  if (!speech.speaking && message.status !== "streaming") {
    return null;
  }
  const length = message.text.length;
  const exact = message.status === "done" && speech.receivedS > 0;
  const rate = exact ? length / speech.receivedS : SPEECH_CHARS_PER_S;
  return Math.min(length, Math.floor(speech.playedS * rate));
}

/** Текст сообщений в режиме субтитров; помнит показанное, чтобы оно не убывало. */
export class Subtitles {
  readonly #shown = new Map<number, number>();

  text(message: ChatMessage, view: SubtitleView): string {
    const revealed = revealedLength(message, view);
    if (revealed === null) {
      // Показан целиком — так и останется (пауза в звуке посреди ответа не прячет текст).
      this.#shown.set(message.id, message.text.length);
      return message.text;
    }
    const shown = Math.max(revealed, this.#shown.get(message.id) ?? 0);
    this.#shown.set(message.id, shown);
    return message.text.slice(0, shown);
  }
}

/** Настройка из хранилища; недоступное хранилище (политика WebView) — режим выключен. */
export function readSubtitles(storage: SettingStorage | undefined): boolean {
  try {
    return storage?.getItem(SUBTITLES_KEY) === "on";
  } catch {
    return false;
  }
}

export function writeSubtitles(storage: SettingStorage | undefined, on: boolean): void {
  try {
    storage?.setItem(SUBTITLES_KEY, on ? "on" : "off");
  } catch {
    // Не запомнится — не беда: режим работает до перезапуска.
  }
}
