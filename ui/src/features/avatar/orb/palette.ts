/**
 * Цвет сферы (Этап 22): переливается по кругу оттенков, эмоция ответа тянет оттенок к своему.
 * Чистые функции — проверяются тестами, в кадре вызываются без выделения памяти.
 */
import type { Emotion } from "../../../core";

/** Оттенок (0…360) эмоции; нейтральная — голубой «Джарвиса». */
export const EMOTION_HUE: Record<Emotion, number> = {
  neutral: 195,
  happy: 165,
  sad: 225,
  angry: 355,
  surprised: 45,
  embarrassed: 330,
  thinking: 265,
};

/** Переливание: медленный дрейф ±25° вокруг оттенка эмоции. */
export function shimmerHue(base: number, timeS: number): number {
  return (base + 25 * Math.sin(timeS * 0.35) + 360) % 360;
}

/** Плавный переход оттенка по короткой дуге круга; `t` 0…1. */
export function mixHue(from: number, to: number, t: number): number {
  const delta = ((to - from + 540) % 360) - 180;
  return (from + delta * Math.min(1, Math.max(0, t)) + 360) % 360;
}

/** Искрение точки: у каждой своя фаза, яркость 0.55…1. */
export function sparkle(index: number, timeS: number): number {
  return 0.775 + 0.225 * Math.sin(timeS * 2.3 + index * 2.39);
}
