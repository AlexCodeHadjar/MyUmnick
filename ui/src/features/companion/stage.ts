/**
 * Отрисовка спутника на слое (Этап 23): поза из пакета (или силуэт), процедурная жизнь поверх неё —
 * дыхание, подскок в такт речи, «сплющивание» при приземлении, — моргание и речь вариантами `_blink`,
 * `_talk`, затем эффекты. Чистится только прошлый прямоугольник, а не весь экран (раздел 8).
 */
import type { Pose } from "./anchors";
import type { Body } from "./brain";
import { drawEffects } from "./effects";
import { ANCHORS, CANVAS_RATIO, FALLBACK, loadPoses, pickFrame } from "./pack";
import { drawPanel, panelRect } from "./panel";
import { placeholderPose } from "./placeholder";
import type { Rect } from "./world";

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
    this.#placeholders = new Map(placeholders);
  }

  resize(width: number, height: number): void {
    const ratio = devicePixelRatio || 1;
    this.#canvas.width = Math.round(width * ratio);
    this.#canvas.height = Math.round(height * ratio);
    this.#ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    this.#dirty = null;
  }

  /** Имя кадра, нарисованного последним: табло — только у кадров `jukebox*`. */
  #frameKey: string | null = null;

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
    };
    const key = pickFrame(pose, state, this.#keys);
    this.#frameKey = key;
    if (key !== null) return this.#poses.get(key) ?? null;
    const fallback = [pose, ...FALLBACK[pose]].find((one) => this.#placeholders.has(one));
    return fallback === undefined ? null : (this.#placeholders.get(fallback) ?? null);
  }

  draw(body: Body, look: Look, dt: number): void {
    this.#time += dt;
    this.#seed = (this.#seed + 1) % 100000;
    const ctx = this.#ctx;
    const dirty = this.#dirty;
    if (dirty !== null) ctx.clearRect(dirty.x, dirty.y, dirty.w, dirty.h);
    this.bounds = null;
    let area: Rect | null = null;
    if (body.phase !== "hidden" && body.scale > 0.01) area = this.#figure(body, look);
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
    this.#dirty = area === null ? null : grow(area, 40);
  }

  /** Центр фигуры в полный рост (CSS-пиксели): из него растёт персонаж в портале. */
  #centerOf(body: Body, look: Look): [number, number] {
    const image = this.#image(body.pose, look, body.petting);
    const H = this.#height * CANVAS_RATIO;
    const W = image === null ? H * 0.55 : (image.width / image.height) * H;
    const [ax, ay] = ANCHORS[body.pose];
    return [body.x + body.facing * (0.5 - ax) * W, body.y + (0.5 - ay) * H];
  }

  #figure(body: Body, look: Look): Rect | null {
    const image = this.#image(body.pose, look, body.petting);
    if (image === null) return null;
    const H = this.#height * CANVAS_RATIO;
    const W = (image.width / image.height) * H;
    // В портале фигура масштабируется вокруг своего центра; в полный рост — та же точка опоры.
    const h = H * body.scale;
    const w = W * body.scale;
    const [ax, ay] = ANCHORS[body.pose];
    const cx = (0.5 - ax) * W;
    const cy = (0.5 - ay) * H;
    const breath = body.phase === "rest" ? Math.sin(this.#time * 1.8) * 0.008 : 0;
    // Подскок: в такт речи и маленький прыжок радости, когда гладят.
    const hop = body.petting > 0 ? Math.abs(Math.sin(body.petting * Math.PI * 3)) * 10 : 0;
    const lift = (look.speaking && !CALM.has(body.pose) ? look.mouth * 5 : 0) + hop;
    const ctx = this.#ctx;
    ctx.save();
    ctx.translate(body.x, body.y - lift);
    ctx.scale(body.facing, 1 + breath);
    if (look.attention > 0.01) {
      ctx.shadowColor = `hsla(${String(look.hue)}, 95%, 70%, ${String(look.attention)})`;
      ctx.shadowBlur = 30 * look.attention;
    }
    ctx.drawImage(image, cx - w / 2, cy - h / 2, w, h);
    ctx.restore();
    const box = {
      x: body.x + body.facing * cx - w / 2,
      y: body.y - lift + cy - h / 2,
      w,
      h,
    };
    // Табло по центру кадра — отражение не мешает; текст пишется прямо, а не зеркально.
    if (look.panel !== null && this.#frameKey?.startsWith("jukebox") === true) {
      drawPanel(ctx, panelRect(box), look.panel, this.#time);
    }
    this.bounds = box;
    return box;
  }
}

function grow(rect: Rect, by: number): Rect {
  return { x: rect.x - by, y: rect.y - by, w: rect.w + by * 2, h: rect.h + by * 2 };
}
