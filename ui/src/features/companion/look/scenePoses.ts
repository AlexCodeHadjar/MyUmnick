/**
 * Позы сцен настольного спутника (FRAMES-6): замены, точки опоры, частота кадров и одноразовые сцены.
 * Отдельно от `pack.ts`, чтобы таблицы поз пакета не разрастались.
 */
import type { Pose } from "../space";

export type ScenePose =
  | "purr"
  | "knock"
  | "carry_box"
  | "stamp"
  | "hug_paper"
  | "flinch"
  | "blown"
  | "read"
  | "draw"
  | "juggle"
  | "trip"
  | "chase"
  | "inspect"
  | "pocket"
  | "put_back"
  | "throw"
  | "dust_hands"
  | "build"
  | "note_put"
  | "note_take";

/** Без своих кадров (пакет пользователя) сцена рисуется той позой, что была до FRAMES-6. */
export const SCENE_FALLBACK: Record<ScenePose, readonly Pose[]> = {
  purr: ["pet", "stand"],
  knock: ["wave", "stand"],
  carry_box: ["walk", "stand"],
  stamp: ["stand"],
  hug_paper: ["pet", "stand"],
  flinch: ["pet", "stand"],
  blown: ["float", "stand"],
  read: ["stand"],
  draw: ["stand"],
  juggle: ["dance", "stand"],
  trip: ["dizzy", "stand"],
  chase: ["walk", "stand"],
  inspect: ["stand"],
  pocket: ["stand"],
  put_back: ["stand"],
  throw: ["stand"],
  dust_hands: ["stand"],
  build: ["stand"],
  note_put: ["stand"],
  note_take: ["walk", "stand"],
};

const FEET: readonly [number, number] = [0.5, 0.97];
/** Сидит на полу, как `sit_corner`. */
const SEAT: readonly [number, number] = [0.5, 0.95];

export const SCENE_ANCHORS: Record<ScenePose, readonly [number, number]> = {
  purr: FEET,
  knock: FEET,
  carry_box: FEET,
  stamp: FEET,
  hug_paper: FEET,
  flinch: FEET,
  // Летит по ветру: опора — середина тела (этапы 2026-11-19: 0,5 — иначе огонь сверху обрезается).
  blown: [0.5, 0.5],
  read: SEAT,
  draw: SEAT,
  juggle: FEET,
  trip: FEET,
  chase: FEET,
  inspect: FEET,
  pocket: FEET,
  put_back: FEET,
  throw: FEET,
  dust_hands: FEET,
  build: FEET,
  note_put: FEET,
  note_take: FEET,
};

/** Кадров в секунду. У одноразовых сцен — так, чтобы кадры уложились в длительность сцены. */
export const SCENE_FPS: Partial<Record<Pose, number>> = {
  purr: 4,
  knock: 8,
  carry_box: 8,
  stamp: 6,
  hug_paper: 5,
  flinch: 6,
  blown: 8,
  read: 2,
  draw: 3,
  juggle: 6,
  trip: 6,
  chase: 12,
  // Вертит находку 3 с (KEEPSAKE_TIMING: inspectMs − endingMs): 6 кадров по 2 в секунду.
  inspect: 2,
  pocket: 4,
  put_back: 4,
  throw: 6,
  dust_hands: 6,
  build: 4,
  note_put: 4,
  note_take: 5,
  // Зевает один раз за эмоцию (2–2,5 с): 4 кадра.
  yawn: 2,
};

/** Частота одноразовой сцены без своей записи в `SCENE_FPS`. */
const ONCE_DEFAULT_FPS = 3;

/** Одноразовые сцены: кадры идут по разу от начала позы и держат последний, а не крутятся. */
export const ONCE: ReadonlySet<Pose> = new Set<Pose>([
  "yawn",
  "stamp",
  "hug_paper",
  "flinch",
  "trip",
  "inspect",
  "pocket",
  "put_back",
  "throw",
  "dust_hands",
  "build",
  "note_put",
  "note_take",
]);

/** Циклы с направлением (бег, ноша) — кольцом, а не «туда-обратно». */
export const SCENE_RING: readonly Pose[] = ["carry_box", "chase", "blown", "juggle"];

/**
 * Кадры одноразовой сцены по порядку: `<имя>_1…N`. Базовый кадр `<имя>` — копия одного из них (этапы
 * 2026-11-19: у штампа — удар, кадр 4) и в порядок не вставляется; он нужен, только если номерных нет.
 */
export function onceFrames(name: string, loop: readonly string[], hasBase: boolean): string[] {
  if (loop.length > 0) return [...loop];
  return hasBase ? [name] : [];
}

/** Номер кадра одноразовой сцены: `since` секунд от начала позы, последний кадр держится. */
export function onceIndex(pose: Pose, since: number, length: number): number {
  const fps = SCENE_FPS[pose] ?? ONCE_DEFAULT_FPS;
  return Math.min(length - 1, Math.max(0, Math.floor(since * fps)));
}
