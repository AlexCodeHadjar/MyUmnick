/**
 * PCM s16 голоса → float в частоте AudioContext. Линейная интерполяция с сохранением положения и
 * последнего сэмпла между кадрами: стык фрагментов непрерывен, без щелчков на границах кадров.
 * Для речи 22–48 кГц → частота устройства линейной интерполяции достаточно; WebAudio ресемплит
 * только целые буферы, а не поток.
 */

const INT16_SCALE = 32768;

/** Сэмплы s16 → float [-1, 1). */
export function int16ToFloat(pcm: Int16Array): Float32Array {
  const out = new Float32Array(pcm.length);
  for (let i = 0; i < pcm.length; i++) {
    out[i] = (pcm[i] ?? 0) / INT16_SCALE;
  }
  return out;
}

export class StreamResampler {
  readonly fromRate: number;
  readonly toRate: number;
  readonly #step: number;
  /**
   * Позиция следующего выходного сэмпла в индексах текущего входа; -1…0 — между последним
   * сэмплом прошлого входа (`#last`) и первым текущего.
   */
  #position = 0;
  #last = 0;

  constructor(fromRate: number, toRate: number) {
    this.fromRate = fromRate;
    this.toRate = toRate;
    this.#step = fromRate / toRate;
  }

  /** Следующий кусок потока; длина выхода ≈ длина входа × toRate / fromRate. */
  process(input: Float32Array): Float32Array {
    if (this.fromRate === this.toRate || input.length === 0) {
      return input;
    }
    const out: number[] = [];
    let position = this.#position;
    // Правый сосед `floor(position) + 1` обязан быть внутри входа.
    while (position < input.length - 1) {
      const left = Math.floor(position);
      const a = left < 0 ? this.#last : (input[left] ?? 0);
      const b = input[left + 1] ?? 0;
      out.push(a + (b - a) * (position - left));
      position += this.#step;
    }
    this.#position = position - input.length;
    this.#last = input[input.length - 1] ?? 0;
    return Float32Array.from(out);
  }

  /** Новый ход: стык с прошлым звуком не нужен. */
  reset(): void {
    this.#position = 0;
    this.#last = 0;
  }
}
