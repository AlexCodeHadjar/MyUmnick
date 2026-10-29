/**
 * Липсинк по громкости (ADR-0003): RMS звучащего сигнала → сглаживание → открытие рта 0…1.
 * Рот открывается быстро (атака) и закрывается медленнее (спад) — так он не «дребезжит» на
 * слогах; тихий фон ниже порога рот не шевелит (критерий Этапа 7: «рот не двигается в паузах»).
 */

export interface LipsyncConfig {
  /** Постоянная времени открытия, мс. */
  attackMs: number;
  /** Постоянная времени закрытия, мс. */
  releaseMs: number;
  /** RMS ниже — тишина (шум, хвост реверберации). */
  gate: number;
  /** RMS, при котором рот открыт полностью. */
  fullAt: number;
}

/** Замер S-7.6 на Silero (48 кГц): пик RMS речи ~0.31, паузы между фразами ниже порога. */
export const DEFAULT_LIPSYNC: LipsyncConfig = {
  attackMs: 30,
  releaseMs: 90,
  gate: 0.02,
  fullAt: 0.2,
};

/** Среднеквадратичная громкость блока сэмплов. */
export function rms(samples: Float32Array): number {
  if (samples.length === 0) {
    return 0;
  }
  let sum = 0;
  for (const sample of samples) {
    sum += sample * sample;
  }
  return Math.sqrt(sum / samples.length);
}

export class MouthFollower {
  readonly #cfg: LipsyncConfig;
  #value = 0;

  constructor(cfg: LipsyncConfig = DEFAULT_LIPSYNC) {
    this.#cfg = cfg;
  }

  get value(): number {
    return this.#value;
  }

  /** Новая громкость за `deltaMs`; возвращает сглаженное открытие рта. */
  update(level: number, deltaMs: number): number {
    const { attackMs, releaseMs, gate, fullAt } = this.#cfg;
    const target = level <= gate ? 0 : Math.min(1, (level - gate) / (fullAt - gate));
    const tau = target > this.#value ? attackMs : releaseMs;
    // Экспоненциальное сглаживание, независимое от частоты кадров.
    const k = 1 - Math.exp(-Math.max(0, deltaMs) / tau);
    this.#value += (target - this.#value) * k;
    return this.#value;
  }

  reset(): void {
    this.#value = 0;
  }
}
