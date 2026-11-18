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
  /** Куда сесть наверху (или встать внизу, если `down`). */
  target: Spot;
  /** Спуск: сползает по боку с крыши окна вниз (COMPANION.md, этап 2). */
  down?: boolean;
  /** Остаться на стене в `target` (за курсором, 2026-11-18), а не перелезать на крышу. */
  stay?: boolean;
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

/** Спуск ниже — хотя бы на столько; ближе — прыжок. */
const MIN_DROP = 150;

/**
 * Маршрут спуска с крыши окна `from` вниз на опору `to` или `null` (прыгать): дойти по крыше до края над
 * боком и сползти по стене. Бок должен быть над опорой-целью, иначе внизу не на что встать.
 */
export function descendRoute(surfaces: readonly Surface[], from: Spot, to: Spot): Climb | null {
  const top = from.surface;
  const floor = to.surface;
  if (top.kind !== "edge" || top.host < 0) return null;
  if (floor.kind !== "edge" && floor.kind !== "floor") return null;
  if (to.y - from.y < MIN_DROP) return null;
  let best: Climb | null = null;
  for (const side of surfaces) {
    if (side.kind !== "side" || side.host !== top.host) continue;
    const x = wallX(side);
    if (x < floor.x0 || x > floor.x1) continue;
    const foot = spotOn(top, side.x, from.y);
    if (best === null || Math.abs(foot.x - from.x) < Math.abs(best.foot.x - from.x)) {
      best = { foot, side, target: spotOn(floor, x, to.y), down: true };
    }
  }
  return best;
}
