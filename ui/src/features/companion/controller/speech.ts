/**
 * Облачко спутника: ответ ассистента, «Я вас слушаю» и его собственные реплики. Только состояние
 * облачка — что и до какого времени показывать; где — решает вид (`placeBubble`).
 */
import { bubbleText } from "../space";

/** Сколько висит собственная реплика, ответ ассистента после конца речи и «слушаю» (мс). */
const OWN_MS = 6000;
const REPLY_MS = 4000;
const CALL_MS = 5000;

export class Speech {
  #text = "";
  #until = 0;
  #listening = false;
  #own = "";

  /** Позвали по имени: «Я вас слушаю». */
  call(now: number): void {
    this.#listening = true;
    this.#until = now + CALL_MS;
  }

  /** Ассистент говорит: облачко — его текст. Вернёт `true`, если начался новый ответ. */
  reply(text: string, now: number): boolean {
    const fresh =
      text !== this.#text && this.#text !== this.#own && text.length < this.#text.length;
    this.#listening = false;
    this.#text = text;
    this.#until = now + REPLY_MS;
    return fresh;
  }

  /** Своя реплика (её отпустил голос «Разума»). */
  say(text: string, now: number): void {
    this.#listening = false;
    this.#text = text;
    this.#own = text;
    this.#until = now + OWN_MS;
  }

  get listening(): boolean {
    return this.#listening;
  }

  get last(): string {
    return this.#own;
  }

  /** Висит ли сейчас облачко. */
  visible(now: number): boolean {
    return now < this.#until;
  }

  /** Сейчас висит своя реплика (на мышь не оборачивается — занят инициативой). */
  own(now: number): boolean {
    return !this.#listening && this.visible(now) && this.#text === this.#own;
  }

  /** Текст облачка или пустая строка. */
  text(now: number, listeningLabel: string): string {
    if (!this.visible(now)) return "";
    return this.#listening ? listeningLabel : bubbleText(this.#text);
  }
}
