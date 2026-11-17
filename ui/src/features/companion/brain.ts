/**
 * Поведение спутника (Этап 23, разделы 4–5): где он, что делает и какая поза. Чистая логика без DOM:
 * `tick(dt)` двигает его, `body()` — что нарисовать. Переход между местами — пешком или прыжком, если
 * близко, молнией, если далеко (решение пользователя); бросок мышью — полёт с отскоками, как у Capri.
 */
import {
  below,
  hostId,
  sameSurface,
  snap,
  spotOn,
  surfaces,
  type Pose,
  type Spot,
  type Surface,
} from "./anchors";
import type { Rect, World } from "./world";

export type Phase =
  "hidden" | "rest" | "walk" | "jump" | "fall" | "held" | "bolt" | "portal_out" | "portal_in";

export type Effect =
  | { kind: "bolt"; from: [number, number]; to: [number, number]; t: number }
  | { kind: "portal"; x: number; y: number; t: number; opening: boolean }
  | { kind: "sparks"; x: number; y: number; t: number };

export interface Body {
  phase: Phase;
  x: number;
  y: number;
  pose: Pose;
  facing: 1 | -1;
  /** 0…1: портал «вытягивает» персонажа из точки и втягивает обратно. */
  scale: number;
  effects: Effect[];
}

/** Ближе — пешком или прыжком, дальше — молнией (решение пользователя, раздел 9.1). */
export const WALK_LIMIT = 300;
const WALK_SPEED = 140;
const GRAVITY = 2600;
const WALL_BOUNCE = 0.55;
const FLOOR_BOUNCE = 0.42;
const MAX_SPEED = 2500;
const BOLT_S = 0.35;
const JUMP_S = 0.6;
const PORTAL_S = 0.6;
const SPARKS_S = 0.5;
const LAY_AFTER_S = 90;
const SLEEP_AFTER_S = 300;

type Random = () => number;

export class Brain {
  phase: Phase = "hidden";
  x = 0;
  y = 0;
  facing: 1 | -1 = 1;
  #vx = 0;
  #vy = 0;
  #spot: Spot | null = null;
  /** Сдвиг от левого края окна-хозяина: окно двигают — персонаж едет вместе с ним. */
  #rel = 0;
  #pinned: Pose | null = null;
  #pinAfter: { pose: Pose; facing: 1 | -1 } | null = null;
  #from: [number, number] = [0, 0];
  #target: Spot | null = null;
  #point: [number, number] = [0, 0];
  #t = 0;
  #idle = 0;
  #wanderIn = 10;
  #surfaces: Surface[] = [];
  #bounds: Rect = { x: 0, y: 0, w: 1920, h: 1080 };
  #effects: Effect[] = [];
  #random: Random;
  wander = false;
  /** «Следовать»: гуляет реже и недалеко; «Гулять» — часто. */
  calm = false;
  #lookIn = 6;
  /** Высота груди над точкой опоры: отсюда выходит молния и искры (рост × 0,55). */
  chest = 150;

  constructor(random: Random = Math.random) {
    this.#random = random;
  }

  /** Сколько секунд стоит на месте без дела: для комментариев «мне скучно». */
  get idleSeconds(): number {
    return this.#idle;
  }

  get spot(): Spot | null {
    return this.#spot;
  }

  get surfaceList(): readonly Surface[] {
    return this.#surfaces;
  }

  /** Новая картина рабочего стола: опоры пересчитываются, ушедшее из-под ног окно — падение. */
  setWorld(world: World): void {
    this.#surfaces = surfaces(world);
    this.#bounds = world.monitor;
    const spot = this.#spot;
    if (this.phase !== "rest" || spot === null) return;
    const host = hostId(spot.surface);
    const seat = host === null ? null : world.seats.find((one) => one.id === host);
    const same = this.#surfaces.filter((surface) => sameSurface(surface, spot.surface));
    if (host !== null && seat === undefined) {
      this.#fall();
      return;
    }
    const x = seat ? seat.rect.x + this.#rel : this.x;
    const again = same.length > 0 ? snap(same, x, seat ? seat.rect.y : this.y, 80) : null;
    if (again === null) this.#fall();
    else this.#rest(again);
  }

  /** Окно-хозяин сдвинулось (`companion-host`, быстро) или исчезло. */
  hostMoved(id: number, rect: Rect | null): void {
    const spot = this.#spot;
    if (this.phase !== "rest" || spot === null || hostId(spot.surface) !== id) return;
    if (spot.surface.kind !== "edge" && spot.surface.kind !== "side") return;
    if (rect === null) {
      this.#fall();
      return;
    }
    this.x =
      spot.surface.kind === "side" && spot.surface.side === "right"
        ? rect.x + rect.w
        : rect.x + this.#rel;
    if (spot.surface.kind === "edge") this.y = rect.y;
  }

  /** Встать на место сразу (первый показ, Shift + отпустить). */
  place(spot: Spot): void {
    this.#rest(spot);
  }

  /** Перейти на место: близко — пешком или прыжком, далеко — молнией. */
  goTo(spot: Spot): void {
    if (this.phase === "held" || this.phase === "hidden") return;
    const distance = Math.hypot(spot.x - this.x, spot.y - this.y);
    if (distance < 4) return;
    if (distance >= WALK_LIMIT) {
      this.bolt(spot, [spot.x, spot.y]);
      return;
    }
    const level = this.#spot !== null && sameSurface(this.#spot.surface, spot.surface);
    this.#start(level ? "walk" : "jump", spot);
  }

  /** Перенос молнией: разряд бежит по молнии, персонаж собирается в цели (или падает, если опоры нет). */
  bolt(target: Spot | null, point: [number, number]): void {
    this.#effects.push({ kind: "sparks", x: this.x, y: this.y - this.chest, t: 0 });
    this.#effects.push({ kind: "bolt", from: [this.x, this.y - this.chest], to: point, t: 0 });
    this.#target = target;
    this.#point = point;
    this.#t = 0;
    this.phase = "bolt";
  }

  /**
   * Подлететь молнией к точке на экране и замереть там в позе `pose` (ADR-0048): кончик пальца — в
   * точке. Опоры нет — до следующего перехода (`goTo`) персонаж висит, не падая.
   */
  visit(x: number, y: number, pose: Pose, facing: 1 | -1): void {
    if (this.phase === "held" || this.phase === "hidden") return;
    this.bolt(null, [x, y]);
    this.#pinAfter = { pose, facing };
  }

  /** Персонажа взяли мышью: висит за «шиворот» у курсора. */
  hold(px: number, py: number): void {
    this.phase = "held";
    this.#spot = null;
    this.#pinned = null;
    this.moveHeld(px, py);
  }

  moveHeld(px: number, py: number): void {
    if (this.phase !== "held") return;
    if (Math.abs(px - this.x) > 1) this.facing = px > this.x ? 1 : -1;
    this.x = px;
    this.y = py;
  }

  /** Отпустили с разгона: полёт с отскоками. */
  toss(vx: number, vy: number): void {
    const speed = Math.hypot(vx, vy);
    const k = speed > MAX_SPEED ? MAX_SPEED / speed : 1;
    this.#fall();
    this.#vx = vx * k;
    this.#vy = vy * k;
  }

  /** Ctrl + отпустить: повиснуть прямо здесь (как у Capri). */
  hang(px: number, py: number): void {
    this.phase = "rest";
    this.#spot = null;
    this.#pinned = "hang_side";
    this.x = px;
    this.y = py;
    this.#idle = 0;
  }

  /** Выйти из портала в точке (окно свернули): персонаж «вытягивается», затем опускается на опору. */
  portalOut(x: number, y: number): void {
    this.x = x;
    this.y = y;
    this.#spot = null;
    this.#pinned = null;
    this.#effects.push({ kind: "portal", x, y: y - 120, t: 0, opening: true });
    this.#t = 0;
    this.phase = "portal_out";
  }

  /** Уйти в портал (окно развернули); по окончании — `hidden`. */
  portalIn(): void {
    if (this.phase === "hidden") return;
    this.#effects.push({ kind: "portal", x: this.x, y: this.y - 120, t: 0, opening: false });
    this.#t = 0;
    this.phase = "portal_in";
  }

  hide(): void {
    this.phase = "hidden";
    this.#effects = [];
  }

  /** Разговор, зов, движение мыши рядом: сон и лежание сбрасываются. */
  wake(): void {
    this.#idle = 0;
  }

  tick(dt: number): void {
    const step = Math.min(dt, 0.05);
    this.#t += step;
    this.#effects = this.#effects
      .map((effect) => ({ ...effect, t: effect.t + step / this.#effectLength(effect) }))
      .filter((effect) => effect.t < 1);
    if (this.phase === "rest") this.#tickRest(step);
    else if (this.phase === "walk") this.#tickWalk(step);
    else if (this.phase === "jump") this.#tickJump();
    else if (this.phase === "fall") this.#tickFall(step);
    else if (this.phase === "bolt") this.#tickBolt();
    else if (this.phase === "portal_out" && this.#t >= PORTAL_S) this.#fall();
    else if (this.phase === "portal_in" && this.#t >= PORTAL_S) this.hide();
  }

  body(): Body {
    return {
      phase: this.phase,
      x: this.x,
      y: this.y,
      pose: this.#pose(),
      facing: this.facing,
      scale: this.#scale(),
      effects: this.#effects,
    };
  }

  #effectLength(effect: Effect): number {
    if (effect.kind === "bolt") return BOLT_S;
    if (effect.kind === "portal") return PORTAL_S * 1.4;
    return SPARKS_S;
  }

  #scale(): number {
    const s = Math.min(1, this.#t / PORTAL_S);
    if (this.phase === "portal_out") return s;
    if (this.phase === "portal_in") return 1 - s;
    if (this.phase === "bolt") return this.#t < BOLT_S ? 0 : 1;
    return 1;
  }

  #pose(): Pose {
    if (this.#pinned !== null) return this.#pinned;
    if (this.phase === "held") return "held";
    if (this.phase === "walk") return "walk";
    if (this.phase === "jump" || this.phase === "fall" || this.phase.startsWith("portal"))
      return "float";
    const pose = this.#spot?.pose ?? "float";
    if (
      this.#idle > SLEEP_AFTER_S &&
      (pose === "sit_edge" || pose === "stand" || pose === "sit_corner")
    ) {
      return "sleep";
    }
    if (this.#idle > LAY_AFTER_S && (pose === "sit_edge" || pose === "stand")) return "laydown";
    return pose;
  }

  #rest(spot: Spot): void {
    this.phase = "rest";
    this.#spot = spot;
    this.#pinned = null;
    this.x = spot.x;
    this.y = spot.y;
    this.facing = spot.facing;
    this.#vx = 0;
    this.#vy = 0;
    const surface = spot.surface;
    this.#rel = surface.kind === "edge" ? spot.x - this.#hostLeft(surface) : 0;
  }

  #hostLeft(surface: Surface): number {
    if (surface.kind !== "edge") return 0;
    // Левый край окна — по любой опоре того же хозяина: открытые участки могут начинаться правее.
    const side = this.#surfaces.find(
      (one) => one.kind === "side" && one.host === surface.host && one.side === "left",
    );
    return side?.kind === "side" ? side.x : surface.x0;
  }

  #start(phase: "walk" | "jump", spot: Spot): void {
    this.#from = [this.x, this.y];
    this.#target = spot;
    this.#t = 0;
    this.#pinned = null;
    this.phase = phase;
    this.facing = spot.x >= this.x ? 1 : -1;
    this.#idle = 0;
  }

  #fall(): void {
    this.phase = "fall";
    this.#spot = null;
    this.#pinned = null;
    this.#vx = 0;
    this.#vy = 0;
  }

  #tickRest(dt: number): void {
    this.#idle += dt;
    const surface = this.#spot?.surface;
    if (surface === undefined || this.#pinned !== null) return;
    const standing = surface.kind === "edge" || surface.kind === "floor";
    // Оглядывается: стоя и сидя не смотрит всё время в одну сторону.
    this.#lookIn -= dt;
    if (this.#lookIn <= 0 && standing && this.#idle < LAY_AFTER_S) {
      this.#lookIn = 5 + this.#random() * 9;
      this.facing = this.facing === 1 ? -1 : 1;
    }
    if (!this.wander || !standing) return;
    this.#wanderIn -= dt;
    if (this.#wanderIn > 0) return;
    this.#wanderIn = this.calm ? 20 + this.#random() * 25 : 6 + this.#random() * 12;
    const reach = this.calm ? 320 : 500;
    this.goTo(spotOn(surface, this.x + (this.#random() - 0.5) * reach, this.y));
  }

  #tickWalk(dt: number): void {
    const target = this.#target;
    if (target === null) return;
    const dx = target.x - this.x;
    const move = WALK_SPEED * dt;
    if (Math.abs(dx) <= move) this.#rest(target);
    else this.x += Math.sign(dx) * move;
  }

  #tickJump(): void {
    const target = this.#target;
    if (target === null) return;
    const s = Math.min(1, this.#t / JUMP_S);
    const [x0, y0] = this.#from;
    const height = 80 + Math.abs(target.y - y0) * 0.2;
    this.x = x0 + (target.x - x0) * s;
    this.y = y0 + (target.y - y0) * s - 4 * height * s * (1 - s);
    if (s >= 1) this.#rest(target);
  }

  #tickBolt(): void {
    if (this.#t < BOLT_S) return;
    const target = this.#target;
    const pin = this.#pinAfter;
    this.#pinAfter = null;
    if (pin !== null) {
      // Подлетел к элементу экрана: висит у него и тыкает — искры в точке касания.
      this.#effects.push({ kind: "sparks", x: this.#point[0], y: this.#point[1], t: 0 });
      this.phase = "rest";
      this.#spot = null;
      this.#pinned = pin.pose;
      this.facing = pin.facing;
      this.x = this.#point[0];
      this.y = this.#point[1];
      this.#idle = 0;
      return;
    }
    this.#effects.push({ kind: "sparks", x: this.#point[0], y: this.#point[1] - this.chest, t: 0 });
    if (target !== null) {
      this.#rest(target);
      return;
    }
    this.x = this.#point[0];
    this.y = this.#point[1];
    this.#fall();
  }

  #tickFall(dt: number): void {
    const previous = this.y;
    this.#vy += GRAVITY * dt;
    this.x += this.#vx * dt;
    this.y += this.#vy * dt;
    this.#vx *= 1 - Math.min(1, 0.6 * dt);
    const { x, w, y } = this.#bounds;
    if (this.x < x + 30 || this.x > x + w - 30) {
      this.x = Math.min(x + w - 30, Math.max(x + 30, this.x));
      this.#vx = -this.#vx * WALL_BOUNCE;
    }
    if (this.y < y + 200 && this.#vy < 0) this.#vy = -this.#vy * WALL_BOUNCE;
    if (this.#vy <= 0) return;
    const landing = below(this.#surfaces, this.x, previous);
    if (landing === null || landing.y > this.y) return;
    if (this.#vy > 900) {
      this.y = landing.y;
      this.#vy = -this.#vy * FLOOR_BOUNCE;
      return;
    }
    this.#rest(landing);
  }
}
