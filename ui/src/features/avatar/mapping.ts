/**
 * `mapping.json` модели: всё модель-зависимое — какие выражения есть, какая эмоция какое
 * выражение включает, чем модель реагирует на ход и как она стоит в кадре. Замена модели —
 * замена файлов и этого маппинга, без кода (критерий Этапа 6).
 */
import type { Emotion, Gesture } from "../../core";
import type { AvatarReaction } from "./AvatarRenderer";
import type { GestureSpec, HeadAxis } from "./gesture";

export const MAPPING_VERSION = 1;

export interface MotionRef {
  group: string;
  index: number;
}

export interface ReactionSpec {
  /** Выражение на время реакции; без него остаётся выражение текущей эмоции. */
  expression?: string;
  /** Моушен один раз при входе в реакцию. */
  motion?: MotionRef;
}

/** Кадр поверх «вписать целиком»: масштаб и сдвиг центра в долях сцены (y — вниз). */
export interface FrameSpec {
  zoom: number;
  offsetX: number;
  offsetY: number;
}

export interface AvatarMapping {
  /** Имя выражения → файл `.exp3.json` относительно каталога модели. */
  expressions: Record<string, string>;
  emotions: Partial<Record<Emotion, string>>;
  reactions: Partial<Record<AvatarReaction, ReactionSpec>>;
  frame: FrameSpec;
  /** Жесты этой модели; жеста нет в списке — он пропускается, ответ идёт как шёл. */
  gestures: Partial<Record<Gesture, GestureSpec>>;
}

/** Маппинга нет — модель как есть: без выражений и реакций, кадр «вписать целиком». */
export const DEFAULT_MAPPING: AvatarMapping = {
  expressions: {},
  emotions: {},
  reactions: {},
  frame: { zoom: 1, offsetX: 0, offsetY: 0 },
  gestures: {},
};

/** Ключи сверяются с типами протокола и контракта: новый член — ошибка компиляции здесь. */
const EMOTIONS = {
  neutral: true,
  happy: true,
  sad: true,
  angry: true,
  surprised: true,
  embarrassed: true,
  thinking: true,
} satisfies Record<Emotion, true>;
const REACTIONS = { idle: true, listening: true, thinking: true } satisfies Record<
  AvatarReaction,
  true
>;

const GESTURES = { nod: true, shake: true, tilt: true, startle: true } satisfies Record<
  Gesture,
  true
>;
const AXES = { pitch: true, yaw: true, roll: true } satisfies Record<HeadAxis, true>;

export class MappingError extends Error {
  override name = "MappingError";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isEmotion(key: string): key is Emotion {
  return Object.hasOwn(EMOTIONS, key);
}

function isReaction(key: string): key is AvatarReaction {
  return Object.hasOwn(REACTIONS, key);
}

function isGesture(key: string): key is Gesture {
  return Object.hasOwn(GESTURES, key);
}

function isAxis(value: unknown): value is HeadAxis {
  return typeof value === "string" && Object.hasOwn(AXES, value);
}

function fail(path: string, problem: string): never {
  throw new MappingError(`mapping.json: ${path} — ${problem}`);
}

function record(value: unknown, path: string): Record<string, unknown> {
  return isRecord(value) ? value : fail(path, "ожидается объект");
}

function finite(value: unknown, path: string, min: number, max: number): number {
  return typeof value === "number" && Number.isFinite(value) && value >= min && value <= max
    ? value
    : fail(path, `ожидается число ${String(min)}…${String(max)}`);
}

function parseExpressions(raw: unknown): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [name, file] of Object.entries(record(raw ?? {}, "expressions"))) {
    result[name] =
      typeof file === "string" && file.endsWith(".exp3.json")
        ? file
        : fail(`expressions.${name}`, "ожидается путь к .exp3.json");
  }
  return result;
}

function expressionName(value: unknown, path: string, known: Record<string, string>): string {
  return typeof value === "string" && Object.hasOwn(known, value)
    ? value
    : fail(path, "нет такого выражения в expressions");
}

function parseEmotions(raw: unknown, known: Record<string, string>): AvatarMapping["emotions"] {
  const result: AvatarMapping["emotions"] = {};
  for (const [key, value] of Object.entries(record(raw ?? {}, "emotions"))) {
    if (!isEmotion(key)) {
      fail(`emotions.${key}`, `неизвестная эмоция; есть: ${Object.keys(EMOTIONS).join(", ")}`);
    }
    result[key] = expressionName(value, `emotions.${key}`, known);
  }
  return result;
}

function parseMotion(raw: unknown, path: string): MotionRef {
  const motion = record(raw, path);
  const group =
    typeof motion.group === "string" ? motion.group : fail(`${path}.group`, "ожидается строка");
  const index = finite(motion.index, `${path}.index`, 0, 999);
  return Number.isInteger(index) ? { group, index } : fail(`${path}.index`, "ожидается целое");
}

function parseReaction(raw: unknown, path: string, known: Record<string, string>): ReactionSpec {
  const spec = record(raw, path);
  const result: ReactionSpec = {};
  if (spec.expression !== undefined) {
    result.expression = expressionName(spec.expression, `${path}.expression`, known);
  }
  if (spec.motion !== undefined) {
    result.motion = parseMotion(spec.motion, `${path}.motion`);
  }
  return result;
}

function parseReactions(raw: unknown, known: Record<string, string>): AvatarMapping["reactions"] {
  const result: AvatarMapping["reactions"] = {};
  for (const [key, value] of Object.entries(record(raw ?? {}, "reactions"))) {
    if (!isReaction(key)) {
      fail(`reactions.${key}`, `неизвестная реакция; есть: ${Object.keys(REACTIONS).join(", ")}`);
    }
    result[key] = parseReaction(value, `reactions.${key}`, known);
  }
  return result;
}

function parseFrame(raw: unknown): FrameSpec {
  const frame = record(raw ?? {}, "frame");
  return {
    zoom: finite(frame.zoom ?? 1, "frame.zoom", 0.1, 10),
    offsetX: finite(frame.offsetX ?? 0, "frame.offsetX", -1, 1),
    offsetY: finite(frame.offsetY ?? 0, "frame.offsetY", -1, 1),
  };
}

function parseGesture(raw: unknown, path: string): GestureSpec {
  const spec = record(raw, path);
  return {
    axis: isAxis(spec.axis) ? spec.axis : fail(`${path}.axis`, "ожидается pitch, yaw или roll"),
    degrees: finite(spec.degrees, `${path}.degrees`, -30, 30),
    ms: finite(spec.ms, `${path}.ms`, 100, 3000),
    waves: finite(spec.waves, `${path}.waves`, 1, 8),
  };
}

function parseGestures(raw: unknown): AvatarMapping["gestures"] {
  const result: AvatarMapping["gestures"] = {};
  for (const [key, value] of Object.entries(record(raw ?? {}, "gestures"))) {
    if (!isGesture(key)) {
      fail(`gestures.${key}`, `неизвестный жест; есть: ${Object.keys(GESTURES).join(", ")}`);
    }
    result[key] = parseGesture(value, `gestures.${key}`);
  }
  return result;
}

/** JSON маппинга → проверенный маппинг; ошибка называет поле и что с ним не так. */
export function parseMapping(raw: unknown): AvatarMapping {
  const root = record(raw, "корень");
  if (root.version !== MAPPING_VERSION) {
    fail("version", `ожидается ${String(MAPPING_VERSION)}`);
  }
  const expressions = parseExpressions(root.expressions);
  return {
    expressions,
    emotions: parseEmotions(root.emotions, expressions),
    reactions: parseReactions(root.reactions, expressions),
    frame: parseFrame(root.frame),
    gestures: parseGestures(root.gestures),
  };
}

/**
 * Какое выражение должно быть на лице: реакция (например, «думаю» до первого токена) важнее
 * эмоции ответа; null — у модели нет выражения ни для того, ни для другого.
 */
export function expressionFor(
  mapping: AvatarMapping,
  emotion: Emotion,
  reaction: AvatarReaction,
): string | null {
  return mapping.reactions[reaction]?.expression ?? mapping.emotions[emotion] ?? null;
}
