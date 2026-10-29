/**
 * Эмоция на лице во времени: держится, пока витюбер говорит, и ещё `holdMs` после; затем за
 * `fadeMs` сила спадает до нуля — лицо возвращается к нейтральному (Этап 8, S-8.2). Новая речь
 * возвращает последнюю эмоцию ответа в полную силу.
 */
import type { Emotion } from "../../core";

export interface MoodConfig {
  /** Сколько держать эмоцию после конца речи, мс. */
  holdMs: number;
  /** За сколько сила спадает от 1 до 0, мс. */
  fadeMs: number;
}

/** Пара фраз тишины — эмоция ещё «про» ответ; дольше — лицо застывает маской. */
export const DEFAULT_MOOD: MoodConfig = { holdMs: 4000, fadeMs: 1500 };

export interface MoodFrame {
  emotion: Emotion;
  /** 0…1; 0 — эмоция угасла, на лице нейтральное. */
  intensity: number;
}

export class Mood {
  readonly #cfg: MoodConfig;
  #emotion: Emotion = "neutral";
  /** Сколько мс тишины прошло с конца речи. */
  #quietMs = 0;

  constructor(cfg: MoodConfig = DEFAULT_MOOD) {
    this.#cfg = cfg;
  }

  /** Эмоция ответа пришла (или сброшена в нейтральную в начале хода). */
  set(emotion: Emotion): void {
    this.#emotion = emotion;
    this.#quietMs = 0;
  }

  /** Шаг кадра: `active` — идёт ход или звучит голос. */
  update(deltaMs: number, active: boolean): MoodFrame {
    this.#quietMs = active ? 0 : this.#quietMs + Math.max(0, deltaMs);
    const { holdMs, fadeMs } = this.#cfg;
    const intensity = Math.max(0, Math.min(1, 1 - (this.#quietMs - holdMs) / fadeMs));
    return intensity > 0
      ? { emotion: this.#emotion, intensity }
      : { emotion: "neutral", intensity: 0 };
  }
}
