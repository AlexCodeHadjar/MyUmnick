/**
 * «Следовать за мной» (просьба пользователя 2026-11-18) и «не мешать печатать»: куда встать относительно
 * курсора и поля ввода. Чистые функции над опорами — проверяются тестами.
 *
 * За курсором:
 * - курсор у верха экрана — висит на верхнем краю над ним;
 * - курсор заметно выше персонажа — лезет по краю экрана с его стороны и смотрит оттуда на курсор;
 * - иначе — идёт по опоре под курсором (или по «полу») к нему.
 */
import { below, spotOn, type Spot, type Surface } from "./anchors";
import type { Rect } from "./world";

/** Верхняя доля экрана, где курсор — «свисать». */
const TOP_ZONE = 0.16;
/** Выше персонажа на столько ростов — лезть по стене, а не идти. */
const CLIMB_RISE = 0.7;
/** Не ближе к курсору: персонаж не встаёт прямо под стрелкой. */
const KEEP_OFF = 90;

export interface Point {
  x: number;
  y: number;
}

/** Край экрана со стороны курсора; бок может быть разбит на участки (`room.ts`) — ближайший по высоте. */
function sideToward(list: readonly Surface[], x: number, y: number, monitor: Rect): Surface | null {
  // Левый край экрана — бок `right` (стена слева от персонажа).
  const want = x < monitor.x + monitor.w / 2 ? "right" : "left";
  let best: Surface | null = null;
  let bestGap = Infinity;
  for (const one of list) {
    if (one.kind !== "side" || one.host >= 0 || one.side !== want) continue;
    const gap = y < one.y0 ? one.y0 - y : y > one.y1 ? y - one.y1 : 0;
    if (gap < bestGap) {
      best = one;
      bestGap = gap;
    }
  }
  return best;
}

/** Где встать, чтобы быть рядом с курсором; `body` — где персонаж сейчас (ступни). */
export function cursorSpot(
  list: readonly Surface[],
  cursor: Point,
  body: Point,
  monitor: Rect,
  figure: number,
): Spot | null {
  if (cursor.y < monitor.y + monitor.h * TOP_ZONE) {
    const ceiling = list.find((one) => one.kind === "ceiling");
    if (ceiling !== undefined) return spotOn(ceiling, cursor.x, cursor.y);
  }
  if (body.y - cursor.y > figure * CLIMB_RISE) {
    // Голова — на уровне курсора: точка опоры у стены — ступни, на 0,8 роста ниже.
    const feet = cursor.y + figure * 0.8;
    const side = sideToward(list, cursor.x, feet, monitor);
    if (side !== null) return spotOn(side, cursor.x, feet);
  }
  const ground = below(list, cursor.x, cursor.y - figure * 0.2);
  if (ground === null) return null;
  const off = cursor.x >= body.x ? -KEEP_OFF : KEEP_OFF;
  return spotOn(ground.surface, cursor.x + off, ground.y);
}

/** Стоит ли идти: другая опора или заметно другое место на той же. */
export function worthMoving(from: Spot | null, to: Spot, step = 140): boolean {
  if (from === null) return true;
  if (from.surface !== to.surface && from.surface.kind !== to.surface.kind) return true;
  return Math.hypot(from.x - to.x, from.y - to.y) > step;
}

/** Мешает ли персонаж печатать: его фигура рядом с полем ввода (с запасом `gap`). */
export function inTheWay(caret: Rect, body: Point, figure: number, gap = 160): boolean {
  const half = figure * 0.25;
  const left = body.x - half - gap;
  const right = body.x + half + gap;
  const top = body.y - figure - gap;
  const bottom = body.y + gap;
  return caret.x + caret.w > left && caret.x < right && caret.y + caret.h > top && caret.y < bottom;
}

/**
 * Куда отойти от поля ввода: по своей опоре в сторону, где места больше, на `away` от него; не выходит —
 * на «пол» в дальний от поля угол.
 */
export function stepAside(
  list: readonly Surface[],
  spot: Spot | null,
  caret: Rect,
  figure: number,
  away = 320,
): Spot | null {
  const center = caret.x + caret.w / 2;
  const surface = spot?.surface;
  if (surface !== undefined && surface.kind !== "side" && surface.kind !== "ceiling") {
    for (const x of [center - away, center + away].sort(
      (a, b) => Math.abs(a - (spot?.x ?? 0)) - Math.abs(b - (spot?.x ?? 0)),
    )) {
      if (x < surface.x0 || x > surface.x1) continue;
      const next = spotOn(surface, x, surface.y);
      if (!inTheWay(caret, next, figure, 40)) return next;
    }
  }
  const floor = list.find((one) => one.kind === "floor");
  if (floor === undefined) return null;
  const far = center < (floor.x0 + floor.x1) / 2 ? floor.x1 : floor.x0;
  const next = spotOn(floor, far, floor.y);
  return inTheWay(caret, next, figure, 40) ? null : next;
}
