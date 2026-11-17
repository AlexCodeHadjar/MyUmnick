/** Разделы фраз поглаживания (BEHAVIOR §7). */
export interface PetPhrases {
  /** Первое касание серии. */
  first: readonly string[];
  /** 3-й клик серии. */
  more: readonly string[];
  /** 6-й. */
  lots: readonly string[];
  /** 10-й: «перегрелся». */
  overload: readonly string[];
  /** 15-й. */
  max: readonly string[];
  /** Гладят спящего или лежащего. */
  sleepy: readonly string[];
  morning: readonly string[];
  night: readonly string[];
  /** Гладят во время радио. */
  singing: readonly string[];
  /** Гладят вскоре после тряски. */
  held: readonly string[];
  /** Гладят вскоре после долгого отсутствия пользователя. */
  comeback: readonly string[];
}

/** Фразы «смотрим вместе» (BEHAVIOR §11.2): универсальные, к любому фильму. */
export interface WatchPhrases {
  start: readonly string[];
  /** Редкие тихие реплики во время просмотра. */
  during: readonly string[];
  /** Видео встало на паузу. */
  pause: readonly string[];
  /** Продолжили после паузы. */
  resume: readonly string[];
  end: readonly string[];
}
