/**
 * Сводка замеров стадии для панели метрик (FR-15): последний, p50, p95 и сверка с бюджетом
 * из `docs/requirements.md` / `docs/performance.md`.
 */
import { FIRST_AUDIO_SPAN, FIRST_CHAR_SPAN } from "../../core";

export interface Summary {
  name: string;
  last: number;
  p50: number;
  p95: number;
  count: number;
  /** Бюджет p50, мс; нет — стадия без нормы. */
  budget: number | null;
}

/**
 * Бюджеты p50, мс. TTFT — NFR-01 (≤ 250); UI-замер — TTFT + 20 мс (критерий Этапа 5); звук от
 * Enter — NFR-02 (TTFA ≤ 800). Новые стадии получают норму вместе со своим замером.
 */
const BUDGETS: Partial<Record<string, number>> = {
  "llm.first_token": 250,
  [FIRST_CHAR_SPAN]: 270,
  [FIRST_AUDIO_SPAN]: 800,
};

/** Перцентиль по ближайшему рангу: значение из выборки, без интерполяции — честно для малых n. */
export function percentile(sorted: readonly number[], p: number): number {
  if (sorted.length === 0) {
    return Number.NaN;
  }
  const rank = Math.ceil((p / 100) * sorted.length);
  return sorted[Math.min(sorted.length, Math.max(1, rank)) - 1] ?? Number.NaN;
}

export function summarize(name: string, values: readonly number[]): Summary {
  const sorted = [...values].sort((a, b) => a - b);
  return {
    name,
    last: values.at(-1) ?? Number.NaN,
    p50: percentile(sorted, 50),
    p95: percentile(sorted, 95),
    count: values.length,
    budget: BUDGETS[name] ?? null,
  };
}

/** Строки панели: сначала стадии с бюджетом (главное), затем остальные по имени. */
export function summarizeAll(spans: Readonly<Record<string, readonly number[]>>): Summary[] {
  return Object.entries(spans)
    .map(([name, values]) => summarize(name, values))
    .sort(
      (a, b) =>
        Number(b.budget !== null) - Number(a.budget !== null) || a.name.localeCompare(b.name),
    );
}

export function overBudget(summary: Summary): boolean {
  return summary.budget !== null && summary.p50 > summary.budget;
}
