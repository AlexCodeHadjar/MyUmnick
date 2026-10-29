/**
 * Кивок «услышала» в начале хода (S-8.2): наклон головы вниз и обратно по одной полуволне
 * синуса. Процедурный — работает у любой модели со стандартным параметром наклона головы, без
 * моушена в её файлах.
 */

/** Длительность кивка, мс: короче — дёрганье, дольше — поклон. */
export const NOD_MS = 450;
/** Глубина кивка, градусы параметра `ParamAngleY` (диапазон модели обычно ±30). */
export const NOD_DEGREES = 9;

/** Добавка к наклону головы через `elapsedMs` после начала кивка; вне кивка — 0. */
export function nodAngle(elapsedMs: number): number {
  if (elapsedMs < 0 || elapsedMs >= NOD_MS) {
    return 0;
  }
  return -NOD_DEGREES * Math.sin((Math.PI * elapsedMs) / NOD_MS);
}
