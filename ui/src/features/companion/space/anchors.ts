/**
 * Точки привязки спутника (Этап 23, раздел 4.3): где он может сидеть, стоять, висеть и какая поза этому
 * месту подходит. Чистые функции над картиной рабочего стола в CSS-пикселях — проверяются тестами.
 */
import type { World } from "./world";

export type Pose =
  | "stand"
  | "walk"
  | "sit_edge"
  | "perch_corner"
  | "lean_side"
  | "hang_side"
  | "sit_corner"
  | "laydown"
  | "sleep"
  | "held"
  | "float"
  /** Тыкает пальцем в элемент экрана (ADR-0048); точка опоры — кончик пальца. */
  | "poke"
  /** Довольный, когда гладят (стоя); точка опоры — ступни, как у `stand`. */
  | "pet"
  | "reach"
  /** Поёт в режиме радио: наушники на шее, микрофон (BEHAVIOR §8). */
  | "sing"
  /** Радио на паузе: слушает, наушники на шее. */
  | "radio_idle"
  /** Лезет по стене справа от себя; точка опоры — середина тела (BEHAVIOR §9). */
  | "climb"
  /** Кружится голова после тряски (T4). */
  | "dizzy"
  /** Машет рукой: приветствие (T6, T7, T8). */
  | "wave"
  /** Зевает: ночь, перед сном (T16). */
  | "yawn"
  /** Танцует под музыку плеера (T15). */
  | "dance"
  /** «Смотрим вместе»: сидит в углу экрана с попкорном (BEHAVIOR §11). */
  | "watch"
  /** Радио: сидит на музыкальном ящике, медленно болтает ножками; на табло — станция (FRAMES-3). */
  | "jukebox"
  /** Выглядывает из-за края экрана: видна голова и рука; точка опоры — край кадра (FRAMES-2 §6). */
  | "peek"
  // Сцены настольного спутника (FRAMES-6, ADR-0055/0056): свои кадры вместо чужих поз и эмодзи.
  /** Жмурится, когда гладят курсором. */
  | "purr"
  | "knock"
  | "carry_box"
  | "stamp"
  | "hug_paper"
  | "flinch"
  /** Сдувает ветром (Win+D); точка опоры — середина тела. */
  | "blown"
  | "read"
  | "draw"
  | "juggle"
  | "trip"
  | "chase"
  /** Вертит находку; значок файла рисует код. */
  | "inspect"
  | "pocket"
  | "put_back"
  | "throw"
  | "dust_hands"
  | "build"
  | "note_put"
  | "note_take";

/** Опора: горизонтальная (край окна, «пол») или вертикальная (бок окна). */
export type Surface =
  | { kind: "edge"; host: number; x0: number; x1: number; y: number }
  | { kind: "floor"; x0: number; x1: number; y: number }
  /** Верх экрана: висит, держась за край, — в том числе в верхних углах. */
  | { kind: "ceiling"; x0: number; x1: number; y: number }
  | { kind: "side"; host: number; x: number; y0: number; y1: number; side: "left" | "right" };

/** Место на опоре: точка опоры позы (сиденье, ступни, ладони) и сама поза. */
export interface Spot {
  surface: Surface;
  x: number;
  y: number;
  pose: Pose;
  /** Куда смотрит: при сидении в правом углу — влево и наоборот. */
  facing: 1 | -1;
}

/** «Хозяин» боков экрана: не окно, за ним не следят и его не опрашивают. */
export const SCREEN = -1;
/** Бока экрана — чуть внутри: персонаж облокачивается, а не уходит наполовину за край. */
const WALL_INSET = 0;
/** От стены до точки опоры: полкорпуса, чтобы персонаж был виден целиком и не заходил в окно. */
const WALL_GAP = 60;
const WALL_GAP_SCREEN = 70;

export const SNAP_RADIUS = 40;
/** Ближе к концу опоры — «угловая» поза. */
const CORNER = 36;

/** Все опоры картины: открытые участки верхних краёв окон, бока окон, «пол» над панелью задач. */
export function surfaces(world: World): Surface[] {
  const list: Surface[] = [];
  for (const seat of world.seats) {
    for (const [x0, x1] of seat.open) {
      list.push({ kind: "edge", host: seat.id, x0, x1, y: seat.rect.y });
    }
    const { x, y, w, h } = seat.rect;
    const y1 = y + Math.min(h, 240);
    list.push({ kind: "side", host: seat.id, x, y0: y + 8, y1, side: "left" });
    list.push({ kind: "side", host: seat.id, x: x + w, y0: y + 8, y1, side: "right" });
  }
  const { work } = world;
  list.push({ kind: "floor", x0: work.x, x1: work.x + work.w, y: work.y + work.h });
  const m = world.monitor;
  list.push({ kind: "ceiling", x0: m.x, x1: m.x + m.w, y: m.y });
  const bottom = work.y + work.h;
  list.push({
    kind: "side",
    host: SCREEN,
    x: m.x + WALL_INSET,
    y0: m.y + 8,
    y1: bottom,
    side: "right",
  });
  list.push({
    kind: "side",
    host: SCREEN,
    x: m.x + m.w - WALL_INSET,
    y0: m.y + 8,
    y1: bottom,
    side: "left",
  });
  return list;
}

function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}

/** Место на опоре `surface`, ближайшее к точке; поза — по месту. */
export function spotOn(surface: Surface, px: number, py: number): Spot {
  if (surface.kind === "side") {
    const y = clamp(py, surface.y0, surface.y1);
    // Лицом от стены (просьба пользователя 2026-11-17) и рядом с ней, а не наполовину за краем:
    // стена справа от персонажа (`left` — левый бок окна или правый край экрана) — смотрит влево.
    const away: 1 | -1 = surface.side === "left" ? -1 : 1;
    const x = wallX(surface);
    // Наверху бока — висит, держась за край; ниже — стоит у стены.
    const pose: Pose = y - surface.y0 < 60 ? "hang_side" : "lean_side";
    return { surface, x, y, pose, facing: away };
  }
  const x = clamp(px, surface.x0 + 20, surface.x1 - 20);
  if (surface.kind === "ceiling") {
    return { surface, x, y: surface.y + 4, pose: "hang_side", facing: x > surface.x1 / 2 ? -1 : 1 };
  }
  const nearLeft = x - surface.x0 < CORNER + 20;
  const nearRight = surface.x1 - x < CORNER + 20;
  // Узкая опора (значок) — сидит посередине, а не «на углу».
  const corner = (nearLeft || nearRight) && surface.x1 - surface.x0 >= 140;
  const facing: 1 | -1 = nearRight ? -1 : 1;
  if (surface.kind === "edge") {
    return { surface, x, y: surface.y, pose: corner ? "perch_corner" : "sit_edge", facing };
  }
  return { surface, x, y: surface.y, pose: corner ? "sit_corner" : "stand", facing };
}

/** Окно, на котором место (за ним следят), или `null` — «пол», верх и бока экрана. */
export function hostId(surface: Surface): number | null {
  if (surface.kind === "edge" || surface.kind === "side")
    return surface.host < 0 ? null : surface.host;
  return null;
}

/** «Хозяин» значков рабочего стола: они опоры, но не окна (оболочка их не отслеживает). */
export const ICONS = -2;

/** Верх значков рабочего стола как опоры (по образцу Capri): сесть на «Корзину» или «Steam». */
export function iconSurfaces(
  icons: readonly { x: number; y: number; w: number; h: number }[],
): Surface[] {
  return icons.map((r) => ({
    kind: "edge",
    host: ICONS,
    x0: r.x + 4,
    x1: r.x + r.w - 4,
    y: r.y + 6,
  }));
}

/** Где стоит персонаж у бока: на полкорпуса от стены, внутри экрана и вне окна. */
export function wallX(surface: Extract<Surface, { kind: "side" }>): number {
  const away = surface.side === "left" ? -1 : 1;
  return surface.x + away * (surface.host === SCREEN ? WALL_GAP_SCREEN : WALL_GAP);
}

function distance(surface: Surface, px: number, py: number): number {
  if (surface.kind === "side") {
    const dy = py < surface.y0 ? surface.y0 - py : py > surface.y1 ? py - surface.y1 : 0;
    // От места у стены, где персонаж стоит, а не от самой стены (отступ — `wallX`).
    return Math.hypot(px - wallX(surface), dy);
  }
  const dx = px < surface.x0 ? surface.x0 - px : px > surface.x1 ? px - surface.x1 : 0;
  return Math.hypot(dx, py - surface.y);
}

/** Ближайшее место в радиусе `radius` или `null` — тогда спутник «парит» и опускается сам. */
export function snap(
  list: readonly Surface[],
  px: number,
  py: number,
  radius = SNAP_RADIUS,
): Spot | null {
  let best: Surface | null = null;
  let bestDistance = radius;
  for (const surface of list) {
    const d = distance(surface, px, py);
    if (d <= bestDistance) {
      best = surface;
      bestDistance = d;
    }
  }
  return best === null ? null : spotOn(best, px, py);
}

/** Горизонтальная опора под точкой (падение): ближайшая сверху вниз, иначе «пол». */
export function below(list: readonly Surface[], px: number, py: number): Spot | null {
  let best: Extract<Surface, { kind: "edge" | "floor" }> | null = null;
  for (const surface of list) {
    // «Пол» ловит в любой точке по ширине: его отрезок сужен до места, где персонаж виден целиком
    // (`room.ts`), а падение у самого края иначе не находило опоры и уходило за экран (баг 2026-11-17).
    if (surface.kind === "side" || surface.kind === "ceiling" || surface.y < py) continue;
    if (surface.kind === "edge" && (px < surface.x0 || px > surface.x1)) continue;
    if (best === null || surface.y < best.y) best = surface;
  }
  return best === null ? null : spotOn(best, px, py);
}

/** Куда сесть, когда активным стало окно: правая треть верхнего края, на открытом участке. */
export function seatSpot(
  list: readonly Surface[],
  host: number,
  x: number,
  w: number,
): Spot | null {
  const want = x + w * 0.75;
  let best: Spot | null = null;
  for (const surface of list) {
    if (surface.kind !== "edge" || surface.host !== host) continue;
    const spot = spotOn(surface, want, surface.y);
    if (best === null || Math.abs(spot.x - want) < Math.abs(best.x - want)) best = spot;
  }
  return best;
}

/** Место на «полу» у правого края — рабочий стол или развёрнутое окно. */
export function floorSpot(list: readonly Surface[], corner: boolean): Spot | null {
  const floor = list.find(
    (surface): surface is Extract<Surface, { kind: "floor" }> => surface.kind === "floor",
  );
  if (floor === undefined) return null;
  return spotOn(floor, corner ? floor.x1 : floor.x1 - 180, floor.y);
}

/** Та же опора в новой картине (окно сдвинули): по хозяину и виду. */
export function sameSurface(a: Surface, b: Surface): boolean {
  if (a.kind === "floor" || b.kind === "floor" || a.kind === "ceiling" || b.kind === "ceiling") {
    return a.kind === b.kind;
  }
  if (a.kind === "edge" && b.kind === "edge") return a.host === b.host;
  return a.kind === "side" && b.kind === "side" && a.host === b.host && a.side === b.side;
}
