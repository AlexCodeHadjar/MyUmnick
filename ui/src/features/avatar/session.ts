/**
 * Жизнь аватара на сцене: создать рендер, загрузить модель, крутить кадры, следить за размером
 * панели и курсором; всё снять в `dispose()`. Компонент сцены только показывает статус.
 */
import type { AvatarRenderer, AvatarSource, StageSize } from "./AvatarRenderer";
import { gazeAt } from "./live2d/fit";
import { AvatarLoop } from "./loop";

/** Файлы модели `<имя>` в `ui/public/avatars/<имя>/` (ADR-0011). */
export function avatarSource(name: string): AvatarSource {
  const base = `/avatars/${encodeURIComponent(name)}`;
  return {
    modelUrl: `${base}/${encodeURIComponent(name)}.model3.json`,
    mappingUrl: `${base}/mapping.json`,
  };
}

/** Открытие рта 0…1 за прошедшие `deltaMs`; без звука — всегда 0. */
export type MouthSource = (deltaMs: number) => number;

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
      this.#onStatus({ state: "error", message: `Модель «${name}» не загрузилась: ${reason}` });
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
      renderer.setMouth(this.#mouthSource(deltaMs));
      renderer.update(deltaMs);
    });
    this.#loop.start();
    this.#observer = new ResizeObserver(() => {
      renderer.resize(sizeOf(this.#host));
    });
    this.#observer.observe(this.#host);
  }
}
