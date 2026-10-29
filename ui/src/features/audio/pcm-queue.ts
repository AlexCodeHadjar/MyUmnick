/**
 * Очередь звука внутри AudioWorklet: фрагменты float в частоте устройства, выдача блоками по 128
 * сэмплов. Чистая логика без WebAudio — тестируется в vitest, работает в потоке аудио.
 *
 * Щелчки: после паузы звук нарастает за `FADE_SAMPLES`; сброс (`flush`) — не обрыв, а затухание
 * за те же `FADE_SAMPLES` (≈ 3 мс при 48 кГц), затем тишина. Отмена хода укладывается в бюджет
 * «≤ 100 мс до тишины» с большим запасом (NFR-04). Звук, пришедший во время затухания (новый
 * ход), не теряется: он ждёт в основной очереди.
 */

/** Длина нарастания и затухания, сэмплов: ~3 мс — неслышно как «ступенька», щелчка нет. */
export const FADE_SAMPLES = 128;

interface Chunk {
  samples: Float32Array;
  /** Метка хода — плеер сообщает её, когда звук хода действительно начал звучать. */
  tag: string;
}

/** Последовательное чтение из списка фрагментов. */
class Cursor {
  chunks: Chunk[] = [];
  #offset = 0;

  get head(): Chunk | undefined {
    return this.chunks[0];
  }

  get size(): number {
    return this.chunks.reduce((sum, chunk) => sum + chunk.samples.length, 0) - this.#offset;
  }

  /** Следующий сэмпл или null, если фрагменты кончились. */
  next(): number | null {
    const head = this.chunks[0];
    if (head === undefined) {
      return null;
    }
    const sample = head.samples[this.#offset] ?? 0;
    this.#offset += 1;
    if (this.#offset >= head.samples.length) {
      this.chunks.shift();
      this.#offset = 0;
    }
    return sample;
  }

  take(): Cursor {
    const taken = new Cursor();
    taken.chunks = this.chunks;
    taken.#offset = this.#offset;
    this.chunks = [];
    this.#offset = 0;
    return taken;
  }
}

export class PcmQueue {
  readonly #fade: number;
  #queue = new Cursor();
  /** Звук, который затухает после `flush`; null — затухания нет. */
  #fading: Cursor | null = null;
  #fadeOutLeft = 0;
  /** Сколько сэмплов нарастания уже прошло; `fade` — нарастание закончено. */
  #fadeIn = 0;
  #playingTag: string | null = null;

  constructor(fade = FADE_SAMPLES) {
    this.#fade = fade;
  }

  /** Сэмплов в очереди (без затухающего хвоста). */
  get buffered(): number {
    return this.#queue.size;
  }

  push(samples: Float32Array, tag: string): void {
    if (samples.length > 0) {
      this.#queue.chunks.push({ samples, tag });
    }
  }

  /** Затухнуть и замолчать: всё, что сейчас в очереди, отбрасывается. */
  flush(): void {
    if (this.#queue.size > 0) {
      this.#fading = this.#queue.take();
      this.#fadeOutLeft = this.#fade;
    }
  }

  /**
   * Заполнить `out` (тишиной, где звука нет). Возвращает метку хода, если в этом блоке его звук
   * начался, — для замера «до первого звука».
   */
  pull(out: Float32Array): string | null {
    let started: string | null = null;
    for (let i = 0; i < out.length; i++) {
      if (this.#fading !== null) {
        out[i] = this.#fadingSample();
        continue;
      }
      const tag = this.#queue.head?.tag;
      const sample = this.#queue.next();
      if (sample === null || tag === undefined) {
        out[i] = 0;
        this.#silence();
        continue;
      }
      if (tag !== this.#playingTag) {
        this.#playingTag = tag;
        started = tag;
      }
      out[i] = sample * this.#fadeInGain();
    }
    return started;
  }

  #fadingSample(): number {
    const sample = this.#fading?.next() ?? null;
    this.#fadeOutLeft -= 1;
    if (sample === null || this.#fadeOutLeft <= 0) {
      this.#fading = null;
      this.#silence();
      return 0;
    }
    return sample * (this.#fadeOutLeft / this.#fade);
  }

  #fadeInGain(): number {
    if (this.#fadeIn < this.#fade) {
      this.#fadeIn += 1;
    }
    return this.#fadeIn / this.#fade;
  }

  /** Пауза: следующий звук начнётся с нарастания и будет считаться новым началом. */
  #silence(): void {
    this.#fadeIn = 0;
    this.#playingTag = null;
  }
}
