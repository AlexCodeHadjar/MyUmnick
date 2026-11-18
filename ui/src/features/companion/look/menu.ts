/**
 * Где открыть меню спутника: у курсора, но целиком на экране (просьба пользователя 2026-11-18: у нижнего
 * края меню уходило за экран). Не влезает вниз — открывается вверх от курсора, вправо — влево от него.
 */
const MARGIN = 8;

export interface MenuPlace {
  x: number;
  y: number;
}

/** Одна ось: от курсора вперёд, иначе назад, иначе прижать к краю. */
function axis(at: number, size: number, view: number): number {
  if (at + size + MARGIN <= view) return at;
  if (at - size >= MARGIN) return at - size;
  return Math.max(MARGIN, view - size - MARGIN);
}

/** Левый верхний угол меню размера `size` для щелчка в `at` на экране `view`. */
export function placeMenu(
  at: MenuPlace,
  size: { w: number; h: number },
  view: { w: number; h: number },
): MenuPlace {
  return { x: axis(at.x, size.w, view.w), y: axis(at.y, size.h, view.h) };
}
