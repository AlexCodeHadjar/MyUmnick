/**
 * Контракт рендера аватара: остальное UI знает только его — смена Live2D на VRM или на другой
 * движок Live2D не трогает чат и звук (ADR-0011). Реализации: `live2d/` (S-6.2), `vrm/` (позже).
 *
 * Цикл кадров — снаружи, вне реактивности Svelte (R-66): владелец зовёт `update()` из своего
 * `requestAnimationFrame` и ставит паузу, когда окно свёрнуто. Методы-сеттеры (`setMouth`,
 * `lookAt` и др.) только запоминают цель — применяется она в ближайшем `update()`, поэтому их
 * можно звать чаще кадра без лишней работы.
 */
import type { Emotion, Gesture } from "../../core";

/** Что загрузить: файлы модели в `ui/public/avatars/<имя>/` (ADR-0011). */
export interface AvatarSource {
  /** URL манифеста модели, например `/avatars/hiyori/hiyori.model3.json`. */
  modelUrl: string;
  /** URL `mapping.json` — эмоции и реакции модели (S-6.3). */
  mappingUrl: string;
}

/**
 * Реакция на ход разговора, не зависящая от текста: «слушаю» (пользователь печатает),
 * «думаю» (реплика ушла — в том же кадре, T-17, NFR-03 ≤ 50 мс), «покой».
 */
export type AvatarReaction = "idle" | "listening" | "thinking";

/** Размер области сцены в CSS-пикселях; рендер сам учитывает devicePixelRatio. */
export interface StageSize {
  width: number;
  height: number;
}

export interface AvatarRenderer {
  /**
   * Загружает модель и её маппинг; повторный вызов заменяет модель. Отказ — `Error` с текстом
   * для пользователя (нет Cubism Core, нет файлов модели, битый маппинг).
   */
  load(source: AvatarSource): Promise<void>;

  /**
   * Выражение по эмоции из ответа LLM; `intensity` 0…1 — сила при затухании (`mood.ts`). Зовётся
   * каждый кадр: без изменений — ничего не делает.
   */
  setEmotion(emotion: Emotion, intensity: number): void;

  /** Кивок «услышала» (начало хода); повторный вызов начинает кивок заново. */
  nod(): void;

  /** Жест по смыслу фразы; у модели такого жеста нет — ничего не происходит. */
  gesture(gesture: Gesture): void;

  /** Витюбер говорит: моргает чаще, как человек в разговоре. */
  setSpeaking(speaking: boolean): void;

  /** Открытие рта 0…1 из громкости звука (липсинк, ADR-0003); значения вне диапазона обрезаются. */
  setMouth(openness: number): void;

  /** Точка взгляда в координатах сцены, -1…1 по каждой оси (0, 0 — центр, y вверх). */
  lookAt(x: number, y: number): void;

  /** Реакция на событие хода. */
  react(reaction: AvatarReaction): void;

  /** Шаг анимации и отрисовка; `deltaMs` — время с прошлого кадра. */
  update(deltaMs: number): void;

  /** Над моделью ли точка сцены, CSS-пиксели: окно поверх стола пропускает клики вокруг неё. */
  contains(x: number, y: number): boolean;

  /** Новый размер сцены (перетаскивание разделителя, окно): модель вписывается заново. */
  resize(size: StageSize): void;

  /** Освобождает GPU-ресурсы и холст; после вызова объект не используется. */
  dispose(): void;
}
