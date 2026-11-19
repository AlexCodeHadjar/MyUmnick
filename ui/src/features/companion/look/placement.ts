/**
 * Где рисовать кадр позы относительно точки опоры: размер и сдвиг центра. Кадр выше обычного (место над
 * головой — штамп, рожки; FRAMES-6) рисуется в том же масштабе, а точка опоры отсчитывается снизу.
 */
export interface Placement {
  /** Размер кадра при росте `height` (без масштаба портала). */
  w: number;
  h: number;
  /** Сдвиг центра кадра от точки опоры. */
  cx: number;
  cy: number;
}

/**
 * `tall` — во сколько раз кадр выше обычного (1 — обычный); `ANCHORS` заданы в долях обычного кадра.
 * Лишнее место у высокого кадра — со стороны, дальней от опоры: у стоящих (опора внизу) — сверху (штамп над
 * головой, рожки), у подвешенных за верх (держат за капюшон, висит) — снизу (свисающие ноги).
 */
export function placement(
  aspect: number,
  anchor: readonly [number, number],
  height: number,
  tall: number,
): Placement {
  const h = height * tall;
  const w = aspect * h;
  const [ax, ay] = anchor;
  const anchorY = growsDown(ay) ? ay / tall : (ay + tall - 1) / tall;
  return { w, h, cx: (0.5 - ax) * w, cy: (0.5 - anchorY) * h };
}

/** Опора в верхней половине кадра — лишнее место у высокого кадра снизу (подгонка FRAMES/этапов — так же). */
export function growsDown(anchorY: number): boolean {
  return anchorY < 0.5;
}

/** Во сколько раз кадр выше обычного; `unit` — высота обычного кадра (рост × CANVAS_RATIO). */
export function tallness(image: { height: number }, unit: number | null): number {
  if (unit === null || unit <= 0) return 1;
  return Math.max(1, image.height / unit);
}
