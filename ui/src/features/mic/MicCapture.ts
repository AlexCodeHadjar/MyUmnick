/**
 * Захват микрофона: `getUserMedia` с эхоподавлением браузерного движка (он вычитает то, что играет
 * этот же контекст окна, поэтому витюбер не слышит себя) → AudioWorklet → `MicFramer` → кадр ядру.
 */
import workletUrl from "./capture.worklet?worker&url";
import { MicFramer, MIC_SAMPLE_RATE, type FrameSink } from "./framer";

const CAPTURE_PROCESSOR = "vtuber-mic";

export class MicCapture {
  readonly #stream: MediaStream;
  readonly #context: AudioContext;
  readonly #node: AudioWorkletNode;
  readonly #framer: MicFramer;
  /** Push-to-talk: кадры идут, только пока нажато. */
  #open = true;

  private constructor(
    stream: MediaStream,
    context: AudioContext,
    node: AudioWorkletNode,
    framer: MicFramer,
  ) {
    this.#stream = stream;
    this.#context = context;
    this.#node = node;
    this.#framer = framer;
    node.port.onmessage = (event: MessageEvent<unknown>) => {
      if (this.#open && event.data instanceof Float32Array) {
        framer.push(event.data);
      }
    };
  }

  /** Спрашивает доступ к микрофону; отказ — `DOMException` наружу, его покажет кнопка. */
  static async start(send: FrameSink): Promise<MicCapture> {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    const context = new AudioContext({ latencyHint: "interactive" });
    await context.audioWorklet.addModule(workletUrl);
    const node = new AudioWorkletNode(context, CAPTURE_PROCESSOR, { numberOfOutputs: 0 });
    context.createMediaStreamSource(stream).connect(node);
    await context.resume();
    return new MicCapture(stream, context, node, new MicFramer(context.sampleRate, send));
  }

  get sampleRate(): number {
    return MIC_SAMPLE_RATE;
  }

  /** Пропускать ли звук ядру (push-to-talk); закрытие дописывает тишину — конец фразы сразу. */
  setOpen(open: boolean, trailingSilenceMs: number): void {
    if (this.#open && !open) {
      this.#framer.silence(trailingSilenceMs);
    }
    this.#open = open;
  }

  async stop(): Promise<void> {
    this.#open = false;
    this.#node.port.onmessage = null;
    this.#node.disconnect();
    for (const track of this.#stream.getTracks()) {
      track.stop();
    }
    await this.#context.close();
  }
}
