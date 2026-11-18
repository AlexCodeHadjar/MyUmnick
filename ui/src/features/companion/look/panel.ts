/**
 * Табло музыкального ящика (FRAMES-3 §1): название песни или станции поверх пустого прямоугольника
 * кадра `jukebox*`. Доли холста кадра — как в задании для генерации; длинное — бегущей строкой.
 */
import type { Rect } from "../space";

/** Табло в долях кадра — измерено по сгенерированным кадрам `frames-4` (2026-11-18), с отступом внутрь. */
export const PANEL = { x0: 0.285, x1: 0.712, y0: 0.737, y1: 0.797 } as const;
const SCROLL_PX_S = 28;

/** Прямоугольник табло на экране по рамке нарисованного кадра. */
export function panelRect(frame: Rect): Rect {
  return {
    x: frame.x + frame.w * PANEL.x0,
    y: frame.y + frame.h * PANEL.y0,
    w: frame.w * (PANEL.x1 - PANEL.x0),
    h: frame.h * (PANEL.y1 - PANEL.y0),
  };
}

/** Написать `text` на табло; не влезает — медленно бежит по кругу (`time` — секунды). */
export function drawPanel(
  ctx: CanvasRenderingContext2D,
  rect: Rect,
  text: string,
  time: number,
): void {
  if (text === "" || rect.w < 10) return;
  ctx.save();
  ctx.beginPath();
  ctx.rect(rect.x, rect.y, rect.w, rect.h);
  ctx.clip();
  ctx.font = `600 ${String(Math.max(8, rect.h * 0.62))}px system-ui, sans-serif`;
  ctx.fillStyle = "#7ff3ff";
  ctx.textBaseline = "middle";
  ctx.shadowColor = "#3be3ff";
  ctx.shadowBlur = 6;
  const width = ctx.measureText(text).width;
  const y = rect.y + rect.h / 2;
  if (width <= rect.w - 6) {
    ctx.textAlign = "center";
    ctx.fillText(text, rect.x + rect.w / 2, y);
  } else {
    const loop = width + rect.w * 0.5;
    const shift = (time * SCROLL_PX_S) % loop;
    ctx.textAlign = "left";
    ctx.fillText(text, rect.x + rect.w - shift, y);
    ctx.fillText(text, rect.x + rect.w - shift + loop, y);
  }
  ctx.restore();
}
