/** Курсор → взгляд персонажа: общий для всех видов показа (сфера, окно персонажа). */

export interface StageRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * -1…1 по осям, y вверх (как `AvatarRenderer.lookAt`). За пределами сцены значение обрезается:
 * персонаж смотрит «в край», а не выворачивается.
 */
export function gazeAt(pointerX: number, pointerY: number, stage: StageRect): [number, number] {
  const clamp = (value: number): number => Math.max(-1, Math.min(1, value));
  const halfW = stage.width / 2 || 1;
  const halfH = stage.height / 2 || 1;
  const x = (pointerX - (stage.left + halfW)) / halfW;
  const y = (stage.top + halfH - pointerY) / halfH;
  return [clamp(x), clamp(y)];
}
