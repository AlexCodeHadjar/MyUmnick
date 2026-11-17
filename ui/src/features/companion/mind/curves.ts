/** Кривые отклика utility AI (MIND §2, §4): вход 0…1 → оценка 0…1. */
export function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

/** Сглаженная ступень между `from` и `to`: ниже — 0, выше — 1, между — плавно. */
export function smoothstep(value: number, from: number, to: number): number {
  const t = clamp01((value - from) / (to - from));
  return t * t * (3 - 2 * t);
}

/** Потребность: до 0,4 почти не тянет, к 0,9 — тянет сильно. */
export function need(value: number): number {
  return smoothstep(value, 0.35, 0.9);
}
