/**
 * Действия спутника и их оценки (MIND §4). Здесь только «насколько хочется» — исполняет
 * `Companion.svelte`. Числа настраиваются здесь.
 */
import type { Activity } from "./arbiter";
import { need } from "./curves";

export type ActivityId =
  "idle" | "sing" | "watch" | "hush" | "follow" | "chat" | "poke" | "hop" | "wander" | "play";

/** Что арбитр знает о мире в момент оценки (сглаженное, MIND §3.1–3.3). */
export interface MindContext {
  /** Стоит на опоре, его не держат, тело не занято рефлексом. */
  resting: boolean;
  /** Ассистент говорит или персонажа позвали. */
  listening: boolean;
  singing: boolean;
  video: boolean;
  /** Полный экран без видео. */
  hush: boolean;
  desktop: boolean;
  behavior: "follow" | "stay" | "wander";
  energy: number;
  social: number;
  curiosity: number;
  restless: number;
  /** Стимул «новая программа» 0…1. */
  focus: number;
  /** Можно сказать фразу «сам по себе» (жетон голоса). */
  canChat: boolean;
  /** «Спокойнее»: не тычет и не прыгает по значкам. */
  calm: boolean;
  /** Стимул «с ним играют» 0…1. */
  play: number;
}

type Spec = Omit<Activity<MindContext>, "id"> & { id: ActivityId };

/**
 * Выходки — только стоя на месте и пока никто не говорит. «Слушает» — не действие, а запрет на выходки:
 * режим (видео, радио) речь ассистента не прерывает.
 */
function free(context: MindContext): number {
  return context.resting && !context.listening ? 1 : 0;
}

export const ACTIVITIES: readonly Spec[] = [
  {
    id: "idle",
    band: 0,
    minS: 0,
    cooldownS: 0,
    boredom: 1 / 150,
    oneShot: false,
    score: () => 0.2,
  },
  {
    id: "sing",
    band: 2,
    minS: 5,
    cooldownS: 0,
    boredom: 0,
    oneShot: false,
    score: (c) => (c.singing ? 0.95 : 0),
  },
  {
    id: "watch",
    band: 2,
    minS: 10,
    cooldownS: 5,
    boredom: 0,
    oneShot: false,
    score: (c) => (c.video ? 0.9 : 0),
  },
  {
    id: "hush",
    band: 2,
    minS: 10,
    cooldownS: 5,
    boredom: 0,
    oneShot: false,
    score: (c) => (c.hush ? 0.85 : 0),
  },
  {
    id: "follow",
    band: 1,
    minS: 2,
    cooldownS: 3,
    boredom: 0,
    oneShot: true,
    score: (c) => (c.behavior === "follow" ? free(c) * c.focus * 0.8 : 0),
  },
  {
    id: "chat",
    band: 1,
    minS: 6,
    cooldownS: 60,
    boredom: 0,
    oneShot: true,
    score: (c) => (c.canChat ? free(c) * need(c.social) * (0.5 + c.focus * 0.5) * 0.75 : 0),
  },
  {
    id: "poke",
    band: 1,
    minS: 6,
    cooldownS: 180,
    boredom: 0,
    oneShot: true,
    score: (c) => (c.desktop || c.calm ? 0 : free(c) * need(c.curiosity) * 0.65),
  },
  {
    id: "hop",
    band: 1,
    minS: 3,
    cooldownS: 20,
    boredom: 0,
    oneShot: true,
    score: (c) =>
      c.desktop && !c.calm && c.behavior !== "stay" ? free(c) * need(c.curiosity) * 0.7 : 0,
  },
  {
    id: "wander",
    band: 1,
    minS: 3,
    cooldownS: 12,
    boredom: 0,
    oneShot: true,
    score: (c) => (c.behavior === "stay" ? 0 : free(c) * need(c.restless) * (0.3 + c.energy * 0.5)),
  },
  {
    id: "play",
    band: 1,
    minS: 3,
    cooldownS: 4,
    boredom: 0,
    oneShot: true,
    score: (c) => free(c) * c.play * 0.95,
  },
];
