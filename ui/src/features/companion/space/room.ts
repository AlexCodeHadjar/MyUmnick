/**
 * Опоры, на которых персонаж виден целиком (просьба пользователя 2026-11-17): не уходит головой за верх
 * экрана, сидя на значке или окне у верхнего края, и не прячется наполовину за боковыми краями.
 * `figure` — рост холста позы в CSS-пикселях (`height * CANVAS_RATIO`).
 */
import { wallX, type Surface } from "./anchors";
import type { Rect } from "./world";

/** Над сиденьем — 0,6 холста (точка опоры `sit_edge` — 0,62, сверху поля рисунка). */
const ABOVE_SEAT = 0.6;
/** Стоя у стены, над ступнями — почти весь холст. */
const ABOVE_FEET = 0.95;
/** Видимая полуширина фигуры — четверть роста холста: по бокам холста пусто. */
const HALF_WIDTH = 0.25;
const SLACK = 20;

export function fitScreen(list: readonly Surface[], monitor: Rect, figure: number): Surface[] {
  const half = figure * HALF_WIDTH;
  const lo = monitor.x + half;
  const hi = monitor.x + monitor.w - half;
  const out: Surface[] = [];
  for (const surface of list) {
    if (surface.kind === "side") {
      out.push(...fitSide(surface, lo, hi, monitor.y + figure * ABOVE_FEET));
      continue;
    }
    if (surface.kind === "edge" && surface.y - figure * ABOVE_SEAT < monitor.y) continue;
    const span = fitSpan(surface.x0, surface.x1, lo, hi);
    if (span !== null) out.push({ ...surface, x0: span[0], x1: span[1] });
  }
  return out;
}

/**
 * Отрезок опоры, где центр фигуры в [lo, hi]. Узкая опора (значок у края экрана) — персонаж садится
 * со сдвигом внутрь экрана, если до неё не дальше 40 px; иначе опоры нет.
 */
function fitSpan(x0: number, x1: number, lo: number, hi: number): [number, number] | null {
  const a = Math.max(x0, lo - SLACK);
  const b = Math.min(x1, hi + SLACK);
  if (b - a >= SLACK * 2) return [a, b];
  const mid = Math.min(hi, Math.max(lo, (x0 + x1) / 2));
  if (mid < x0 - 40 || mid > x1 + 40) return null;
  return [mid - SLACK, mid + SLACK];
}

/** Бок: место у стены — на экране; стоять у стены можно только там, где голова не за верхом. */
function fitSide(
  surface: Extract<Surface, { kind: "side" }>,
  lo: number,
  hi: number,
  lean: number,
): Surface[] {
  const x = wallX(surface);
  if (x < lo - 15 || x > hi + 15) return [];
  // Верхние 60 px бока — «висит», ниже — стоит (`spotOn`).
  const hang = { ...surface, y1: Math.min(surface.y1, surface.y0 + 50) };
  if (surface.y1 < lean) return [hang];
  if (surface.y0 + 60 >= lean) return [surface];
  return [hang, { ...surface, y0: lean - 60 }];
}
