/**
 * Пакет поз спутника (Этап 23, раздел 5.2, по образцу Capri): одна PNG на позу и варианты `_blink`, `_talk`.
 * Картинки пользователь загружает папкой из меню окошка; хранятся в IndexedDB окна (`pose:<имя>`), поэтому
 * их видит и слой спутника. Нет позы — цепочка замен, нет ничего — временные силуэты (`placeholder.ts`).
 */
import { characterChannel, run } from "../../avatar/portrait/picture";
import type { Pose } from "../space";
import {
  ONCE,
  SCENE_ANCHORS,
  SCENE_FALLBACK,
  SCENE_FPS,
  SCENE_RING,
  onceFrames,
  onceIndex,
} from "./scenePoses";

/** Замены отсутствующей позы, в порядке предпочтения; всё кончается позой `stand`. */
export const FALLBACK: Record<Pose, readonly Pose[]> = {
  stand: [],
  walk: ["stand"],
  sit_edge: ["stand"],
  perch_corner: ["sit_edge", "stand"],
  sit_corner: ["laydown", "sit_edge", "stand"],
  lean_side: ["stand"],
  hang_side: ["held", "float", "stand"],
  laydown: ["sit_edge", "stand"],
  sleep: ["laydown", "sit_edge", "stand"],
  held: ["float", "stand"],
  float: ["held", "stand"],
  poke: ["lean_side", "stand"],
  pet: ["stand"],
  reach: ["wave", "stand"],
  // Кадров BEHAVIOR §10 пока нет (FRAMES-2.md): спутник не пропадает, рисуется ближайшая поза.
  sing: ["radio_idle", "stand"],
  radio_idle: ["stand"],
  climb: ["hang_side", "held", "float", "stand"],
  dizzy: ["float", "stand"],
  wave: ["stand"],
  yawn: ["stand"],
  dance: ["stand"],
  watch: ["sit_corner", "sit_edge", "stand"],
  jukebox: ["sing", "radio_idle", "stand"],
  peek: ["sit_corner", "stand"],
  ...SCENE_FALLBACK,
};

/** Точка опоры позы — доля ширины и высоты картинки: сиденье, ступни, ладони, «шиворот». */
export const ANCHORS: Record<Pose, readonly [number, number]> = {
  stand: [0.5, 0.97],
  walk: [0.5, 0.97],
  lean_side: [0.5, 0.97],
  sit_edge: [0.5, 0.62],
  perch_corner: [0.5, 0.62],
  sit_corner: [0.5, 0.95],
  laydown: [0.5, 0.92],
  sleep: [0.5, 0.92],
  held: [0.5, 0.06],
  hang_side: [0.5, 0.04],
  // Середина тела; 0,55, а не 0,6 — у кадров этапов 2026-11-19 ноги в полёте ниже (иначе обрезаются).
  float: [0.5, 0.55],
  // Кончик вытянутого вперёд пальца — справа на уровне груди (кадр poke, раздел 7.2).
  poke: [0.88, 0.42],
  pet: [0.5, 0.97],
  reach: [0.5, 0.97],
  sing: [0.5, 0.97],
  radio_idle: [0.5, 0.97],
  climb: [0.5, 0.5],
  dizzy: [0.5, 0.97],
  wave: [0.5, 0.97],
  yawn: [0.5, 0.97],
  dance: [0.5, 0.97],
  watch: [0.5, 0.95],
  jukebox: [0.5, 0.97],
  // Левый край кадра — край экрана; голова посередине высоты.
  peek: [0, 0.5],
  ...SCENE_ANCHORS,
};

/** Холст позы 512×1024, рост персонажа ~960 (раздел 7.2): холст выше роста в 1024/960 раз. */
export const CANVAS_RATIO = 1024 / 960;

const PREFIX = "pose:";
/** Имя позы, варианта или кадра: `walk`, `stand_talk`, `walk_3`, `stand_talk_2`. */
const NAME = /^[a-z]+(?:_[a-z]+)*(?:_\d{1,2})?$/;

/** Частота кадров зацикленной позы (`<поза>_1…N`), кадров в секунду. */
// Частоты — по заданию этапов (docs/character/ANIMATION-STAGES.md, кадры 2026-11-19).
export const LOOP_FPS: Partial<Record<Pose, number>> = {
  walk: 10,
  stand: 6,
  sit_edge: 5,
  perch_corner: 5,
  held: 8,
  hang_side: 6,
  float: 8,
  poke: 6,
  pet: 8,
  laydown: 3,
  // Радио — спокойно (просьба пользователя 2026-11-17: «слишком дёргается»): медленные циклы.
  sing: 3,
  jukebox: 2,
  climb: 6,
  dizzy: 4,
  wave: 8,
  dance: 8,
  watch: 3,
  lean_side: 4,
  sit_corner: 4,
  sleep: 2,
  reach: 5,
  peek: 4,
  ...SCENE_FPS,
};

/** Что сейчас с персонажем: для выбора кадра. `blink` — доля моргания 0…1 или `null`. */
export interface FrameState {
  time: number;
  mouth: number;
  speaking: boolean;
  blink: number | null;
  /** Секунд с начала позы: одноразовые сцены идут кадр за кадром по ним (`ONCE`). */
  since?: number;
}

/** Кадры `<имя>_1`, `<имя>_2` … подряд, пока есть. */
export function sequence(name: string, have: ReadonlySet<string>): string[] {
  const list: string[] = [];
  while (have.has(`${name}_${String(list.length + 1)}`))
    list.push(`${name}_${String(list.length + 1)}`);
  return list;
}

function frameOf(name: string, pose: Pose, state: FrameState, have: ReadonlySet<string>): string {
  // Спит, а позы сна нет: замена с закрытыми глазами.
  if (pose === "sleep" && name !== "sleep" && have.has(`${name}_blink`)) return `${name}_blink`;
  // Поёт: тело качается циклом `sing_1…4` (рот там уже открыт), кадры рта — только на громких местах.
  // Поёт или сидит на ящике — кадры рта не вклиниваются в спокойный цикл совсем.
  const threshold = pose === "sing" || pose === "jukebox" ? 2 : 0.08;
  if (state.speaking && state.mouth > threshold) {
    // Рот по громкости: `_talk_1` приоткрыт … `_talk_N` открыт широко; без них — один `_talk`.
    const talk = sequence(`${name}_talk`, have);
    const level = Math.min(talk.length - 1, Math.floor(state.mouth * talk.length));
    const open = talk[level];
    if (open !== undefined) return open;
    if (state.mouth > 0.25 && have.has(`${name}_talk`)) return `${name}_talk`;
  }
  if (state.blink !== null && have.has(`${name}_blink`)) {
    // Полуприкрытые глаза до и после закрытых — моргание мягче.
    const half = `${name}_blink_1`;
    const edge = state.blink < 0.3 || state.blink > 0.7;
    return edge && have.has(half) ? half : `${name}_blink`;
  }
  const loop = sequence(name, have);
  if (ONCE.has(pose) && state.since !== undefined) {
    const frames = onceFrames(name, loop, have.has(name));
    const frame = frames[onceIndex(pose, state.since, frames.length)];
    if (frame !== undefined) return frame;
  }
  if (loop.length > 0) {
    const frame = loop[loopIndex(pose, state.time, loop.length)];
    if (frame !== undefined) return frame;
  }
  return have.has(name) ? name : `${name}_1`;
}

/**
 * Кадр для позы с учётом замен: речь (кадры рта по громкости), моргание, зацикленные кадры позы,
 * одна картинка. Ничего нет — `null` (временный силуэт).
 */
export function pickFrame(pose: Pose, state: FrameState, have: ReadonlySet<string>): string | null {
  for (const name of [pose, ...FALLBACK[pose], "stand"]) {
    if (have.has(name) || have.has(`${name}_1`)) return frameOf(name, pose, state, have);
  }
  return null;
}

/** Имя позы из имени файла: `Sit_Edge.PNG` → `sit_edge`; не картинка — `null`. */
export function poseName(fileName: string): string | null {
  const match = /^(.+)\.(png|webp)$/i.exec(fileName);
  const name = match?.[1]?.toLowerCase() ?? "";
  return NAME.test(name) ? name : null;
}

/** Сохранить позы из выбранной папки; вернёт, сколько картинок принято. */
export async function savePoses(files: readonly File[]): Promise<number> {
  let saved = 0;
  for (const file of files) {
    const name = poseName(file.name);
    if (name === null || file.size > 20 * 1024 * 1024) continue;
    await run("readwrite", (store) => store.put(file, PREFIX + name));
    saved += 1;
  }
  characterChannel?.postMessage("pack");
  return saved;
}

export async function clearPoses(): Promise<void> {
  const keys = await run("readonly", (store) => store.getAllKeys());
  for (const key of keys) {
    if (typeof key === "string" && key.startsWith(PREFIX)) {
      await run("readwrite", (store) => store.delete(key));
    }
  }
  characterChannel?.postMessage("pack");
}

/** Встроенный персонаж (`ui/public/characters/default/`; подгонка — `docs/character/README.md`). */
export const DEFAULT_PACK = "/characters/default";

function bitmap(blob: Blob, height: number): Promise<ImageBitmap> {
  return createImageBitmap(blob, {
    resizeHeight: Math.round(height * CANVAS_RATIO * devicePixelRatio),
    resizeQuality: "high",
  });
}

/** Высота кадра встроенного пакета; выше — место над головой (штамп, рожки), FRAMES-6 «Принято». */
export const PACK_HEIGHT = 768;

/**
 * Кадр встроенного пакета в общем масштабе: кадр выше `PACK_HEIGHT` уменьшается во столько же раз,
 * что и обычный, — персонаж того же роста, а лишнее место остаётся сверху.
 */
async function packBitmap(blob: Blob, height: number): Promise<ImageBitmap> {
  const full = await createImageBitmap(blob);
  try {
    const tall = full.height / PACK_HEIGHT;
    return await createImageBitmap(full, {
      resizeHeight: Math.round(height * CANVAS_RATIO * devicePixelRatio * tall),
      resizeQuality: "high",
    });
  } finally {
    full.close();
  }
}

/**
 * Позы, с которых персонаж начинает (ускорение запуска, 2026-11-19): выход из портала, падение, стоит,
 * идёт. Их кадры декодируются первыми — персонаж на экране за доли секунды, остальные ~280 кадров
 * догружаются, пока он уже ходит (все сразу — ~1,5 с декодирования до первого кадра).
 */
const FIRST_POSES: ReadonlySet<string> = new Set(["stand", "walk", "float", "held", "sit_corner"]);

/** Кадр одной из первых поз (`stand`, `stand_2`), но не переход (`stand_to_wave_1`). */
export function isFirstFrame(name: string): boolean {
  if (name.includes("_to_")) return false;
  const base = name.replace(/_\d+$/u, "");
  return FIRST_POSES.has(base);
}

async function decodeInto(
  poses: Map<string, ImageBitmap>,
  names: readonly string[],
  height: number,
): Promise<void> {
  await Promise.all(
    names.map(async (name) => {
      const response = await fetch(`${DEFAULT_PACK}/${name}.webp`);
      if (response.ok) poses.set(name, await packBitmap(await response.blob(), height));
    }),
  );
}

/**
 * Позы встроенного персонажа; файлов нет (вкладка без сборки) — пусто, будут силуэты. Сначала — первые
 * позы, остальные — в `rest`, который заполняет ту же карту и завершается, когда догрузил всё.
 */
async function defaultPoses(height: number): Promise<Staged> {
  const poses = new Map<string, ImageBitmap>();
  try {
    const list: unknown = await (await fetch(`${DEFAULT_PACK}/index.json`)).json();
    if (!Array.isArray(list)) return { poses, rest: Promise.resolve() };
    const names = list.filter(
      (name): name is string => typeof name === "string" && poseName(`${name}.webp`) !== null,
    );
    await decodeInto(poses, names.filter(isFirstFrame), height);
    const rest = decodeInto(
      poses,
      names.filter((name) => !isFirstFrame(name)),
      height,
    ).catch(() => undefined);
    return { poses, rest };
  } catch {
    // Нет пакета — временные силуэты.
    return { poses, rest: Promise.resolve() };
  }
}

/** Позы: карта сразу (первые кадры) и обещание догрузки остальных в ту же карту. */
export interface Staged {
  poses: Map<string, ImageBitmap>;
  rest: Promise<void>;
}

/**
 * Позы как `ImageBitmap`, уменьшенные до экранного размера (5.2: экономная загрузка): загруженные
 * пользователем папкой, а если их нет — встроенный персонаж.
 */
export async function loadPoses(height: number): Promise<Staged> {
  const own = await userPoses(height);
  return own.size > 0 ? { poses: own, rest: Promise.resolve() } : defaultPoses(height);
}

async function userPoses(height: number): Promise<Map<string, ImageBitmap>> {
  const poses = new Map<string, ImageBitmap>();
  try {
    const keys = await run("readonly", (store) => store.getAllKeys());
    for (const key of keys) {
      if (typeof key !== "string" || !key.startsWith(PREFIX)) continue;
      const blob: unknown = await run("readonly", (store) => store.get(key));
      if (!(blob instanceof Blob)) continue;
      poses.set(key.slice(PREFIX.length), await bitmap(blob, height));
    }
  } catch {
    // Хранилище недоступно — будут временные силуэты.
  }
  return poses;
}

/** Циклы с направлением (походка, лазанье, танец) — кольцом; спокойные — «туда-обратно» (ANIMATION.md). */
export const RING: ReadonlySet<Pose> = new Set<Pose>([
  "dizzy",
  "walk",
  "climb",
  "dance",
  "jukebox",
  ...SCENE_RING,
]);

/**
 * Номер кадра цикла. «Туда-обратно» (1-2-3-4-3-2): нет скачка с последнего кадра на первый, и из
 * четырёх кадров выходит шесть фаз.
 */
export function loopIndex(pose: Pose, time: number, length: number): number {
  const step = Math.floor(time * (LOOP_FPS[pose] ?? 6));
  if (RING.has(pose) || length < 3) return step % length;
  const period = 2 * length - 2;
  const phase = step % period;
  return phase < length ? phase : period - phase;
}
