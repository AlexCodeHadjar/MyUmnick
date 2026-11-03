/**
 * Жест по смыслу фразы (S-18.4): качание головы по одной оси. Процедурный, как кивок: работает у
 * любой модели со стандартными параметрами головы, а размах и темп — в `mapping.json` (ADR-0011).
 */

export type HeadAxis = "pitch" | "yaw" | "roll";

export interface GestureSpec {
  axis: HeadAxis;
  /** Размах, градусы параметра головы; знак — направление. */
  degrees: number;
  ms: number;
  /** Сколько полуволн качания: 1 — наклон и обратно, 4 — покачать из стороны в сторону. */
  waves: number;
}

/** Добавка к углу головы через `elapsedMs`; огибающая возвращает голову на место к концу жеста. */
export function gestureAngle(spec: GestureSpec, elapsedMs: number): number {
  if (elapsedMs < 0 || elapsedMs >= spec.ms) {
    return 0;
  }
  const t = elapsedMs / spec.ms;
  return spec.degrees * Math.sin(Math.PI * spec.waves * t) * Math.sin(Math.PI * t);
}
