/**
 * Картина рабочего стола от оболочки (`desktop.rs`, физические пиксели экрана) → CSS-пиксели слоя спутника.
 * Слой лежит на весь основной монитор, поэтому начало координат — его левый верхний угол.
 */
export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Seat {
  id: number;
  rect: Rect;
  open: [number, number][];
}

export type Focus =
  | { kind: "window"; id: number; app: string }
  | { kind: "maximized"; app: string }
  | { kind: "desktop" }
  | { kind: "other"; app: string };

export interface World {
  monitor: Rect;
  work: Rect;
  seats: Seat[];
  focus: Focus;
  fullscreen: boolean;
}

export function rectToCss(rect: Rect, origin: Rect, scale: number): Rect {
  return {
    x: (rect.x - origin.x) / scale,
    y: (rect.y - origin.y) / scale,
    w: rect.w / scale,
    h: rect.h / scale,
  };
}

/** Вся картина в CSS-пикселях слоя. */
export function worldToCss(world: World, scale: number): World {
  const origin = world.monitor;
  return {
    ...world,
    monitor: rectToCss(world.monitor, origin, scale),
    work: rectToCss(world.work, origin, scale),
    seats: world.seats.map((seat) => ({
      id: seat.id,
      rect: rectToCss(seat.rect, origin, scale),
      open: seat.open.map(([a, b]): [number, number] => [
        (a - origin.x) / scale,
        (b - origin.x) / scale,
      ]),
    })),
  };
}
