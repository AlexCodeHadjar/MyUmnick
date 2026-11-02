/**
 * Звук микрофона → кадры для ядра: ресемплинг в 16 кГц (их ждут VAD и Whisper), s16, ровно 20 мс на
 * кадр. Чистая логика без WebAudio — тестируется в vitest.
 */
import { StreamResampler } from "../../core";

export const MIC_SAMPLE_RATE = 16_000;
/** 20 мс при 16 кГц: мельче — лишние кадры, крупнее — запаздывает реакция на голос. */
export const MIC_FRAME_SAMPLES = 320;
const INT16_MAX = 32767;
const INT16_MIN = -32768;

export type FrameSink = (pcm: Int16Array) => void;

export class MicFramer {
  readonly #resampler: StreamResampler;
  readonly #send: FrameSink;
  #pending = new Int16Array(MIC_FRAME_SAMPLES);
  #filled = 0;

  constructor(inputRate: number, send: FrameSink) {
    this.#resampler = new StreamResampler(inputRate, MIC_SAMPLE_RATE);
    this.#send = send;
  }

  /** Очередной кусок float-сэмплов с микрофона. */
  push(samples: Float32Array): void {
    for (const sample of this.#resampler.process(samples)) {
      const scaled = Math.round(sample * INT16_MAX);
      this.#append(Math.max(INT16_MIN, Math.min(INT16_MAX, scaled)));
    }
  }

  /**
   * Тишина длиной `ms`: push-to-talk отпущен — ядро сразу видит конец фразы и не ждёт настоящих
   * пауз, которых без кадров не будет.
   */
  silence(ms: number): void {
    const samples = Math.round((ms * MIC_SAMPLE_RATE) / 1000);
    for (let i = 0; i < samples; i++) {
      this.#append(0);
    }
  }

  #append(sample: number): void {
    this.#pending[this.#filled] = sample;
    this.#filled += 1;
    if (this.#filled === MIC_FRAME_SAMPLES) {
      this.#send(this.#pending);
      // Кадр уходит в сокет как есть: новый буфер вместо копии.
      this.#pending = new Int16Array(MIC_FRAME_SAMPLES);
      this.#filled = 0;
    }
  }
}
