/**
 * Плеер голоса (ADR-0003): кадры ядра → ресемплинг в частоту устройства → AudioWorklet; после
 * него AnalyserNode — липсинк считается из того, что звучит, а не из того, что пришло.
 *
 * Отмена хода сбрасывает очередь с коротким затуханием; кадры отменённого хода, ещё летевшие по
 * сети, отбрасываются (их ход помнится в `#cancelled`). Новый ход вытесняет звук прошлого: ядро
 * синтезирует быстрее реального времени и закрывает ход раньше, чем UI договорит, — отмены для
 * такого хода от ядра уже не будет.
 */
import type { AudioFrame } from "../../core";
import { MouthFollower, rms } from "./lipsync";
import workletUrl from "./player.worklet?worker&url";
import { int16ToFloat, StreamResampler } from "./resample";

const PROCESSOR_NAME = "vtuber-player";
/** Окно анализа громкости: ~21 мс при 48 кГц — меньше кадра экрана, рот не запаздывает. */
const ANALYSER_FFT_SIZE = 1024;
/** Сколько отменённых ходов помнить: поздние кадры приходят в пределах пары ходов. */
const CANCELLED_MEMORY = 16;

export class VoicePlayer {
  readonly #context: AudioContext;
  readonly #node: AudioWorkletNode;
  readonly #analyser: AnalyserNode;
  readonly #window: Float32Array<ArrayBuffer>;
  readonly #mouth = new MouthFollower();
  readonly #cancelled: string[] = [];
  #turn: string | null = null;
  #resampler: StreamResampler | null = null;
  #onStarted: (turn: string) => void = () => undefined;

  private constructor(context: AudioContext, node: AudioWorkletNode, analyser: AnalyserNode) {
    this.#context = context;
    this.#node = node;
    this.#analyser = analyser;
    this.#window = new Float32Array(analyser.fftSize);
    node.port.onmessage = (event: MessageEvent<unknown>) => {
      const data = event.data;
      if (
        typeof data === "object" &&
        data !== null &&
        "tag" in data &&
        typeof data.tag === "string"
      ) {
        this.#onStarted(data.tag);
      }
    };
  }

  static async create(): Promise<VoicePlayer> {
    const context = new AudioContext({ latencyHint: "interactive" });
    await context.audioWorklet.addModule(workletUrl);
    const node = new AudioWorkletNode(context, PROCESSOR_NAME, { outputChannelCount: [1] });
    const analyser = context.createAnalyser();
    analyser.fftSize = ANALYSER_FFT_SIZE;
    node.connect(analyser);
    analyser.connect(context.destination);
    return new VoicePlayer(context, node, analyser);
  }

  /** Звук хода реально зазвучал (первый сэмпл ушёл в устройство). */
  onStarted(listener: (turn: string) => void): void {
    this.#onStarted = listener;
  }

  /** Браузер не играет звук до жеста пользователя: вызвать на первом нажатии клавиши или мыши. */
  async resume(): Promise<void> {
    if (this.#context.state === "suspended") {
      await this.#context.resume();
    }
  }

  play(frame: AudioFrame): void {
    if (this.#cancelled.includes(frame.turn)) {
      return;
    }
    if (this.#turn !== null && this.#turn !== frame.turn) {
      this.cancel(this.#turn);
    }
    const resampler = this.#resamplerFor(frame);
    const samples = resampler.process(int16ToFloat(frame.pcm));
    if (samples.length === 0) {
      return;
    }
    // Буфер передаётся в поток аудио без копирования.
    this.#node.port.postMessage({ type: "push", samples, tag: frame.turn }, [samples.buffer]);
  }

  /** Оборвать звук: `turn` отменён (null — всё, что звучит: стоп, новая реплика, разрыв). */
  cancel(turn: string | null): void {
    const dropped = turn ?? this.#turn;
    if (dropped !== null) {
      this.#cancelled.push(dropped);
      this.#cancelled.splice(0, Math.max(0, this.#cancelled.length - CANCELLED_MEMORY));
    }
    if (turn === null || turn === this.#turn) {
      this.#node.port.postMessage({ type: "flush" });
      this.#turn = null;
      this.#resampler = null;
    }
  }

  /** Открытие рта 0…1 по звучащему сигналу; звать раз в кадр с временем от прошлого вызова. */
  mouth(deltaMs: number): number {
    this.#analyser.getFloatTimeDomainData(this.#window);
    return this.#mouth.update(rms(this.#window), deltaMs);
  }

  async dispose(): Promise<void> {
    this.#node.disconnect();
    this.#analyser.disconnect();
    await this.#context.close();
  }

  #resamplerFor(frame: AudioFrame): StreamResampler {
    const current = this.#resampler;
    if (current !== null && this.#turn === frame.turn && current.fromRate === frame.sampleRate) {
      return current;
    }
    this.#turn = frame.turn;
    this.#resampler = new StreamResampler(frame.sampleRate, this.#context.sampleRate);
    return this.#resampler;
  }
}
