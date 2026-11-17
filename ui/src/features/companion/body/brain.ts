/**
 * Поведение спутника (Этап 23, разделы 4–5): где он, что делает и какая поза. Чистая логика без DOM:
 * `tick(dt)` двигает его, `body()` — что нарисовать. Переход между местами — пешком или прыжком, если
 * близко, молнией, если далеко (решение пользователя); бросок мышью — полёт с отскоками, как у Capri.
 */
import {
  below,
  hostId,
  iconSurfaces,
  sameSurface,
  snap,
  spotOn,
  surfaces,
  type Pose,
  type Spot,
  type Surface,
} from "../space";
import { climbRoute, descendRoute, type Climb } from "../space";
import { fitScreen } from "../space";
import type { Rect, World } from "../space";
import { poseOf } from "./pose";
import type { Body, Effect, Music, Phase } from "./types";

export type { Body, Effect, Music, Phase } from "./types";

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
const LOOK_DEADZONE = 40;
const HEARTS_S = 1.4;
/** Сколько держится «довольная мордочка» после поглаживания. */
const PET_S = 1.2;
/** Скорость лазанья: медленнее ходьбы — видно, что тяжело. */
const CLIMB_SPEED = 90;

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
  /** Курсор по x (CSS-пиксели слоя) или `null`, пока неизвестен: в покое персонаж смотрит на мышь. */
  cursorX: number | null = null;
  /**
   * Занят своей инициативой (говорит фразу, тыкает в кнопку): на мышь не оборачивается. Во время ходьбы,
   * прыжка и полёта он и так смотрит по движению.
   */
  busy = false;
  #petting = 0;
  #world: World | null = null;
  #icons: Surface[] = [];
  /** Высота груди над точкой опоры: отсюда выходит молния и искры (рост × 0,55). */
  chest = 150;
  /** Рост холста позы в CSS-пикселях: сколько места нужно над сиденьем (`fitScreen`). */
  figure = 300;
  music: Music = "off";
  /**
   * «Смотрим вместе» (BEHAVIOR §11): сидит в углу, смотрит видео с попкорном, не гуляет и не засыпает.
   * «Тихо» — полный экран без видео: сидит в углу и не мешает.
   */
  watching = false;
  quiet = false;
  #popcornIn = 2;
  /** Простой до «лечь» и «уснуть», секунды; задаёт настроение (`mood.ts`, BEHAVIOR §2). */
  layAfter = 90;
  sleepAfter = 300;
  /** Множитель пауз между прогулками: бодрый гуляет чаще. */
  pace = 1;
  #climb: Climb | null = null;
  /** Окно, по которому лезет: его левый/правый край в момент прошлого сдвига. */
  #climbBase = 0;
  /** Короткая поза-эмоция в покое (кружится, машет, зевает), секунды до конца. */
  #emote: { pose: Pose; left: number } | null = null;

  constructor(random: Random = Math.random) {
    this.#random = random;
  }

  /** Сколько секунд стоит на месте без дела: для комментариев «мне скучно». */
  get idleSeconds(): number {
    return this.#idle;
  }

  /** Лежит или спит: гладят — фразы «сонные». */
  get drowsy(): boolean {
    return this.phase === "rest" && this.#idle > this.layAfter;
  }

  /** Показать позу-эмоцию на `seconds` секунд, если стоит или сидит (T4, T6, T7, T16). */
  emote(pose: Pose, seconds: number): void {
    if (this.phase !== "rest") return;
    this.#emote = { pose, left: seconds };
    this.#idle = 0;
  }

  get spot(): Spot | null {
    return this.#spot;
  }

  get surfaceList(): readonly Surface[] {
    return this.#surfaces;
  }

  /** Новая картина рабочего стола: опоры пересчитываются, ушедшее из-под ног окно — падение. */
  /** Значки рабочего стола как опоры, пока он активен; закрыли значки окном — пусто (персонаж падает). */
  setIcons(icons: readonly Rect[]): void {
    this.#icons = iconSurfaces(icons);
    if (this.#world !== null) this.setWorld(this.#world);
  }

  setWorld(world: World): void {
    this.#world = world;
    // Только опоры, где персонаж виден целиком: не за верхом и не за боками экрана.
    this.#surfaces = fitScreen([...surfaces(world), ...this.#icons], world.monitor, this.figure);
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
    if (this.phase === "climb" && this.#climb?.side.host === id) {
      this.#climbMoved(rect);
      return;
    }
    const spot = this.#spot;
    if (this.phase !== "rest" || spot === null || hostId(spot.surface) !== id) return;
    if (spot.surface.kind !== "edge" && spot.surface.kind !== "side") return;
    if (rect === null) {
      this.#fall();
      return;
    }
    const surface = spot.surface;
    const base = surface.kind === "side" && surface.side === "right" ? rect.x + rect.w : rect.x;
    this.x = base + this.#rel;
    if (spot.surface.kind !== "edge") return;
    this.y = rect.y;
    // Окно утащили к верху экрана: сидя, голова ушла бы за край — спрыгивает.
    if (rect.y - this.figure * 0.6 < this.#bounds.y) this.#fall();
  }

  /** Встать на место сразу (первый показ, Shift + отпустить). */
  place(spot: Spot): void {
    this.#rest(spot);
  }

  /** Сторож (`mind/sanity.ts`): поставить на опору под собой или на «пол», в пределах экрана. */
  rescue(): void {
    const b = this.#bounds;
    const fallback = b.x + b.w / 2;
    const x = Math.min(
      b.x + b.w - 40,
      Math.max(b.x + 40, Number.isFinite(this.x) ? this.x : fallback),
    );
    const landing = below(this.#surfaces, x, b.y);
    this.x = x;
    if (landing !== null) this.#rest(landing);
    else this.y = b.y + b.h / 2;
  }

  /** Прогулка по своей опоре — когда, решает «Разум» (MIND §4, действие «прогулка»). */
  stroll(): void {
    const surface = this.#spot?.surface;
    if (this.phase !== "rest" || surface === undefined) return;
    if (surface.kind !== "edge" && surface.kind !== "floor") return;
    const reach = this.calm ? 320 : 500;
    this.goTo(spotOn(surface, this.x + (this.#random() - 0.5) * reach, this.y));
  }

  /** Перейти на место: близко — пешком или прыжком, далеко — молнией. */
  goTo(spot: Spot): void {
    if (this.phase === "held" || this.phase === "hidden") return;
    const distance = Math.hypot(spot.x - this.x, spot.y - this.y);
    if (distance < 4) return;
    if (this.#tryClimb(spot) || this.#tryDescend(spot)) return;
    if (distance >= WALK_LIMIT) {
      this.bolt(spot, [spot.x, spot.y]);
      return;
    }
    const level = this.#spot !== null && sameSurface(this.#spot.surface, spot.surface);
    this.#start(level ? "walk" : "jump", spot);
  }

  /** На окно выше — по его боку, если до стены можно дойти (BEHAVIOR §9). */
  #tryClimb(spot: Spot): boolean {
    const from = this.#spot;
    if (this.phase !== "rest" || from === null || spot.surface.kind !== "edge") return false;
    const host = spot.surface.host;
    const seat = this.#world?.seats.find((one) => one.id === host);
    if (seat === undefined) return false;
    const route = climbRoute(this.#surfaces, from, spot, seat.rect.y + seat.rect.h);
    return route !== null && this.#follow(route);
  }

  /** С крыши окна вниз — сползает по стене, а не прыгает с высоты (COMPANION.md, этап 2). */
  #tryDescend(spot: Spot): boolean {
    const from = this.#spot;
    if (this.phase !== "rest" || from === null) return false;
    const route = descendRoute(this.#surfaces, from, spot);
    return route !== null && this.#follow(route);
  }

  /** Пойти по маршруту: к началу стены пешком, потом — лезть. */
  #follow(route: Climb): boolean {
    this.#climb = route;
    if (Math.abs(route.foot.x - this.x) < 4) this.#startClimb();
    else this.#start("walk", route.foot);
    return true;
  }

  #startClimb(): void {
    const climb = this.#climb;
    if (climb === null) return;
    this.phase = "climb";
    this.#spot = null;
    this.#pinned = null;
    this.#t = 0;
    // Стена справа от персонажа (`left` — левый бок окна) — лицом к ней, вправо.
    this.facing = climb.side.side === "left" ? 1 : -1;
    this.#climbBase = climb.side.x;
    if (climb.down === true) {
      // Перелез через край крыши на стену: середина тела чуть ниже края.
      this.x = climb.target.x;
      this.y += this.figure * 0.25;
      return;
    }
    // Точка опоры «лезет» — середина тела, а не ступни: поднять её на полроста.
    this.y -= this.figure * 0.45;
  }

  #tickClimb(dt: number): void {
    const climb = this.#climb;
    if (climb === null) {
      this.#fall();
      return;
    }
    if (climb.down === true) {
      // Спуск: ноги дошли до опоры внизу — спрыгнул на неё.
      this.y += CLIMB_SPEED * 1.4 * dt;
      if (this.y < climb.target.y - this.figure * 0.5) return;
      this.#climb = null;
      this.#start("jump", climb.target);
      return;
    }
    this.y -= CLIMB_SPEED * dt;
    // Середина тела дошла до крыши — перевалился наверх коротким прыжком.
    if (this.y > climb.target.y + this.figure * 0.15) return;
    this.#climb = null;
    this.#start("jump", climb.target);
  }

  /** Окно, по которому лезет, двигают: лезет вместе с ним; закрыли — падает. */
  #climbMoved(rect: Rect | null): void {
    const climb = this.#climb;
    if (climb === null) return;
    if (rect === null) {
      this.#fall();
      return;
    }
    const base = climb.side.side === "right" ? rect.x + rect.w : rect.x;
    const dx = base - this.#climbBase;
    this.#climbBase = base;
    this.x += dx;
    const target = climb.target;
    const y = climb.down === true ? target.y : rect.y;
    this.#climb = { ...climb, target: { ...target, x: target.x + dx, y } };
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

  /** Погладили (клик по персонажу): жмурится, подпрыгивает, над головой сердечки. */
  pet(): void {
    if (this.phase === "hidden" || this.phase === "held") return;
    this.#effects.push({ kind: "hearts", x: this.x, y: this.y - this.chest * 1.7, t: 0 });
    this.#petting = PET_S;
    this.#idle = 0;
  }

  /** Персонажа взяли мышью: висит за «шиворот» у курсора. */
  hold(px: number, py: number): void {
    this.#climb = null;
    this.#emote = null;
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
    // Разбудили — сначала потягивается (COMPANION.md, этап 2).
    const sleepy = this.phase === "rest" && this.#idle > this.layAfter;
    this.#idle = 0;
    if (sleepy) this.emote("yawn", 2);
  }

  tick(dt: number): void {
    const step = Math.min(dt, 0.05);
    this.#t += step;
    this.#petting = Math.max(0, this.#petting - step);
    if (this.#emote !== null) {
      this.#emote.left -= step;
      if (this.#emote.left <= 0 || this.phase !== "rest") this.#emote = null;
    }
    this.#effects = this.#effects
      .map((effect) => ({ ...effect, t: effect.t + step / this.#effectLength(effect) }))
      .filter((effect) => effect.t < 1);
    if (this.phase === "rest") this.#tickRest(step);
    else if (this.phase === "walk") this.#tickWalk(step);
    else if (this.phase === "jump") this.#tickJump();
    else if (this.phase === "fall") this.#tickFall(step);
    else if (this.phase === "bolt") this.#tickBolt();
    else if (this.phase === "climb") this.#tickClimb(step);
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
      petting: this.#petting / PET_S,
      effects: this.#effects,
    };
  }

  #effectLength(effect: Effect): number {
    if (effect.kind === "bolt") return BOLT_S;
    if (effect.kind === "portal") return PORTAL_S * 1.4;
    if (effect.kind === "hearts") return HEARTS_S;
    if (effect.kind === "popcorn") return 0.9;
    if (effect.kind === "mark") return 0.05;
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
    return poseOf({
      pinned: this.#pinned,
      phase: this.phase,
      spot: this.#spot?.pose ?? null,
      emote: this.#emote?.pose ?? null,
      watching: this.watching,
      music: this.music,
      petting: this.#petting > 0,
      idle: this.#idle,
      layAfter: this.layAfter,
      sleepAfter: this.sleepAfter,
    });
  }

  #rest(spot: Spot): void {
    this.#climb = null;
    this.phase = "rest";
    this.#spot = spot;
    this.#pinned = null;
    this.x = spot.x;
    this.y = spot.y;
    this.facing = spot.facing;
    this.#vx = 0;
    this.#vy = 0;
    const surface = spot.surface;
    // Сдвиг от окна: по краю — от левого края окна, у бока — от самого бока (отступ от стены).
    this.#rel =
      surface.kind === "edge"
        ? spot.x - this.#hostLeft(surface)
        : surface.kind === "side"
          ? spot.x - surface.x
          : 0;
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
    this.#climb = null;
    this.phase = "fall";
    this.#spot = null;
    this.#pinned = null;
    this.#vx = 0;
    this.#vy = 0;
  }

  #tickRest(dt: number): void {
    // Поёт или смотрит — не скучает и не засыпает.
    if (this.music === "playing" || this.watching) {
      this.#idle = 0;
      if (this.watching && this.#spot?.pose === "sit_corner") this.#munch(dt);
      return;
    }
    if (this.quiet) return;
    this.#idle += dt;
    const surface = this.#spot?.surface;
    if (surface === undefined || this.#pinned !== null) return;
    const standing = surface.kind === "edge" || surface.kind === "floor";
    if (standing) this.#faceCursor();
    if (!this.wander || !standing) return;
    this.#wanderIn -= dt;
    if (this.#wanderIn > 0) return;
    const base = this.calm ? 20 + this.#random() * 25 : 6 + this.#random() * 12;
    this.#wanderIn = base * this.pace;
    const reach = this.calm ? 320 : 500;
    this.goTo(spotOn(surface, this.x + (this.#random() - 0.5) * reach, this.y));
  }

  /** Жуёт попкорн: время от времени зёрнышко вылетает из ведёрка. */
  #munch(dt: number): void {
    this.#popcornIn -= dt;
    if (this.#popcornIn > 0) return;
    this.#popcornIn = 2 + this.#random() * 2.5;
    const x = this.x + this.facing * this.chest * 0.25;
    this.#effects.push({ kind: "popcorn", x, y: this.y - this.chest * 0.75, t: 0 });
  }

  /** Смотрит в сторону мыши; порог 40 px — не дёргается, когда курсор прямо над ним. */
  #faceCursor(): void {
    const cursor = this.cursorX;
    if (cursor === null || this.busy || this.#idle > this.sleepAfter) return;
    if (cursor > this.x + LOOK_DEADZONE) this.facing = 1;
    else if (cursor < this.x - LOOK_DEADZONE) this.facing = -1;
  }

  #tickWalk(dt: number): void {
    const target = this.#target;
    if (target === null) return;
    const dx = target.x - this.x;
    const move = WALK_SPEED * dt;
    if (Math.abs(dx) > move) {
      this.x += Math.sign(dx) * move;
      return;
    }
    // Дошёл до стены — дальше лезет (маршрут `#tryClimb`).
    if (this.#climb !== null && target === this.#climb.foot) {
      this.x = target.x;
      this.#startClimb();
      return;
    }
    this.#rest(target);
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
    // Страховка: улетел ниже экрана (картина окон устарела) — на пол, а не в пустоту.
    if (this.y > y + this.#bounds.h + 200) {
      const floor = below(this.#surfaces, this.x, y);
      if (floor !== null) this.#rest(floor);
      return;
    }
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
