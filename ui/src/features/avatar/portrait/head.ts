/**
 * Кадр «мордашки» встроенного персонажа (2026-11-17, кадры `head_*` из docs/character/FRAMES.md): рот по
 * громкости в три уровня, моргание с полуприкрытыми глазами, лицо по эмоции ответа. Чистая функция —
 * проверяется тестами.
 */
import type { Emotion } from "../../../core";

const PACK = "/characters/default";
/** Эмоции, для которых есть свой кадр; «смущение» ближе всего к радости. */
const FACES: Partial<Record<Emotion, string>> = {
  happy: "head_happy",
  embarrassed: "head_happy",
  sad: "head_sad",
  angry: "head_angry",
  surprised: "head_surprised",
  thinking: "head_thinking",
};
/** Слабая эмоция — обычное лицо: кадр не скачет от шума. */
const FACE_FROM = 0.35;

export const HEAD_FRAMES: readonly string[] = [
  "head",
  "head_blink",
  "head_blink_1",
  "head_talk_1",
  "head_talk_2",
  "head_talk_3",
  ...new Set(Object.values(FACES)),
].map((name) => `${PACK}/${name}.webp`);

export interface HeadState {
  speaking: boolean;
  /** Громкость 0…1. */
  mouth: number;
  /** Доля моргания 0…1 или `null`. */
  blink: number | null;
  emotion: Emotion;
  intensity: number;
}

export function headFrame(state: HeadState): string {
  const name = headName(state);
  return `${PACK}/${name}.webp`;
}

function headName(state: HeadState): string {
  if (state.speaking && state.mouth > 0.08) {
    return `head_talk_${String(Math.min(3, Math.floor(state.mouth * 3) + 1))}`;
  }
  if (state.blink !== null) {
    return state.blink < 0.3 || state.blink > 0.7 ? "head_blink_1" : "head_blink";
  }
  return (state.intensity >= FACE_FROM ? FACES[state.emotion] : undefined) ?? "head";
}
