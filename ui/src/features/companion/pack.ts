/**
 * Пакет поз спутника (Этап 23, раздел 5.2, по образцу Capri): одна PNG на позу и варианты `_blink`, `_talk`.
 * Картинки пользователь загружает папкой из меню окошка; хранятся в IndexedDB окна (`pose:<имя>`), поэтому
 * их видит и слой спутника. Нет позы — цепочка замен, нет ничего — временные силуэты (`placeholder.ts`).
 */
import { characterChannel, run } from "../avatar/portrait/picture";
import type { Pose } from "./anchors";

export type Variant = "" | "_blink" | "_talk";

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
  float: [0.5, 0.6],
};

/** Холст позы 512×1024, рост персонажа ~960 (раздел 7.2): холст выше роста в 1024/960 раз. */
export const CANVAS_RATIO = 1024 / 960;

const PREFIX = "pose:";
const NAME = /^[a-z_]+$/;

/** Какой ключ рисовать: поза с вариантом, без варианта, затем замены. */
export function resolve(pose: Pose, variant: Variant, have: ReadonlySet<string>): string | null {
  for (const name of [pose, ...FALLBACK[pose], "stand"]) {
    if (variant !== "" && have.has(name + variant)) return name + variant;
    if (have.has(name)) return name;
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

/** Позы встроенного персонажа; файлов нет (вкладка без сборки) — пусто, будут силуэты. */
async function defaultPoses(height: number): Promise<Map<string, ImageBitmap>> {
  const poses = new Map<string, ImageBitmap>();
  try {
    const list: unknown = await (await fetch(`${DEFAULT_PACK}/index.json`)).json();
    if (!Array.isArray(list)) return poses;
    const names: unknown[] = list;
    await Promise.all(
      names.map(async (name) => {
        if (typeof name !== "string" || poseName(`${name}.webp`) === null) return;
        const response = await fetch(`${DEFAULT_PACK}/${name}.webp`);
        if (response.ok) poses.set(name, await bitmap(await response.blob(), height));
      }),
    );
  } catch {
    // Нет пакета — временные силуэты.
  }
  return poses;
}

/**
 * Позы как `ImageBitmap`, уменьшенные до экранного размера (5.2: экономная загрузка): загруженные
 * пользователем папкой, а если их нет — встроенный персонаж.
 */
export async function loadPoses(height: number): Promise<Map<string, ImageBitmap>> {
  const own = await userPoses(height);
  return own.size > 0 ? own : defaultPoses(height);
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
