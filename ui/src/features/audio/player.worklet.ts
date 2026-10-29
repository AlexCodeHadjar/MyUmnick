/**
 * Процессор плеера в потоке аудио: принимает фрагменты float (уже в частоте устройства), отдаёт
 * блоками по 128 сэмплов из `PcmQueue`, сообщает о начале звука хода (замер TTFA).
 * Собирается отдельным модулем (`?worker&url`) и грузится через `audioWorklet.addModule`.
 */
import { PcmQueue } from "./pcm-queue";

export const PROCESSOR_NAME = "vtuber-player";

export type PlayerCommand =
  { type: "push"; samples: Float32Array; tag: string } | { type: "flush" };

function isCommand(data: unknown): data is PlayerCommand {
  if (typeof data !== "object" || data === null || !("type" in data)) {
    return false;
  }
  if (data.type === "flush") {
    return true;
  }
  return (
    data.type === "push" &&
    "samples" in data &&
    data.samples instanceof Float32Array &&
    "tag" in data &&
    typeof data.tag === "string"
  );
}

class PlayerProcessor extends AudioWorkletProcessor {
  readonly #queue = new PcmQueue();

  constructor() {
    super();
    this.port.onmessage = (event: MessageEvent<unknown>) => {
      const command = event.data;
      if (!isCommand(command)) {
        return;
      }
      if (command.type === "flush") {
        this.#queue.flush();
      } else {
        this.#queue.push(command.samples, command.tag);
      }
    };
  }

  process(_inputs: Float32Array[][], outputs: Float32Array[][]): boolean {
    const channels = outputs[0] ?? [];
    const [first, ...rest] = channels;
    if (first === undefined) {
      return true;
    }
    const started = this.#queue.pull(first);
    for (const channel of rest) {
      channel.set(first);
    }
    if (started !== null) {
      this.port.postMessage({ type: "started", tag: started });
    }
    // true — процессор живёт всё время: тишина между репликами — тоже его работа.
    return true;
  }
}

registerProcessor(PROCESSOR_NAME, PlayerProcessor);
