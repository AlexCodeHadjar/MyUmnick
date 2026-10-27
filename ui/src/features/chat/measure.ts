/**
 * Замер высоты строк списка: один общий ResizeObserver на все строки — дешевле, чем по
 * наблюдателю на каждую, и колбэк приходит пачкой раз в кадр, до отрисовки.
 */
import type { Action } from "svelte/action";

export interface MeasureTarget {
  id: number;
  /** Куда класть высоты; реактивная карта (`SvelteMap`) — раскладка пересчитается сама. */
  heights: Map<number, number>;
}

const targets = new WeakMap<Element, MeasureTarget>();
let observer: ResizeObserver | null = null;

function record(entries: ResizeObserverEntry[]): void {
  for (const entry of entries) {
    const target = targets.get(entry.target);
    const height = entry.borderBoxSize[0]?.blockSize ?? entry.contentRect.height;
    // Тот же размер не пишется: иначе каждый замер перезапускал бы раскладку впустую.
    if (target !== undefined && target.heights.get(target.id) !== height) {
      target.heights.set(target.id, height);
    }
  }
}

export const measureHeight: Action<HTMLElement, MeasureTarget> = (node, target) => {
  observer ??= new ResizeObserver(record);
  targets.set(node, target);
  observer.observe(node);
  return {
    update(next: MeasureTarget) {
      targets.set(node, next);
    },
    destroy() {
      observer?.unobserve(node);
      targets.delete(node);
    },
  };
};
