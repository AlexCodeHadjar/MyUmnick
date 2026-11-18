/**
 * «Покажи на экране» (COMPANION.md, этап 5): ассистент в ответе называет элемент в кавычках — «Сохранить»,
 * "Settings", — а спутник находит видимую кнопку, ссылку или вкладку с таким названием и показывает на неё
 * пальцем. Без доработки ядра: только текст ответа и видимые элементы (UI Automation). Чистые функции.
 */
import type { Target } from "./remarks";

/** Названия в кавычках «…», "…", “…” длиной 2–40 знаков. */
export function quotedNames(text: string): string[] {
  const found = [...text.matchAll(/[«"“]([^«»"“”\n]{2,40})[»"”]/g)].map((m) => (m[1] ?? "").trim());
  return [...new Set(found.filter((name) => name.length >= 2))];
}

/** Видимый элемент, название которого совпадает с одним из названий (без регистра): точное — лучше. */
export function findTarget(targets: readonly Target[], names: readonly string[]): Target | null {
  const lower = names.map((name) => name.toLowerCase());
  const exact = targets.find((one) => lower.includes(one.name.toLowerCase()));
  if (exact !== undefined) return exact;
  return (
    targets.find((one) => {
      const name = one.name.toLowerCase();
      return lower.some((want) => want.length >= 4 && (name.includes(want) || want.includes(name)));
    }) ?? null
  );
}
