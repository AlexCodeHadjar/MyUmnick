/**
 * Геометрия сферы «как у Джарвиса» (Этап 22): точки по сфере Фибоначчи и рёбра к ближайшим соседям.
 * Считается один раз при создании; в кадре — только поворот и проекция (без выделения памяти).
 */

export interface Sphere {
  /** Единичные векторы точек: x, y, z подряд. */
  points: Float32Array;
  /** Пары индексов рёбер: a, b подряд; каждое ребро один раз. */
  edges: Uint16Array;
}

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

/** `count` точек, равномерно по сфере (спираль Фибоначчи). */
export function fibonacciSphere(count: number): Float32Array {
  const points = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 1) {
    const y = 1 - (2 * (i + 0.5)) / count;
    const ring = Math.sqrt(1 - y * y);
    const theta = GOLDEN_ANGLE * i;
    points[i * 3] = Math.cos(theta) * ring;
    points[i * 3 + 1] = y;
    points[i * 3 + 2] = Math.sin(theta) * ring;
  }
  return points;
}

/** Рёбра к `neighbors` ближайшим точкам; повторы (a–b и b–a) убираются. */
export function nearestEdges(points: Float32Array, neighbors: number): Uint16Array {
  const count = points.length / 3;
  const seen = new Set<number>();
  const edges: number[] = [];
  for (let a = 0; a < count; a += 1) {
    for (const b of closest(points, a, neighbors)) {
      const key = a < b ? a * count + b : b * count + a;
      if (!seen.has(key)) {
        seen.add(key);
        edges.push(a, b);
      }
    }
  }
  return Uint16Array.from(edges);
}

function closest(points: Float32Array, index: number, take: number): number[] {
  const count = points.length / 3;
  const distances: [number, number][] = [];
  for (let other = 0; other < count; other += 1) {
    if (other !== index) distances.push([squaredDistance(points, index, other), other]);
  }
  distances.sort((left, right) => left[0] - right[0]);
  return distances.slice(0, take).map(([, other]) => other);
}

function squaredDistance(points: Float32Array, a: number, b: number): number {
  const dx = (points[a * 3] ?? 0) - (points[b * 3] ?? 0);
  const dy = (points[a * 3 + 1] ?? 0) - (points[b * 3 + 1] ?? 0);
  const dz = (points[a * 3 + 2] ?? 0) - (points[b * 3 + 2] ?? 0);
  return dx * dx + dy * dy + dz * dz;
}

export function buildSphere(count: number, neighbors: number): Sphere {
  const points = fibonacciSphere(count);
  return { points, edges: nearestEdges(points, neighbors) };
}

/**
 * Отклонение точки вдоль радиуса: «вибрация» голосом. Волны бегут по поверхности (зависят от
 * положения точки), поэтому сфера колышется плавно, а не ершится случайными иглами.
 */
export function ripple(x: number, y: number, z: number, timeS: number, energy: number): number {
  const band = Math.sin(timeS * 7 + y * 5);
  const swirl = Math.sin(timeS * 11 + (x + z) * 4);
  const fine = Math.sin(timeS * 19 + (x - y + z) * 9);
  return energy * (0.5 * band + 0.35 * swirl + 0.15 * fine);
}
