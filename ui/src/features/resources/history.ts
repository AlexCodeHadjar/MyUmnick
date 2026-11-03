/**
 * История нагрузки для графика панели ресурсов: занятая память каждой модели по снимкам.
 * Живёт, только пока панель открыта; новая модель появляется сама, правка UI не нужна.
 */
import type { ResourcesData } from "../../core";

/** Снимок приходит раз в секунду: на графике пять минут. */
export const HISTORY_POINTS = 300;

export type LoadHistory = Map<string, number[]>;

/** Сколько МБ модель занимает в этом снимке: выгруженная и ждущая не занимают ничего. */
function usedMb(model: ResourcesData["models"][number]): number {
  return model.state === "in_use" || model.state === "idle" ? model.vram_mb : 0;
}

export function addSnapshot(history: LoadHistory, snapshot: ResourcesData): void {
  for (const model of snapshot.models) {
    const points = history.get(model.name) ?? [];
    points.push(usedMb(model));
    if (points.length > HISTORY_POINTS) {
      points.shift();
    }
    history.set(model.name, points);
  }
}

/** Точки SVG `polyline`; новые — справа, вертикальный масштаб — от `maxMb`. */
export function sparkline(
  points: readonly number[],
  maxMb: number,
  size: [number, number],
): string {
  const [width, height] = size;
  const scale = maxMb > 0 ? height / maxMb : 0;
  const start = HISTORY_POINTS - points.length;
  return points
    .map((mb, index) => {
      const x = ((start + index) / (HISTORY_POINTS - 1)) * width;
      return `${x.toFixed(1)},${(height - mb * scale).toFixed(1)}`;
    })
    .join(" ");
}

const STATE_LABELS: Record<string, string> = {
  unloaded: "выгружена",
  idle: "простаивает",
  in_use: "работает",
  waiting: "ждёт",
};

export function stateLabel(state: string): string {
  return STATE_LABELS[state] ?? state;
}
