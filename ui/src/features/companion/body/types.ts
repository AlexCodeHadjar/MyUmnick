/** Типы тела спутника: фазы, музыка, эффекты и снимок тела для отрисовки. */
import type { Pose } from "../space";

export type Phase =
  | "hidden"
  | "rest"
  | "walk"
  | "jump"
  | "fall"
  | "held"
  | "bolt"
  | "portal_out"
  | "portal_in"
  /** Лезет по боку окна вверх (BEHAVIOR §9). */
  | "climb";

/** Радио (BEHAVIOR §8): играет — поёт стоя и не гуляет; пауза — слушает в наушниках. */
export type Music = "off" | "playing" | "paused";

export type Effect =
  | { kind: "bolt"; from: [number, number]; to: [number, number]; t: number }
  | { kind: "portal"; x: number; y: number; t: number; opening: boolean }
  | { kind: "sparks"; x: number; y: number; t: number }
  /** Сердечки над головой: погладили. */
  | { kind: "hearts"; x: number; y: number; t: number }
  /** Кольцо «закрепится здесь» при перетаскивании и прицеливании; рисуется кадр, не хранится. */
  | { kind: "mark"; x: number; y: number; t: number }
  /** Зёрнышко попкорна вылетает из ведёрка: «смотрим вместе». */
  | { kind: "popcorn"; x: number; y: number; t: number };

export interface Body {
  phase: Phase;
  x: number;
  y: number;
  pose: Pose;
  facing: 1 | -1;
  /** 0…1: портал «вытягивает» персонажа из точки и втягивает обратно. */
  scale: number;
  /** 1 → 0 после поглаживания: зажмуренные глаза, подскок. */
  petting: number;
  effects: Effect[];
}
