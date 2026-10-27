/**
 * Применение входящих изменений раз в кадр (T-16, R-65): дельты LLM приходят чаще, чем экран
 * перерисовывается; всё, что пришло за кадр, применяется к store одной пачкой — Svelte
 * обновляет DOM один раз. Цена — до одного кадра (~16 мс) задержки, бюджет UI — 20 мс.
 */

/** Запланировать вызов перед следующей отрисовкой; в окне — `requestAnimationFrame`. */
export type FrameScheduler = (callback: () => void) => void;

export const animationFrame: FrameScheduler = (callback) => {
  requestAnimationFrame(() => {
    callback();
  });
};

/**
 * Очередь изменений до следующего кадра. Порядок сохраняется: смена связи и сообщения ядра идут
 * одной очередью, иначе разрыв «обогнал» бы уже пришедшие дельты.
 */
export class FrameBatch {
  readonly #schedule: FrameScheduler;
  #pending: (() => void)[] = [];

  constructor(schedule: FrameScheduler) {
    this.#schedule = schedule;
  }

  run(change: () => void): void {
    this.#pending.push(change);
    if (this.#pending.length === 1) {
      this.#schedule(() => {
        this.#flush();
      });
    }
  }

  #flush(): void {
    const changes = this.#pending;
    this.#pending = [];
    for (const change of changes) {
      change();
    }
  }
}
