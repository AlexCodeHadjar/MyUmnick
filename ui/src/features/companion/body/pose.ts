/**
 * Какую позу показать (чистая функция, SOLID: одна ответственность): по фазе движения, месту, эмоции,
 * режиму (видео, радио), поглаживанию и простою. Тело (`Brain`) только собирает своё состояние.
 */
import type { Pose } from "../space";
import type { Music, Phase } from "./types";

export interface PoseState {
  /** Закреплённая поза (тычет, висит по Ctrl). */
  pinned: Pose | null;
  phase: Phase;
  /** Поза места, где стоит, или `null`. */
  spot: Pose | null;
  /** Короткая поза-эмоция (машет, кружится, зевает) или `null`. */
  emote: Pose | null;
  watching: boolean;
  music: Music;
  petting: boolean;
  /** Секунд без дела. */
  idle: number;
  layAfter: number;
  sleepAfter: number;
}

/** Поза в движении или `null`, если стоит на месте. */
function moving(phase: Phase): Pose | null {
  if (phase === "held") return "held";
  if (phase === "walk") return "walk";
  if (phase === "climb") return "climb";
  if (phase === "jump" || phase === "fall" || phase.startsWith("portal")) return "float";
  return null;
}

/** Режимы на месте: смотрит видео, радио, гладят. */
function mode(state: PoseState, pose: Pose): Pose | null {
  if (state.watching && pose === "sit_corner") return "watch";
  // Гладят стоящего — жмурится (`purr`, FRAMES-6); нет кадров — «довольный» `pet` или закрытые глаза.
  if (state.petting && pose === "stand") return "purr";
  return null;
}

/** Долгий простой: сначала лёг, потом уснул. */
function drowsy(state: PoseState, pose: Pose): Pose | null {
  const sits = pose === "sit_edge" || pose === "stand";
  if (state.idle > state.sleepAfter && (sits || pose === "sit_corner")) return "sleep";
  if (state.idle > state.layAfter && sits) return "laydown";
  return null;
}

export function poseOf(state: PoseState): Pose {
  if (state.music !== "off") return "jukebox";
  if (state.pinned !== null) return state.pinned;
  const motion = moving(state.phase);
  if (motion !== null) return motion;
  const pose = state.spot ?? "float";
  if (state.emote !== null) return state.emote;
  return mode(state, pose) ?? drowsy(state, pose) ?? pose;
}
