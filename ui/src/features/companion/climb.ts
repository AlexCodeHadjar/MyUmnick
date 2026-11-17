/**
 * Маршрут лазанья (BEHAVIOR §9): на окно выше — дойти по своей опоре до бока окна и залезть по нему,
 * а не прыгать. Чистая функция над опорами — проверяется тестами.
 */
import { spotOn, wallX, type Spot, type Surface } from "./anchors";

/** Лезть стоит, если крыша выше хотя бы на столько; ниже — прыжок. */
const MIN_RISE = 120;
/** Дальше по горизонтали до стены — молния или прыжок, как раньше. */
const MAX_WALK = 300;

export interface Climb {
  /** Где встать у основания стены (на текущей опоре). */
  foot: Spot;
  /** Бок окна, по которому лезет. */
  side: Extract<Surface, { kind: "side" }>;
  /** Куда сесть наверху. */
  target: Spot;
}

/**
 * Маршрут с места `from` на верх окна `to` или `null` (прыгать). `bottom` — низ окна-цели: окно должно
 * доходить до опоры персонажа, иначе внизу стены нет и лезть не по чему.
 */
export function climbRoute(
  surfaces: readonly Surface[],
  from: Spot,
  to: Spot,
  bottom: number,
): Climb | null {
  const start = from.surface;
  const top = to.surface;
  if (top.kind !== "edge" || top.host < 0) return null;
  if (start.kind !== "edge" && start.kind !== "floor") return null;
  if (from.y - to.y < MIN_RISE || bottom < from.y - 40) return null;
  let best: Climb | null = null;
  for (const side of surfaces) {
    if (side.kind !== "side" || side.host !== top.host) continue;
    const x = wallX(side);
    if (x < start.x0 || x > start.x1 || Math.abs(x - from.x) > MAX_WALK) continue;
    const foot = spotOn(start, x, from.y);
    if (Math.abs(foot.x - x) > 4) continue;
    if (best === null || Math.abs(x - from.x) < Math.abs(best.foot.x - from.x)) {
      best = { foot, side, target: to };
    }
  }
  return best;
}
