/**
 * Процессор плеера в потоке аудио: принимает фрагменты float (уже в частоте устройства), отдаёт
 * блоками по 128 сэмплов из `PcmQueue`, сообщает о начале звука хода (замер TTFA), о том, сколько
 * его сыграно (субтитры), и о тишине («говорит» кончилось).
 * Собирается отдельным модулем (`?worker&url`) и грузится через `audioWorklet.addModule`.
 */
import type { PlayerEvent } from "./events";
import { PcmQueue } from "./pcm-queue";

export const PROCESSOR_NAME = "vtuber-player";
/** Прогресс — раз в 8 блоков (≈ 21 мс при 48 кГц): чаще кадра экрана не нужно. */
const PROGRESS_BLOCKS = 8;

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
  #blocks = 0;
  #wasPlaying = false;

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
      this.#post({ type: "started", tag: started });
    }
    this.#report(started !== null);
    // true — процессор живёт всё время: тишина между репликами — тоже его работа.
    return true;
  }

  #report(started: boolean): void {
    const playing = this.#queue.playing;
    const progress = this.#queue.progress;
    this.#blocks += 1;
    if (playing && progress !== null && (started || this.#blocks % PROGRESS_BLOCKS === 0)) {
      this.#post({ type: "progress", ...progress });
    } else if (!playing && this.#wasPlaying) {
      this.#post({ type: "idle" });
    }
    this.#wasPlaying = playing;
  }

  #post(event: PlayerEvent): void {
    this.port.postMessage(event);
  }
}

registerProcessor(PROCESSOR_NAME, PlayerProcessor);
