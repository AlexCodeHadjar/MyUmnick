/**
 * Присутствие спутника на экране (ADR-0045): показан ли слой, где главное окно, на каком мониторе
 * пользователь; появление из портала, уход в портал, переход на другой монитор.
 */
import type { Brain } from "../body";
import { followSpot, rectToCss, worldToCss, type Rect, type World } from "../space";
import type { Ports } from "./ports";

/** Главное окно: показано ли и в фокусе, где стоит (физические пиксели). */
export interface MainState {
  shown: boolean;
  focused: boolean;
  rect: Rect;
}

export class Presence {
  readonly #ports: Ports;
  readonly #brain: Brain;
  shown = false;
  /** Главное окно открыто и в фокусе — спутник не нужен (режим «когда окно свёрнуто»). */
  mainShown = true;
  world: World | null = null;
  /** Монитор слоя в физических пикселях: окно приложения приходит в них же. */
  monitor: Rect | null = null;
  scale = devicePixelRatio || 1;
  #mainRect: Rect | null = null;

  constructor(ports: Ports, brain: Brain) {
    this.#ports = ports;
    this.#brain = brain;
  }

  /** Физические пиксели экрана → CSS-пиксели слоя. */
  toCss(rect: Rect): Rect {
    return rectToCss(rect, this.monitor ?? { x: 0, y: 0, w: 0, h: 0 }, this.scale);
  }

  /** Новая картина окон. Вернёт `true`, если пользователь перешёл на другой монитор. */
  setWorld(raw: World): boolean {
    const before = this.monitor;
    this.monitor = raw.monitor;
    this.world = worldToCss(raw, this.scale);
    this.#brain.setWorld(this.world);
    return (
      before !== null &&
      (before.x !== raw.monitor.x || before.y !== raw.monitor.y || before.w !== raw.monitor.w)
    );
  }

  /** Состояние главного окна от оболочки. */
  setMain(state: MainState): void {
    // «Ушли» из окна — свернули его или переключились на другую программу: спутник выходит.
    this.mainShown = state.shown && state.focused;
    // Свёрнутое окно Windows уносит к (−32000, −32000): портал там не открыть — помним последнее
    // видимое место окна (иначе персонаж иногда «не появлялся», падая из-за края экрана).
    if (state.shown && this.#onScreen(state.rect)) this.#mainRect = state.rect;
  }

  /** Показать или спрятать. Вернёт `true`, если спутник только что появился. */
  async show(next: boolean): Promise<boolean> {
    if (next === this.shown) return false;
    this.shown = next;
    if (next) {
      await this.#ports.setVisible(true);
      this.arrive();
      return true;
    }
    if (this.world?.fullscreen === true) {
      this.#brain.hide();
      await this.#ports.setVisible(false);
      return false;
    }
    this.#brain.portalIn();
    return false;
  }

  /** Перешли на другой монитор — уйти в портал и выйти уже там. */
  moveToMonitor(): void {
    this.#mainRect = null;
    this.#brain.hide();
    this.arrive();
  }

  /** Выйти из портала: там, где было окно приложения (внутри экрана), иначе — у активного окна. */
  arrive(): void {
    const world = this.world;
    if (world === null) return;
    const m = world.monitor;
    if (this.#mainRect !== null && !this.mainShown) {
      const rect = this.toCss(this.#mainRect);
      const x = Math.min(m.x + m.w - 80, Math.max(m.x + 80, rect.x + rect.w * 0.75));
      const y = Math.min(m.y + m.h - 80, Math.max(m.y + 260, rect.y + rect.h * 0.5));
      this.#brain.portalOut(x, y);
      return;
    }
    const list = this.#brain.surfaceList;
    const spot =
      followSpot(world, list, world.focus) ?? followSpot(world, list, { kind: "desktop" });
    if (spot !== null) this.#brain.portalOut(spot.x, spot.y - 20);
  }

  /** Раз в кадр: ушёл в портал и спрятан — спрятать и слой. */
  tick(): void {
    if (this.#brain.phase === "hidden" && !this.shown) void this.#ports.setVisible(false);
  }

  /** Окно хоть частью на мониторе слоя (физические пиксели экрана). */
  #onScreen(rect: Rect): boolean {
    const m = this.monitor;
    if (m === null) return rect.x > -10000 && rect.y > -10000;
    return (
      rect.x + rect.w > m.x && rect.y + rect.h > m.y && rect.x < m.x + m.w && rect.y < m.y + m.h
    );
  }
}
