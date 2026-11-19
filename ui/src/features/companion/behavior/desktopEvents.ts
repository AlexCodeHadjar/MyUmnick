import { DESKTOP_REACTIONS } from "../settings";
import type { Body } from "../body";
import type { Pose, Rect } from "../space";

/** Свои кадры у каждой реакции (FRAMES-6): коробка, штамп, бумажка, испуг, ветер — в самих кадрах. */
const POSES = {
  download: "carry_box",
  paste: "stamp",
  copy: "hug_paper",
  screenshot: "flinch",
  close: "wave",
  desktop: "blown",
} as const;
export interface DesktopEvent {
  kind: keyof typeof POSES;
  size: number;
}

export class DesktopReactions {
  /** Когда показана реакция: пауза у каждой своя — скачивание не глушит штамп на минуту. */
  readonly #lastOf = new Map<DesktopEvent["kind"], number>();
  /** Последняя показанная реакция (рисунок поверх кадра идёт от неё). */
  #last = -Infinity;
  #event: DesktopEvent | null = null;

  /** Сколько миллисекунд ещё пауза у реакции `kind` (чек-лист); 0 — готова. */
  waitLeft(kind: DesktopEvent["kind"], now: number): number {
    const last = this.#lastOf.get(kind) ?? -Infinity;
    return Math.max(0, DESKTOP_REACTIONS[kind].cooldown - (now - last));
  }

  offer(event: DesktopEvent, now: number, enabled: boolean, random: number): Pose | null {
    const { chance, cooldown } = DESKTOP_REACTIONS[event.kind];
    const last = this.#lastOf.get(event.kind) ?? -Infinity;
    if (!enabled || now - last < cooldown || random >= chance) return null;
    this.#lastOf.set(event.kind, now);
    this.#last = now;
    this.#event = event;
    return POSES[event.kind];
  }

  /** Only the rendered snapshot moves; the window, surface and desktop stay in place. */
  move(body: Body, now: number, height: number): void {
    const event = this.#event;
    const t = (now - this.#last) / DESKTOP_REACTIONS.duration;
    if (!event || t >= 1 || t < 0 || body.pose !== POSES[event.kind]) return;
    const arc = Math.sin(Math.PI * t);
    if (event.kind === "desktop") {
      body.x += body.facing * height * 0.32 * arc;
      body.y -= height * (0.37 + 0.12 * arc);
    } else if (event.kind === "download") {
      const load = Math.min(1, Math.log2(1 + event.size) / 30);
      body.x += body.facing * height * load * arc * Math.sin(t * 23) * 0.07;
    } else if (event.kind === "screenshot") {
      body.y -= height * Math.max(0, 1 - t * 3) * 0.055;
    }
  }

  /** Поверх кадров — только то, чего в них нет: оттиск штампа, вспышка скриншота, линии ветра. */
  draw(
    ctx: CanvasRenderingContext2D | null,
    box: Rect | null,
    now: number,
    saved: string,
    typing: boolean,
  ): Rect | null {
    const event = this.#event;
    const t = (now - this.#last) / DESKTOP_REACTIONS.duration;
    if (event === null || box === null || ctx === null || t >= 1) return null;
    if (typing && event.kind !== "paste" && event.kind !== "desktop") return null;
    ctx.save();
    ctx.globalAlpha = Math.min(1, (1 - t) * 5);
    let painted: Rect | null = null;
    if (event.kind === "paste" && t > STAMP_HIT) painted = stampMark(ctx, box, saved);
    if (event.kind === "screenshot") painted = flash(ctx, box, t);
    if (event.kind === "desktop") painted = wind(ctx, box, t);
    ctx.restore();
    return painted;
  }
}

/** Штамп ударил (кадр `stamp_2`, ~0,6 с из 1,8): с этой доли реакции виден оттиск. */
const STAMP_HIT = 0.36;

function stampMark(ctx: CanvasRenderingContext2D, box: Rect, saved: string): Rect {
  const size = Math.min(26, box.h * 0.14);
  const x = box.x + box.w * 0.72;
  const y = box.y + box.h * 0.9;
  ctx.translate(x, y);
  ctx.rotate(-0.12);
  ctx.font = "bold " + String(size) + "px sans-serif";
  ctx.textAlign = "center";
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#b8323a";
  ctx.strokeRect(-size * 3.2, -size * 0.95, size * 6.4, size * 1.35);
  ctx.fillStyle = "#b8323a";
  ctx.fillText(saved, 0, 0);
  return { x: x - size * 4, y: y - size * 1.5, w: size * 8, h: size * 3 };
}

function flash(ctx: CanvasRenderingContext2D, box: Rect, t: number): Rect | null {
  const fade = Math.max(0, 1 - t * 4);
  if (fade <= 0) return null;
  const r = box.h * (0.3 + t);
  const x = box.x + box.w / 2;
  const glow = ctx.createRadialGradient(x, box.y, 0, x, box.y, r);
  glow.addColorStop(0, `rgba(255,255,255,${String(fade)})`);
  glow.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = glow;
  const painted = { x: x - r, y: box.y - r, w: r * 2, h: r * 2 };
  ctx.fillRect(painted.x, painted.y, painted.w, painted.h);
  return painted;
}

function wind(ctx: CanvasRenderingContext2D, box: Rect, t: number): Rect {
  ctx.strokeStyle = "#cfefff";
  ctx.lineWidth = 3;
  ctx.lineCap = "round";
  for (let i = 0; i < 3; i++) {
    const y = box.y + box.h * (0.3 + i * 0.2);
    const x = box.x - box.w * 0.4 + ((t * 2 + i / 3) % 1) * box.w * 0.9;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.quadraticCurveTo(x + box.w * 0.2, y - 10, x + box.w * 0.4, y);
    ctx.stroke();
  }
  return {
    x: box.x - box.w * 0.4,
    y: box.y + box.h * 0.3 - 10,
    w: box.w * 1.3,
    h: box.h * 0.4 + 10,
  };
}
