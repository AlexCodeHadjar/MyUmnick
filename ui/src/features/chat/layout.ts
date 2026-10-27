/**
 * Окно виртуализированного списка: в DOM — только видимые сообщения и запас вокруг, остальное
 * занимает место высотой (T-16). Высоты разные и меряются после отрисовки; ещё не измеренным
 * сообщениям даётся оценка — когда приходит замер, раскладка уточняется.
 */

/** Оценка высоты не измеренного сообщения, px: реплика в 2–3 строки с отступами. */
export const ESTIMATED_HEIGHT = 72;
/** Запас над и под экраном, px: быстрая прокрутка не показывает пустоту до догрузки. */
export const OVERSCAN_PX = 600;
/** Насколько можно не докрутить до низа, чтобы список всё ещё «прилипал» к новым сообщениям. */
export const STICK_TOLERANCE_PX = 24;

export interface Viewport {
  scrollTop: number;
  height: number;
}

export interface Placed<T> {
  item: T;
  top: number;
}

export interface ListWindow<T> {
  placed: Placed<T>[];
  totalHeight: number;
}

/** Начала элементов (`offsets[i]`) и полная высота; O(n) — для тысяч сообщений это микросекунды. */
function offsetsOf<T>(items: readonly T[], heightOf: (item: T) => number): number[] {
  const offsets = new Array<number>(items.length + 1);
  offsets[0] = 0;
  let sum = 0;
  items.forEach((item, i) => {
    sum += heightOf(item);
    offsets[i + 1] = sum;
  });
  return offsets;
}

/** Первый элемент, нижний край которого ниже `y` (двоичный поиск по началам). */
function firstEndingBelow(offsets: readonly number[], y: number): number {
  let low = 0;
  let high = offsets.length - 1;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if ((offsets[mid + 1] ?? Infinity) > y) {
      high = mid;
    } else {
      low = mid + 1;
    }
  }
  return low;
}

export function computeWindow<T>(
  items: readonly T[],
  heightOf: (item: T) => number,
  viewport: Viewport,
): ListWindow<T> {
  const offsets = offsetsOf(items, heightOf);
  const bottom = viewport.scrollTop + viewport.height + OVERSCAN_PX;
  const placed: Placed<T>[] = [];
  for (let i = firstEndingBelow(offsets, viewport.scrollTop - OVERSCAN_PX); i < items.length; i++) {
    const top = offsets[i] ?? 0;
    const item = items[i];
    if (top >= bottom || item === undefined) {
      break;
    }
    placed.push({ item, top });
  }
  return { placed, totalHeight: offsets[items.length] ?? 0 };
}

/** Пользователь внизу списка — новые сообщения прокручивают к себе; ушёл читать выше — нет. */
export function isAtBottom(viewport: Viewport, totalHeight: number): boolean {
  return totalHeight - (viewport.scrollTop + viewport.height) <= STICK_TOLERANCE_PX;
}
