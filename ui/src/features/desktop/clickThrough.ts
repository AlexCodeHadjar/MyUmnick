/**
 * Пропуск кликов сквозь пустые области. Окно умеет пропускать клики только целиком, и пока оно их
 * пропускает, событий мыши WebView не получает. Поэтому курсор опрашивается у оболочки, а окно
 * переключается, когда он входит на модель или уходит с неё.
 */
import type { Point, WindowPort } from "./mode";

/** 10 раз в секунду: реакция незаметна глазу, а обращения к оболочке не мешают рендеру (NFR-05). */
export const POLL_MS = 100;

type Port = Pick<WindowPort, "cursor" | "passClicks">;

export class ClickThrough {
  readonly #port: Port;
  /** Над чем окно обязано ловить клики: модель и кнопки. */
  readonly #solid: (point: Point) => boolean;
  /** null — окну ещё ничего не сказано. */
  #passing: boolean | null = null;

  constructor(port: Port, solid: (point: Point) => boolean) {
    this.#port = port;
    this.#solid = solid;
  }

  /** Один опрос; оболочка не ответила — состояние прежнее, следующий опрос попробует снова. */
  async tick(): Promise<void> {
    const pass = !this.#solid(await this.#port.cursor());
    if (pass !== this.#passing) {
      await this.#port.passClicks(pass);
      this.#passing = pass;
    }
  }

  /** Обычному окну нужны все клики. */
  async stop(): Promise<void> {
    this.#passing = null;
    await this.#port.passClicks(false);
  }
}
