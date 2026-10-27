/**
 * Ширина панели чата (FR-01): доля окна, ограниченная минимумами обеих панелей; запоминается в
 * localStorage — в Tauri он живёт в каталоге данных приложения и переживает перезапуск.
 */

/** Чат 2 : сцена 3 — как в каркасе S-5.1. */
export const DEFAULT_RATIO = 0.4;
/** Уже — чат не читается, сцена теряет модель. */
export const MIN_CHAT_PX = 320;
export const MIN_STAGE_PX = 320;
/** Шаг стрелками на разделителе — доступность с клавиатуры. */
export const KEYBOARD_STEP = 0.02;

const STORAGE_KEY = "vtuber.layout.chatRatio";

/** Минимальное хранилище: в тестах — Map-подобная подмена. */
export type RatioStorage = Pick<Storage, "getItem" | "setItem">;

/** Доля в пределах, при которых обе панели не уже своего минимума. */
export function clampRatio(ratio: number, totalPx: number): number {
  if (totalPx <= MIN_CHAT_PX + MIN_STAGE_PX) {
    return MIN_CHAT_PX / (MIN_CHAT_PX + MIN_STAGE_PX);
  }
  const low = MIN_CHAT_PX / totalPx;
  const high = 1 - MIN_STAGE_PX / totalPx;
  return Math.min(high, Math.max(low, ratio));
}

/** Доля по положению указателя внутри раскладки. */
export function ratioAt(pointerX: number, left: number, width: number): number {
  return width > 0 ? (pointerX - left) / width : DEFAULT_RATIO;
}

/** Сохранённая доля или умолчание; битое значение или недоступное хранилище — умолчание. */
export function loadRatio(storage: RatioStorage | undefined): number {
  try {
    const value = Number(storage?.getItem(STORAGE_KEY));
    return Number.isFinite(value) && value > 0 && value < 1 ? value : DEFAULT_RATIO;
  } catch {
    return DEFAULT_RATIO;
  }
}

/** Запомнить долю; ошибка хранилища (переполнено, запрещено) не ломает раскладку. */
export function saveRatio(storage: RatioStorage | undefined, ratio: number): void {
  try {
    storage?.setItem(STORAGE_KEY, ratio.toFixed(4));
  } catch {
    // Ширина — удобство, не данные: без хранилища просто не запомнится.
  }
}
