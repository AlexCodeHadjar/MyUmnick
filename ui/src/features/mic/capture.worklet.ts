/**
 * Процессор захвата: копирует вход микрофона и отдаёт в основной поток пачками. Копия обязательна:
 * буферы `process` браузер переиспользует. Ресемплинг и кадры — в основном потоке (`framer.ts`).
 */

export const CAPTURE_PROCESSOR = "vtuber-mic";
/** Пачка из 4 блоков (≈ 10 мс при 48 кГц): реже сообщений — меньше работы основному потоку. */
const BLOCK_SAMPLES = 128;
const BLOCKS_PER_POST = 4;

class CaptureProcessor extends AudioWorkletProcessor {
  #batch = new Float32Array(BLOCK_SAMPLES * BLOCKS_PER_POST);
  #filled = 0;

  process(inputs: Float32Array[][]): boolean {
    const samples = inputs[0]?.[0];
    if (samples !== undefined) {
      this.#add(samples);
    }
    return true;
  }

  #add(samples: Float32Array): void {
    this.#batch.set(samples, this.#filled);
    this.#filled += samples.length;
    if (this.#filled + BLOCK_SAMPLES > this.#batch.length) {
      const full = this.#batch.subarray(0, this.#filled).slice();
      this.port.postMessage(full, [full.buffer]);
      this.#filled = 0;
    }
  }
}

registerProcessor(CAPTURE_PROCESSOR, CaptureProcessor);
