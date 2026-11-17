/**
 * Эффекты спутника (Этап 23, раздел 5.4): молния, разряд по ней, искры, портал. Canvas 2D, без WebGL:
 * видеокарта отдана LLM (приоритет 1). Форма молнии — чистая функция с заданным генератором случайных
 * чисел, проверяется тестами.
 */
import type { Effect } from "../body";

export type Point = [number, number];
export type Random = () => number;

/** Генератор с зерном (mulberry32): молния не «дёргается» сильнее, чем мы просим. */
export function seeded(seed: number): Random {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Ломаная молнии смещением средней точки: `depth` уровней, отклонение — доля длины отрезка. */
export function lightning(
  from: Point,
  to: Point,
  random: Random,
  depth = 6,
  roughness = 0.22,
): Point[] {
  let points: Point[] = [from, to];
  for (let level = 0; level < depth; level += 1) {
    const next: Point[] = [];
    for (let i = 0; i < points.length - 1; i += 1) {
      const a = points[i] ?? from;
      const b = points[i + 1] ?? to;
      const length = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const offset = (random() - 0.5) * length * roughness;
      const nx = -(b[1] - a[1]) / (length || 1);
      const ny = (b[0] - a[0]) / (length || 1);
      next.push(a, [(a[0] + b[0]) / 2 + nx * offset, (a[1] + b[1]) / 2 + ny * offset]);
    }
    next.push(points.at(-1) ?? to);
    points = next;
  }
  return points;
}

/** Ответвления: короткие молнии от случайных точек ствола. */
export function branches(trunk: readonly Point[], random: Random, count = 3): Point[][] {
  const list: Point[][] = [];
  for (let i = 0; i < count; i += 1) {
    const start = trunk[Math.floor(random() * (trunk.length - 1))] ?? trunk[0] ?? [0, 0];
    const angle = random() * Math.PI * 2;
    const length = 30 + random() * 70;
    const end: Point = [start[0] + Math.cos(angle) * length, start[1] + Math.sin(angle) * length];
    list.push(lightning(start, end, random, 4, 0.3));
  }
  return list;
}

/** Точка на ломаной на доле `t` её длины — где сейчас разряд. */
export function along(points: readonly Point[], t: number): Point {
  const lengths: number[] = [];
  let total = 0;
  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i] ?? [0, 0];
    const b = points[i + 1] ?? [0, 0];
    const length = Math.hypot(b[0] - a[0], b[1] - a[1]);
    lengths.push(length);
    total += length;
  }
  let left = Math.min(1, Math.max(0, t)) * total;
  for (let i = 0; i < lengths.length; i += 1) {
    const length = lengths[i] ?? 0;
    const a = points[i] ?? [0, 0];
    const b = points[i + 1] ?? [0, 0];
    if (left <= length) {
      const s = length === 0 ? 0 : left / length;
      return [a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s];
    }
    left -= length;
  }
  return points.at(-1) ?? [0, 0];
}

function stroke(ctx: CanvasRenderingContext2D, points: readonly Point[]): void {
  ctx.beginPath();
  points.forEach(([x, y], i) => {
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

/** Молния тремя проходами: широкое свечение, мягкая линия, яркая сердцевина. */
export function drawBolt(
  ctx: CanvasRenderingContext2D,
  from: Point,
  to: Point,
  hue: number,
  seed: number,
  discharge: number | null,
): void {
  const random = seeded(seed);
  const trunk = lightning(from, to, random);
  const forks = branches(trunk, random);
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const [width, alpha] of [
    [12, 0.12],
    [5, 0.35],
    [2, 0.95],
  ] as const) {
    ctx.lineWidth = width;
    ctx.strokeStyle = `hsla(${String(hue)}, 95%, ${String(width === 2 ? 92 : 65)}%, ${String(alpha)})`;
    stroke(ctx, trunk);
    ctx.lineWidth = width * 0.5;
    forks.forEach((fork) => {
      stroke(ctx, fork);
    });
  }
  if (discharge !== null) {
    const [x, y] = along(trunk, discharge);
    const glow = ctx.createRadialGradient(x, y, 0, x, y, 26);
    glow.addColorStop(0, "rgba(255, 255, 255, 0.95)");
    glow.addColorStop(1, `hsla(${String(hue)}, 95%, 70%, 0)`);
    ctx.fillStyle = glow;
    ctx.fillRect(x - 26, y - 26, 52, 52);
  }
  ctx.restore();
}

function drawSparks(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  t: number,
  hue: number,
): void {
  const random = seeded(Math.round(x * 31 + y * 17));
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (let i = 0; i < 60; i += 1) {
    const angle = random() * Math.PI * 2;
    const speed = 60 + random() * 220;
    const px = x + Math.cos(angle) * speed * t;
    const py = y + Math.sin(angle) * speed * t + 300 * t * t;
    ctx.fillStyle = `hsla(${String(hue)}, 95%, ${String(70 + random() * 25)}%, ${String(1 - t)})`;
    ctx.fillRect(px - 1.5, py - 1.5, 3, 3);
  }
  ctx.restore();
}

/** Сердечки: поднимаются, покачиваясь, и тают (погладили). */
/** Два-три зёрнышка попкорна: подлетают дугой и падают обратно в ведёрко. */
function drawPopcorn(ctx: CanvasRenderingContext2D, x: number, y: number, t: number): void {
  const random = seeded(Math.round(x * 5 + y * 11));
  ctx.save();
  for (let i = 0; i < 3; i += 1) {
    const dx = (random() - 0.5) * 40 * t;
    const dy = -60 * Math.sin(Math.PI * t) * (0.6 + random() * 0.6);
    const size = 4 + random() * 3;
    ctx.globalAlpha = t < 0.8 ? 1 : (1 - t) * 5;
    ctx.fillStyle = "#fff4d6";
    ctx.strokeStyle = "#e6b84a";
    ctx.lineWidth = 1;
    for (const [ox, oy] of [
      [0, 0],
      [size * 0.6, -size * 0.4],
      [-size * 0.5, -size * 0.5],
    ] as const) {
      ctx.beginPath();
      ctx.arc(x + dx + ox, y + dy + oy, size * 0.55, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
  }
  ctx.restore();
}

function drawHearts(ctx: CanvasRenderingContext2D, x: number, y: number, t: number): void {
  const random = seeded(Math.round(x * 13 + y * 7));
  ctx.save();
  for (let i = 0; i < 6; i += 1) {
    const delay = i * 0.08;
    const local = Math.min(1, Math.max(0, (t - delay) / (1 - delay)));
    if (local <= 0) continue;
    const spread = (random() - 0.5) * 90;
    const hx = x + spread + Math.sin(local * 6 + i) * 8;
    const hy = y - local * 110 - random() * 20;
    const size = 7 + random() * 6 + local * 4;
    ctx.globalAlpha = 1 - local;
    ctx.fillStyle = `hsl(${String(335 + random() * 20)} 95% ${String(68 + random() * 12)}%)`;
    ctx.beginPath();
    ctx.moveTo(hx, hy + size * 0.35);
    ctx.bezierCurveTo(
      hx - size,
      hy - size * 0.4,
      hx - size * 0.45,
      hy - size,
      hx,
      hy - size * 0.45,
    );
    ctx.bezierCurveTo(
      hx + size * 0.45,
      hy - size,
      hx + size,
      hy - size * 0.4,
      hx,
      hy + size * 0.35,
    );
    ctx.fill();
  }
  ctx.restore();
}

/** Кольцо «закрепится здесь»: пунктир пульсирует, в центре точка опоры. */
function drawMark(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  hue: number,
  seed: number,
): void {
  const pulse = 1 + Math.sin(seed / 3) * 0.12;
  ctx.save();
  ctx.lineWidth = 2;
  ctx.setLineDash([6, 6]);
  ctx.lineDashOffset = seed;
  ctx.strokeStyle = `hsla(${String(hue)}, 95%, 75%, 0.9)`;
  ctx.beginPath();
  ctx.arc(x, y, 22 * pulse, 0, Math.PI * 2);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = `hsla(${String(hue)}, 95%, 85%, 0.95)`;
  ctx.beginPath();
  ctx.arc(x, y, 3.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function drawPortal(
  ctx: CanvasRenderingContext2D,
  effect: { x: number; y: number; t: number; opening: boolean },
  hue: number,
): void {
  // Кольцо раскрывается, держится и схлопывается; спираль внутри вращается.
  const open = effect.t < 0.3 ? effect.t / 0.3 : effect.t > 0.75 ? (1 - effect.t) / 0.25 : 1;
  const rx = 70 * open;
  const ry = 130 * open;
  ctx.save();
  ctx.translate(effect.x, effect.y);
  ctx.globalCompositeOperation = "lighter";
  const glow = ctx.createRadialGradient(0, 0, 0, 0, 0, ry * 1.2 + 1);
  glow.addColorStop(0, `hsla(${String(hue)}, 90%, 60%, 0.35)`);
  glow.addColorStop(1, `hsla(${String(hue)}, 90%, 40%, 0)`);
  ctx.fillStyle = glow;
  ctx.fillRect(-ry * 1.2, -ry * 1.2, ry * 2.4, ry * 2.4);
  ctx.lineWidth = 3;
  ctx.strokeStyle = `hsla(${String(hue)}, 95%, 75%, 0.9)`;
  ctx.beginPath();
  ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.setLineDash([10, 14]);
  ctx.lineDashOffset = effect.t * 300 * (effect.opening ? 1 : -1);
  ctx.strokeStyle = `hsla(${String((hue + 40) % 360)}, 95%, 70%, 0.7)`;
  ctx.beginPath();
  ctx.ellipse(0, 0, rx * 0.7, ry * 0.7, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

/** Нарисовать эффекты тела; `seed` меняется 30 раз в секунду — молния «живёт». */
export function drawEffects(
  ctx: CanvasRenderingContext2D,
  effects: readonly Effect[],
  hue: number,
  seed: number,
): void {
  for (const effect of effects) {
    if (effect.kind === "bolt") drawBolt(ctx, effect.from, effect.to, hue, seed, effect.t);
    else if (effect.kind === "sparks") drawSparks(ctx, effect.x, effect.y, effect.t, hue);
    else if (effect.kind === "hearts") drawHearts(ctx, effect.x, effect.y, effect.t);
    else if (effect.kind === "popcorn") drawPopcorn(ctx, effect.x, effect.y, effect.t);
    else if (effect.kind === "mark") drawMark(ctx, effect.x, effect.y, hue, seed);
    else drawPortal(ctx, effect, hue);
  }
}
