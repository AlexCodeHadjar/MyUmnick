/**
 * Замер UI «реплика отправлена → первый символ ответа применён к DOM» — TTFT плюс накладные
 * расходы UI (критерий Этапа 5: ≤ 20 мс сверх TTFT). Снимается в кадре применения дельты, то есть
 * прямо перед отрисовкой.
 */
import type { OutboundMessage } from "./protocol.gen";

export const FIRST_CHAR_SPAN = "ui.first_char";

export class FirstCharProbe {
  readonly #now: () => number;
  #sentAt: number | null = null;
  /** Ход, начатый ядром после отправки; дельты прежнего хода (хвост отменённого) не в счёт. */
  #turn: string | null = null;

  constructor(now: () => number) {
    this.#now = now;
  }

  sent(): void {
    this.#sentAt = this.#now();
    this.#turn = null;
  }

  /** Возвращает замер, мс, когда сообщение несёт первый символ ответа на отправленную реплику. */
  observe(message: OutboundMessage): number | null {
    if (this.#sentAt === null) {
      return null;
    }
    switch (message.type) {
      case "turn.started":
        this.#turn = message.turn;
        return null;
      case "chat.delta":
        return message.turn === this.#turn && message.data.text !== "" ? this.#finish() : null;
      case "turn.finished":
      case "turn.cancelled":
        if (message.turn === this.#turn) this.#reset();
        return null;
      default:
        return null;
    }
  }

  #finish(): number {
    const ms = this.#now() - (this.#sentAt ?? 0);
    this.#reset();
    return ms;
  }

  #reset(): void {
    this.#sentAt = null;
    this.#turn = null;
  }
}

export const FIRST_AUDIO_SPAN = "ui.first_audio";

/**
 * Замер UI «реплика отправлена → звук ответа зазвучал» — настоящий TTFA (NFR-02: p50 ≤ 800 мс):
 * TTFT, нарезка, синтез, сеть и буфер плеера вместе. Конец замера сообщает плеер, когда первый
 * сэмпл хода ушёл в устройство.
 */
export class FirstAudioProbe {
  readonly #now: () => number;
  #sentAt: number | null = null;
  #turn: string | null = null;

  constructor(now: () => number) {
    this.#now = now;
  }

  sent(): void {
    this.#sentAt = this.#now();
    this.#turn = null;
  }

  /** Ход, начатый после отправки: звук прежнего (отменённого) хода не в счёт. */
  observe(message: OutboundMessage): void {
    if (this.#sentAt === null) {
      return;
    }
    if (message.type === "turn.started") {
      this.#turn = message.turn;
    } else if (message.type === "turn.cancelled" && message.turn === this.#turn) {
      this.#sentAt = null;
      this.#turn = null;
    }
  }

  /** Звук хода `turn` зазвучал; замер, мс, — если это ответ на отправленную реплику. */
  started(turn: string): number | null {
    if (this.#sentAt === null || turn !== this.#turn) {
      return null;
    }
    const ms = this.#now() - this.#sentAt;
    this.#sentAt = null;
    this.#turn = null;
    return ms;
  }
}
