/**
 * Жизнь аватара на сцене: создать рендер, загрузить модель, крутить кадры, следить за размером
 * панели и курсором; всё снять в `dispose()`. Компонент сцены только показывает статус. Каждый
 * кадр: эмоция с затуханием (`mood.ts`), рот из звука, шаг модели.
 */
import { locale } from "../../core";
import type { AvatarRenderer, AvatarSource, StageSize } from "./AvatarRenderer";
import { gazeAt } from "./live2d/fit";
import { AvatarLoop } from "./loop";
import { Mood } from "./mood";

/** Файлы модели `<имя>` в `ui/public/avatars/<имя>/` (ADR-0011). */
/** Полосы звука компьютера 0…1 (Этап 22). */
export type AmbientSource = () => { bass: number; mid: number; high: number };
const QUIET = { bass: 0, mid: 0, high: 0 };

export function avatarSource(name: string): AvatarSource {
  const base = `/avatars/${encodeURIComponent(name)}`;
  return {
    modelUrl: `${base}/${encodeURIComponent(name)}.model3.json`,
    mappingUrl: `${base}/mapping.json`,
  };
}

/** Открытие рта 0…1 за прошедшие `deltaMs`; без звука — всегда 0. */
export type MouthSource = (deltaMs: number) => number;
/** Идёт ли разговор (ход или голос): пока да — эмоция не угасает. */
export type ActivitySource = () => boolean;

export type AvatarStatus =
  { state: "loading" } | { state: "ready" } | { state: "error"; message: string };

/** Создатель рендера: Live2D в окне, фейк в тестах. */
export type RendererFactory = (host: HTMLElement, size: StageSize) => Promise<AvatarRenderer>;

function sizeOf(host: HTMLElement): StageSize {
  return { width: host.clientWidth, height: host.clientHeight };
}

export class AvatarSession {
  readonly #host: HTMLElement;
  readonly #onStatus: (status: AvatarStatus) => void;
  #renderer: AvatarRenderer | null = null;
  #loop: AvatarLoop | null = null;
  #observer: ResizeObserver | null = null;
  #disposed = false;
  #mouthSource: MouthSource = () => 0;
  #ambientSource: AmbientSource = () => QUIET;
  #formSource: () => number = () => 0;
  #activity: ActivitySource = () => false;
  /** Эмоция ответа во времени; `set()` — из store, затухание — в цикле кадров. */
  readonly mood = new Mood();

  constructor(host: HTMLElement, onStatus: (status: AvatarStatus) => void) {
    this.#host = host;
    this.#onStatus = onStatus;
  }

  /** Рендер — для реакций на ход и липсинка (S-6.3, Этап 8); до загрузки — null. */
  get renderer(): AvatarRenderer | null {
    return this.#renderer;
  }

  async start(name: string, create: RendererFactory): Promise<void> {
    this.#onStatus({ state: "loading" });
    try {
      const renderer = await create(this.#host, sizeOf(this.#host));
      if (this.#disposed) {
        renderer.dispose();
        return;
      }
      this.#renderer = renderer;
      await renderer.load(avatarSource(name));
      this.#run(renderer);
      this.#onStatus({ state: "ready" });
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      this.#onStatus({ state: "error", message: locale.t.avatar.failed(name, reason) });
    }
  }

  /** Курсор в координатах окна → взгляд модели. */
  lookAtPointer(clientX: number, clientY: number): void {
    const rect = this.#host.getBoundingClientRect();
    this.#renderer?.lookAt(...gazeAt(clientX, clientY, rect));
  }

  /** Курсор ушёл из окна — взгляд прямо. */
  lookAhead(): void {
    this.#renderer?.lookAt(0, 0);
  }

  /** Источник открытия рта (липсинк, ADR-0003): опрашивается каждый кадр цикла аватара. */
  set mouth(source: MouthSource) {
    this.#mouthSource = source;
  }

  /** Форма рта (ADR-0023); читается после `mouth`, в том же кадре. */
  set mouthForm(source: () => number) {
    this.#formSource = source;
  }

  /** Звук компьютера (Этап 22): опрашивается каждый кадр; рендер без поддержки его не видит. */
  set ambient(source: AmbientSource) {
    this.#ambientSource = source;
  }

  /** Источник «разговор идёт»: опрашивается каждый кадр (затухание эмоции). */
  set activity(source: ActivitySource) {
    this.#activity = source;
  }

  dispose(): void {
    this.#disposed = true;
    this.#observer?.disconnect();
    this.#loop?.stop();
    this.#renderer?.dispose();
    this.#renderer = null;
  }

  #run(renderer: AvatarRenderer): void {
    if (this.#disposed) {
      return;
    }
    this.#loop = new AvatarLoop((deltaMs) => {
      const { emotion, intensity } = this.mood.update(deltaMs, this.#activity());
      renderer.setEmotion(emotion, intensity);
      renderer.setMouth(this.#mouthSource(deltaMs));
      renderer.setMouthForm(this.#formSource());
      renderer.setAmbient?.(this.#ambientSource());
      renderer.update(deltaMs);
    });
    this.#loop.start();
    this.#observer = new ResizeObserver(() => {
      renderer.resize(sizeOf(this.#host));
    });
    this.#observer.observe(this.#host);
  }
}
