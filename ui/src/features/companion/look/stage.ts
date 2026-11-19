/**
 * Отрисовка спутника на слое (Этап 23): поза из пакета (или силуэт), процедурная жизнь поверх неё —
 * дыхание, подскок в такт речи, «сплющивание» при приземлении, — моргание и речь вариантами `_blink`,
 * `_talk`, затем эффекты. Чистится только прошлый прямоугольник, а не весь экран (раздел 8).
 */
import type { Pose } from "../space";
import type { Body } from "../body";
import { drawEffects } from "./effects";
import { ANCHORS, CANVAS_RATIO, FALLBACK, LOOP_FPS, loadPoses, pickFrame, sequence } from "./pack";

/** Переходные кадры между позами (`<из>_to_<в>_1…N`, FRAMES-4.md): 12 кадров/с, тяжёлые подъёмы — 8. */
const TRANSITION_FPS = 12;
const SLOW_TRANSITION: ReadonlyMap<string, number> = new Map([
  ["laydown_to_stand", 8],
  ["sit_edge_to_stand", 8],
  ["float_to_stand", 10],
]);
/** Последний кадр перехода держится чуть дольше: подъём «доходит» (критик, раунд 4). */
const TRANSITION_HOLD_S = 0.04;
import type { Scene } from "../behavior/diversions";
import { drawDiversion, poseScene } from "./diversions";
import { Motion } from "./motion";
import { drawPanel, panelRect } from "./panel";
import { placeholderPose } from "./placeholder";
import { placement, tallness } from "./placement";
import type { Rect } from "../space";

const POSES: readonly Pose[] = [
  "stand",
  "walk",
  "sit_edge",
  "perch_corner",
  "lean_side",
  "hang_side",
  "sit_corner",
  "laydown",
  "sleep",
  "held",
  "float",
];
const BLINK_EVERY_S = 4.2;
/** Силуэт без кадра (портал до загрузки пакета): ширина к высоте. */
const PLACEHOLDER_ASPECT = 0.55;
/** Моргание с полуприкрытыми кадрами чуть дольше: 0,2 с. */
const BLINK_S = 0.2;

export interface Look {
  mouth: number;
  speaking: boolean;
  hue: number;
  /** 1 → 0 за пару секунд после зова: вспышка. */
  attention: number;
  /** Название станции для табло музыкального ящика или `null`. */
  panel: string | null;
}

/** Позы радио — спокойные: без подскока в такт громкости (просьба пользователя 2026-11-17). */
const CALM: ReadonlySet<Pose> = new Set(["sing", "jukebox", "radio_idle"]);

export class CompanionStage {
  readonly #ctx: CanvasRenderingContext2D;
  readonly #canvas: HTMLCanvasElement;
  #poses = new Map<string, ImageBitmap>();
  /** Имена загруженных кадров: выбор кадра — по ним, без пересоздания множества каждый кадр. */
  #keys: ReadonlySet<string> = new Set<string>();
  #placeholders = new Map<string, ImageBitmap>();
  #height = 280;
  #time = 0;
  #dirty: Rect | null = null;
  #seed = 1;
  /** Центр портала (фигуры) — пока персонаж выходит или уходит; кольцо держится там же и после. */
  #portalAt: [number, number] | null = null;
  /** Где персонаж сейчас нарисован (CSS-пиксели): для кликов и облачка. */
  bounds: Rect | null = null;
  radioControls: Rect | null = null;
  /**
   * Высота обычного кадра в пикселях растра (рост × CANVAS_RATIO × devicePixelRatio, как в `pack.ts`): по ней
   * узнаются высокие кадры (placement.ts). Не по кадру `stand`: он сам может быть высоким (рожки).
   */
  #unit: number | null = null;
  /** Когда началась текущая поза: одноразовые сцены идут кадр за кадром от неё. */
  #poseStart = 0;

  constructor(canvas: HTMLCanvasElement) {
    const ctx = canvas.getContext("2d");
    if (ctx === null) throw new Error("Canvas 2D is unavailable");
    this.#canvas = canvas;
    this.#ctx = ctx;
  }

  /** Позы пользователя и временные силуэты под рост `height`. */
  async load(height: number): Promise<void> {
    this.#height = height;
    const [poses, placeholders] = await Promise.all([
      loadPoses(height),
      Promise.all(POSES.map(async (pose) => [pose, await placeholderPose(pose, height)] as const)),
    ]);
    this.#poses = poses;
    this.#keys = new Set(poses.keys());
    this.#unit = Math.round(height * CANVAS_RATIO * devicePixelRatio);
    this.#placeholders = new Map(placeholders);
  }

  resize(width: number, height: number): void {
    const ratio = devicePixelRatio || 1;
    this.#canvas.width = Math.round(width * ratio);
    this.#canvas.height = Math.round(height * ratio);
    this.#ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    this.#dirty = null;
  }

  /** Эффект поверх персонажа может выходить за рамку кадра; очистить его перед следующей отрисовкой. */
  includePainted(rect: Rect): void {
    const dirty = this.#dirty;
    if (dirty === null) {
      this.#dirty = grow(rect, 2);
      return;
    }
    const x = Math.min(dirty.x, rect.x);
    const y = Math.min(dirty.y, rect.y);
    const w = Math.max(dirty.x + dirty.w, rect.x + rect.w) - x;
    const h = Math.max(dirty.y + dirty.h, rect.y + rect.h) - y;
    this.#dirty = grow({ x, y, w, h }, 2);
  }

  /** Имя кадра, нарисованного последним: табло — только у кадров `jukebox*`. */
  #frameKey: string | null = null;
  /** Плавность кодом: разворот, наклон, упругость, растворение кадров (ANIMATION.md). */
  readonly #motion = new Motion();

  /** Идёт переход (растворение, разворот, посадка) — нужно 60 кадров/с. */
  get animating(): boolean {
    return this.#motion.busy;
  }

  #image(pose: Pose, look: Look, petting: number): ImageBitmap | null {
    const sleeping = pose === "sleep";
    const phase = this.#time % BLINK_EVERY_S;
    // Гладят: жмурится (закрытые глаза), если отдельного кадра «довольный» нет.
    const happy = petting > 0 && !this.#keys.has("pet") && !this.#keys.has("pet_1");
    const blink = happy ? 0.5 : phase < BLINK_S && !sleeping ? phase / BLINK_S : null;
    const state = {
      time: this.#time,
      mouth: look.mouth,
      speaking: look.speaking && !sleeping && petting === 0,
      blink,
      since: this.#time - this.#poseStart,
    };
    const key = this.#transitionKey() ?? pickFrame(pose, state, this.#keys);
    this.#frameKey = key;
    if (key !== null) return this.#poses.get(key) ?? null;
    const fallback = [pose, ...FALLBACK[pose]].find((one) => this.#placeholders.has(one));
    return fallback === undefined ? null : (this.#placeholders.get(fallback) ?? null);
  }

  #lastDt = 0;
  #lastPose: Pose | null = null;
  #transition: { keys: { key: string; s: number }[]; t: number } | null = null;
  /** Рисовался ли прошлый кадр (меняет `#figure`; метод — чтобы анализ типов не «помнил» false). */
  #previousDrawn(): boolean {
    return this.#drewPrevious;
  }

  /** В этом кадре рисовался прошлый кадр — чистить весь холст. */
  #drewPrevious = false;
  /** Этот кадр — граница перехода: без растворения цикла. */
  #edge = false;
  /** Показанное свечение — плавно догоняет `look.attention`. */
  #glow = 0;

  draw(body: Body, look: Look, dt: number, scene: Scene | null = null): void {
    if (scene) poseScene(body, scene, this.#height);
    this.#time += dt;
    this.#lastDt = dt;
    this.#transit(body.pose, dt);
    this.#seed = (this.#seed + 1) % 100000;
    const ctx = this.#ctx;
    const dirty = this.#dirty;
    if (dirty !== null) ctx.clearRect(dirty.x, dirty.y, dirty.w, dirty.h);
    this.bounds = null;
    this.radioControls = null;
    let area: Rect | null = null;
    this.#drewPrevious = false;
    if (scene?.kind === "peek") {
      const lip = body.y;
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, this.#canvas.width, Math.max(0, lip));
      ctx.clip();
      body.y += this.#height * 0.4 * Math.sin(Math.PI * scene.progress);
      area = this.#figure(body, look);
      body.y = lip;
      ctx.restore();
      if (area) this.bounds = { ...area, h: Math.max(0, lip - area.y) };
    } else if (body.phase !== "hidden" && body.scale > 0.01) area = this.#figure(body, look);
    if (scene && area) {
      drawDiversion(ctx, body, scene, this.#height);
      area = grow(area, this.#height * 0.45);
    }
    if (body.phase === "portal_out" || body.phase === "portal_in") {
      this.#portalAt = this.#centerOf(body, look);
    }
    if (body.effects.length > 0) {
      // Кольцо портала — в центре фигуры: персонаж «вырастает» из его середины, а не под ним.
      const at = this.#portalAt;
      const effects =
        at === null
          ? body.effects
          : body.effects.map((one) =>
              one.kind === "portal" ? { ...one, x: at[0], y: at[1] } : one,
            );
      drawEffects(ctx, effects, look.hue, Math.floor(this.#seed / 2));
      area = { x: 0, y: 0, w: this.#canvas.width, h: this.#canvas.height };
    }
    // Прошлый кадр (растворение, смена позы) рисуется со своей точкой опоры и размером — он может выйти за
    // рамку нового. Тогда чистим весь холст в следующем кадре, иначе при быстром перетаскивании оставались
    // обрывки персонажа (баг 2026-11-18).
    if (this.#previousDrawn()) area = { x: 0, y: 0, w: this.#canvas.width, h: this.#canvas.height };
    this.#dirty = area === null ? null : grow(area, 40);
  }

  /** Поза сменилась: есть переходные кадры («из_to_в» или обратные «в_to_из» задом наперёд) — сыграть. */
  #transit(pose: Pose, dt: number): void {
    const was = this.#transitionKey();
    if (this.#transition !== null) this.#transition.t += dt;
    // Вход в переход и выход из него — без растворения цикла: переход сам и есть сглаживание.
    this.#edge = was !== this.#transitionKey();
    if (pose === this.#lastPose) return;
    const from = this.#lastPose;
    this.#lastPose = pose;
    this.#poseStart = this.#time;
    if (from === null) return;
    // Прямого перехода нет — через стойку (критик: «потягивается → машет» без перехода).
    const direct = this.#path(from, pose);
    const keys =
      direct.length > 0 || from === "stand" || pose === "stand"
        ? direct
        : [...this.#path(from, "stand"), ...this.#path("stand", pose)];
    this.#transition = keys.length > 0 ? { keys, t: 0 } : null;
    this.#edge = this.#edge || this.#transition !== null;
  }

  /** Кадры перехода `from → to`: прямые или обратные задом наперёд; каждый — со своей частотой. */
  #path(from: Pose, to: Pose): { key: string; s: number }[] {
    const forward = sequence(`${from}_to_${to}`, this.#keys);
    const name = forward.length > 0 ? `${from}_to_${to}` : `${to}_to_${from}`;
    const keys = forward.length > 0 ? forward : sequence(name, this.#keys).reverse();
    const s = 1 / (SLOW_TRANSITION.get(name) ?? TRANSITION_FPS);
    return keys.map((key, i) => ({ key, s: i === keys.length - 1 ? s + TRANSITION_HOLD_S : s }));
  }

  /** Кадр перехода сейчас или `null`. */
  #transitionKey(): string | null {
    const transition = this.#transition;
    if (transition === null) return null;
    let t = transition.t;
    for (const one of transition.keys) {
      if (t < one.s) return one.key;
      t -= one.s;
    }
    return null;
  }

  /** Нарисовать кадр позы `pose` высотой `h` относительно уже сдвинутой в точку опоры системы. */
  #drawAt(image: ImageBitmap, pose: Pose, scale: number): void {
    const at = this.#place(image, pose);
    const [w, h] = [at.w * scale, at.h * scale];
    this.#ctx.drawImage(image, at.cx - w / 2, at.cy - h / 2, w, h);
  }

  /** Размер и сдвиг кадра при полном росте; высокий кадр — в том же масштабе (placement.ts). */
  #place(image: ImageBitmap, pose: Pose): ReturnType<typeof placement> {
    const H = this.#height * CANVAS_RATIO;
    return placement(image.width / image.height, ANCHORS[pose], H, tallness(image, this.#unit));
  }

  /** Центр фигуры в полный рост (CSS-пиксели): из него растёт персонаж в портале. */
  #centerOf(body: Body, look: Look): [number, number] {
    const image = this.#image(body.pose, look, body.petting);
    const H = this.#height * CANVAS_RATIO;
    const at =
      image === null
        ? placement(PLACEHOLDER_ASPECT, ANCHORS[body.pose], H, 1)
        : this.#place(image, body.pose);
    return [body.x + body.facing * at.cx, body.y + at.cy];
  }

  #figure(body: Body, look: Look): Rect | null {
    const image = this.#image(body.pose, look, body.petting);
    if (image === null) return null;
    // В портале фигура масштабируется вокруг своего центра; в полный рост — та же точка опоры.
    const { w: W, h: H, cx, cy } = this.#place(image, body.pose);
    const h = H * body.scale;
    const w = W * body.scale;
    const breath = body.phase === "rest" ? Math.sin(this.#time * 1.8) * 0.008 : 0;
    // Подскок: в такт речи и маленький прыжок радости, когда гладят.
    const hop = body.petting > 0 ? Math.abs(Math.sin(body.petting * Math.PI * 3)) * 10 : 0;
    const lift = (look.speaking && !CALM.has(body.pose) ? look.mouth * 5 : 0) + hop;
    const ctx = this.#ctx;
    ctx.save();
    // Растворять ли кадры цикла, решает `SOFT_LOOPS` (motion.ts): ходьба, лазанье, танец — нет.
    const loopS = 1 / (LOOP_FPS[body.pose] ?? 6);
    this.#motion.frame(image, body.pose, this.#edge ? 0 : loopS);
    const smooth = this.#motion.step(body, this.#lastDt, this.#transitionKey() !== null);
    ctx.translate(body.x, body.y - lift);
    ctx.rotate(smooth.lean);
    ctx.scale(smooth.scaleX, smooth.scaleY + breath);
    // Свечение нарастает за ~150 мс, а не включается разом (критик: скачок на первом кадре).
    this.#glow +=
      (look.attention - this.#glow) *
      Math.min(1, this.#lastDt * (look.attention > this.#glow ? 7 : 3));
    if (this.#glow > 0.01) {
      ctx.shadowColor = `hsla(${String(look.hue)}, 95%, 70%, ${String(this.#glow)})`;
      ctx.shadowBlur = 30 * this.#glow;
    }
    const previous = this.#motion.previous;
    const swap = this.#motion.swap;
    this.#drewPrevious = previous !== null && (swap !== null || this.#motion.fadeLeft > 0.01);
    if (swap?.phase === "out" && previous !== null) {
      // Смена позы, «выдох»: старая поза приседает и гаснет (своя точка опоры), новой ещё нет.
      ctx.scale(1, 1 - 0.08 * swap.k);
      this.#drawAt(previous, this.#motion.previousPose ?? body.pose, body.scale);
    } else {
      // «Вдох»: новая поза проявляется с лёгкой растяжкой; иначе — обычный кадр.
      if (swap?.phase === "in")
        ctx.scale(1, 0.92 + 0.16 * Math.sin((Math.PI / 2) * swap.k) - 0.08 * swap.k);
      ctx.drawImage(image, cx - w / 2, cy - h / 2, w, h);
      // Кадр «телесного» цикла: прошлый коротко поверх (та же точка опоры — без двоения).
      const left = previous === null || swap !== null ? 0 : this.#motion.fadeLeft;
      if (previous !== null && left > 0.01) {
        ctx.globalAlpha = left;
        this.#drawAt(previous, body.pose, body.scale);
      }
    }
    ctx.globalAlpha = 1;
    ctx.restore();
    const box = {
      x: body.x + body.facing * cx - w / 2,
      y: body.y - lift + cy - h / 2,
      w,
      h,
    };
    // Табло по центру кадра — отражение не мешает; текст пишется прямо, а не зеркально.
    if (look.panel !== null && this.#frameKey?.startsWith("jukebox") === true) {
      const screen = panelRect(box);
      drawPanel(ctx, screen, look.panel, this.#time);
      this.radioControls = {
        x: screen.x,
        y: box.y + box.h * 0.826,
        w: screen.w,
        h: box.h * 0.092,
      };
    }
    this.bounds = box;
    return box;
  }
}

function grow(rect: Rect, by: number): Rect {
  return { x: rect.x - by, y: rect.y - by, w: rect.w + by * 2, h: rect.h + by * 2 };
}
