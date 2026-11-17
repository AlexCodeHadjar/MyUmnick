/**
 * Решения спутника, которые не зависят от DOM (Этап 23): куда идти при смене активного окна, что делать
 * с отпущенной мышью, что показать в облачке. Компонент слоя только передаёт сюда события.
 */
import { below, floorSpot, hostId, seatSpot, snap, type Spot, type Surface } from "./anchors";
import type { Focus, World } from "./world";

/** Место для активного окна (раздел 4.1): край окна, «пол» у правого края или угол экрана. */
export function followSpot(world: World, list: readonly Surface[], focus: Focus): Spot | null {
  if (focus.kind === "window") {
    const seat = world.seats.find((one) => one.id === focus.id);
    return seat === undefined ? null : seatSpot(list, seat.id, seat.rect.x, seat.rect.w);
  }
  if (focus.kind === "desktop") return floorSpot(list, false);
  if (focus.kind === "maximized") return floorSpot(list, true);
  return null;
}

/** Хозяин места (окно) или `null` для «пола». */
export function hostOf(spot: Spot | null): number | null {
  return spot === null ? null : hostId(spot.surface);
}

export type Release =
  | { kind: "place"; spot: Spot }
  | { kind: "hang"; x: number; y: number }
  | { kind: "toss"; vx: number; vy: number };

/** Отпустили, держа мышью (как у Capri): Shift — сесть рядом, Ctrl — повиснуть, иначе — бросок. */
/** Радиус «примагничивания», когда отпускают или целятся молнией: 70 px — промахнуться трудно. */
export const DROP_RADIUS = 70;
/** Отпустили спокойнее этого (px/с) — закрепиться на месте рядом; резче — бросок. */
export const CALM_SPEED = 900;

/** Куда персонаж закрепится, если отпустить здесь: край, угол, бок окна, верх экрана, значок. */
export function dropTarget(list: readonly Surface[], x: number, y: number): Spot | null {
  return snap(list, x, y, DROP_RADIUS);
}

export function release(
  list: readonly Surface[],
  point: { x: number; y: number; shift: boolean; ctrl: boolean },
  velocity: { vx: number; vy: number },
): Release {
  if (point.ctrl) return { kind: "hang", x: point.x, y: point.y };
  if (point.shift) {
    const spot = snap(list, point.x, point.y, 160) ?? below(list, point.x, point.y);
    if (spot !== null) return { kind: "place", spot };
  }
  // Отпустили спокойно рядом с опорой — закрепиться там (просьба пользователя 2026-11-17).
  if (Math.hypot(velocity.vx, velocity.vy) < CALM_SPEED) {
    const spot = dropTarget(list, point.x, point.y);
    if (spot !== null) return { kind: "place", spot };
  }
  return { kind: "toss", vx: velocity.vx, vy: velocity.vy };
}

/** Скорость по следу курсора за последние 80 мс, пикселей в секунду. */
export function velocityOf(trail: readonly { x: number; y: number; t: number }[]): {
  vx: number;
  vy: number;
} {
  const last = trail.at(-1);
  if (last === undefined) return { vx: 0, vy: 0 };
  const first = trail.find((p) => last.t - p.t <= 80) ?? last;
  const dt = (last.t - first.t) / 1000;
  return dt <= 0 ? { vx: 0, vy: 0 } : { vx: (last.x - first.x) / dt, vy: (last.y - first.y) / dt };
}

/** Облачко: последние ~140 знаков реплики, целыми словами. */
export function bubbleText(text: string, limit = 140): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= limit) return clean;
  const tail = clean.slice(clean.length - limit);
  const space = tail.indexOf(" ");
  return `…${space > 0 ? tail.slice(space + 1) : tail}`;
}

const BUBBLE_MARGIN = 8;

/**
 * Где поставить облачко размером `size` у фигуры `box` в окне `view` (левый верхний угол): над головой,
 * а если сверху тесно — сбоку от головы. Всегда целиком в пределах экрана — текст не обрезан краем.
 */
export function placeBubble(
  box: { x: number; y: number; w: number; h: number },
  size: { w: number; h: number },
  view: { w: number; h: number },
): { x: number; y: number } {
  const head = box.y + box.h * 0.08;
  const fit = (value: number, limit: number): number =>
    Math.max(BUBBLE_MARGIN, Math.min(value, limit - BUBBLE_MARGIN));
  if (head - size.h - BUBBLE_MARGIN >= BUBBLE_MARGIN) {
    const x = fit(box.x + box.w / 2 - size.w / 2, view.w - size.w);
    return { x, y: head - size.h };
  }
  const right = box.x + box.w + size.w + BUBBLE_MARGIN <= view.w;
  const x = right ? box.x + box.w : box.x - size.w;
  return { x: fit(x, view.w - size.w), y: fit(head, view.h - size.h) };
}
