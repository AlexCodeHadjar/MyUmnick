/**
 * Сфера из точек и связей вместо модели (Этап 22, ADR-0038): Canvas 2D, без Pixi и Live2D.
 * Голос (`setMouth`) раскачивает точки вдоль радиуса и раздувает свечение; эмоция тянет оттенок;
 * «думаю» ускоряет вращение и пульс; взгляд (`lookAt`) наклоняет сферу к курсору.
 * Работает за контрактом `AvatarRenderer`: остальное UI не знает, модель это или сфера.
 */
import type { Emotion } from "../../../core";
import type { AvatarReaction, AvatarRenderer, StageSize } from "../AvatarRenderer";
import { buildSphere, ripple, type Sphere } from "./geometry";
import { EMOTION_HUE, mixHue, shimmerHue, sparkle } from "./palette";

const POINTS = 420;
const NEIGHBORS = 3;
const IDLE_SPIN = 0.18; // рад/с
const THINK_SPIN = 0.6;
const RADIUS_SHARE = 0.34; // доля меньшей стороны сцены
const PERSPECTIVE = 2.6;
const EDGE_BUCKETS = 4;

/** Сглаживание к цели за кадр: `rate` в 1/с. */
function approach(current: number, target: number, rate: number, dt: number): number {
  return current + (target - current) * Math.min(1, rate * dt);
}

export class OrbRenderer implements AvatarRenderer {
  readonly #canvas: HTMLCanvasElement;
  readonly #ctx: CanvasRenderingContext2D;
  readonly #sphere: Sphere = buildSphere(POINTS, NEIGHBORS);
  readonly #screen = new Float32Array(POINTS * 3); // x, y, глубина 0…1
  #size: StageSize;
  #time = 0;
  #angle = 0;
  #mouth = 0;
  #energy = 0;
  #pulse = 0;
  #hue = EMOTION_HUE.neutral;
  #targetHue = EMOTION_HUE.neutral;
  #look = { x: 0, y: 0 };
  #tilt = { x: 0, y: 0 };
  #reaction: AvatarReaction = "idle";
  #speaking = false;
  #ambient = { bass: 0, mid: 0, high: 0 };

  private constructor(host: HTMLElement, size: StageSize) {
    this.#canvas = document.createElement("canvas");
    this.#canvas.className = "orb";
    this.#canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%";
    host.append(this.#canvas);
    const ctx = this.#canvas.getContext("2d");
    if (ctx === null) throw new Error("Canvas 2D недоступен в этом окне");
    this.#ctx = ctx;
    this.#size = size;
    this.resize(size);
  }

  static create(host: HTMLElement, size: StageSize): Promise<OrbRenderer> {
    return Promise.resolve(new OrbRenderer(host, size));
  }

  load(): Promise<void> {
    return Promise.resolve(); // файлов модели у сферы нет
  }

  setEmotion(emotion: Emotion, intensity: number): void {
    this.#targetHue = mixHue(EMOTION_HUE.neutral, EMOTION_HUE[emotion], intensity);
  }

  nod(): void {
    this.#pulse = Math.max(this.#pulse, 0.6);
  }

  gesture(): void {
    this.#pulse = Math.max(this.#pulse, 1);
  }

  setSpeaking(speaking: boolean): void {
    this.#speaking = speaking;
  }

  setMouth(openness: number): void {
    this.#mouth = Math.min(1, Math.max(0, openness));
  }

  setMouthForm(): void {
    // Форма рта у сферы не видна: только громкость.
  }

  setAmbient(bands: { bass: number; mid: number; high: number }): void {
    this.#ambient = bands;
  }

  lookAt(x: number, y: number): void {
    this.#look = { x: Math.max(-1, Math.min(1, x)), y: Math.max(-1, Math.min(1, y)) };
  }

  react(reaction: AvatarReaction): void {
    this.#reaction = reaction;
  }

  update(deltaMs: number): void {
    const dt = Math.min(0.1, deltaMs / 1000);
    this.#step(dt);
    this.#project();
    this.#draw();
  }

  contains(x: number, y: number): boolean {
    const radius = this.#radius() * 1.15;
    return Math.hypot(x - this.#size.width / 2, y - this.#size.height / 2) <= radius;
  }

  resize(size: StageSize): void {
    this.#size = size;
    const ratio = window.devicePixelRatio || 1;
    this.#canvas.width = Math.max(1, Math.round(size.width * ratio));
    this.#canvas.height = Math.max(1, Math.round(size.height * ratio));
    this.#ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  dispose(): void {
    this.#canvas.remove();
  }

  #radius(): number {
    return Math.min(this.#size.width, this.#size.height) * RADIUS_SHARE;
  }

  #step(dt: number): void {
    this.#time += dt;
    const thinking = this.#reaction === "thinking";
    this.#angle += (thinking ? THINK_SPIN : IDLE_SPIN + this.#energy * 0.8) * dt;
    // Голос важнее музыки: звук компьютера добавляет волны, но не перекрывает речь.
    const music = this.#ambient.mid * 0.05 + this.#ambient.high * 0.02;
    const target =
      this.#mouth * 0.09 + music + (this.#speaking ? 0.015 : 0) + (thinking ? 0.025 : 0.006);
    this.#energy = approach(this.#energy, target, this.#mouth > this.#energy ? 30 : 6, dt);
    this.#pulse = approach(this.#pulse, 0, 3, dt);
    this.#hue = mixHue(this.#hue, this.#targetHue, dt * 2);
    this.#tilt.x = approach(this.#tilt.x, this.#look.y * 0.35, 3, dt);
    this.#tilt.y = approach(this.#tilt.y, this.#look.x * 0.5, 3, dt);
  }

  #project(): void {
    const { points } = this.#sphere;
    const cx = this.#size.width / 2;
    const cy = this.#size.height / 2;
    // Бас — удар: сфера «вздрагивает» целиком.
    const breathe =
      1 + 0.015 * Math.sin(this.#time * 1.3) + this.#pulse * 0.06 + this.#ambient.bass * 0.12;
    const radius = this.#radius() * breathe * (this.#reaction === "listening" ? 1.03 : 1);
    const yaw = this.#angle + this.#tilt.y;
    const [cosY, sinY, cosX, sinX] = [
      Math.cos(yaw),
      Math.sin(yaw),
      Math.cos(this.#tilt.x),
      Math.sin(this.#tilt.x),
    ];
    for (let i = 0; i < POINTS; i += 1) {
      const [px, py, pz] = [points[i * 3] ?? 0, points[i * 3 + 1] ?? 0, points[i * 3 + 2] ?? 0];
      const scale = 1 + ripple(px, py, pz, this.#time, this.#energy);
      const x0 = px * scale;
      const y0 = py * scale;
      const z0 = pz * scale;
      const x1 = x0 * cosY + z0 * sinY;
      const z1 = -x0 * sinY + z0 * cosY;
      const y2 = y0 * cosX - z1 * sinX;
      const z2 = y0 * sinX + z1 * cosX;
      const persp = PERSPECTIVE / (PERSPECTIVE + z2);
      this.#screen[i * 3] = cx + x1 * radius * persp;
      this.#screen[i * 3 + 1] = cy - y2 * radius * persp;
      this.#screen[i * 3 + 2] = (1 - z2) / 2; // 1 — ближе к зрителю
    }
  }

  #draw(): void {
    const ctx = this.#ctx;
    const { width, height } = this.#size;
    ctx.clearRect(0, 0, width, height);
    // Верха сдвигают оттенок и ускоряют переливание.
    const hue =
      shimmerHue(this.#hue, this.#time * (1 + this.#ambient.high * 3)) + this.#ambient.high * 30;
    this.#halo(hue);
    ctx.globalCompositeOperation = "lighter";
    this.#edges(hue);
    this.#dots(hue);
    ctx.globalCompositeOperation = "source-over";
  }

  #halo(hue: number): void {
    const ctx = this.#ctx;
    const cx = this.#size.width / 2;
    const cy = this.#size.height / 2;
    // Ореол сдержанный: поверх рабочего стола он не должен закрывать всё вокруг сферы.
    const radius = this.#radius() * (1.25 + this.#energy + this.#ambient.bass * 0.3);
    const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    const alpha = Math.min(0.3, 0.08 + this.#energy * 1.2 + this.#ambient.bass * 0.12);
    glow.addColorStop(0, `hsla(${String(hue)}, 90%, 60%, ${String(alpha)})`);
    glow.addColorStop(1, `hsla(${String(hue)}, 90%, 40%, 0)`);
    ctx.fillStyle = glow;
    ctx.fillRect(cx - radius, cy - radius, radius * 2, radius * 2);
  }

  #edges(hue: number): void {
    const ctx = this.#ctx;
    const { edges } = this.#sphere;
    const screen = this.#screen;
    ctx.lineWidth = 0.8;
    // Рёбра по корзинам глубины: один stroke на корзину, а не на ребро.
    for (let bucket = 0; bucket < EDGE_BUCKETS; bucket += 1) {
      const low = bucket / EDGE_BUCKETS;
      const high = (bucket + 1) / EDGE_BUCKETS;
      ctx.beginPath();
      for (let e = 0; e < edges.length; e += 2) {
        const a = edges[e] ?? 0;
        const b = edges[e + 1] ?? 0;
        const depth = ((screen[a * 3 + 2] ?? 0) + (screen[b * 3 + 2] ?? 0)) / 2;
        if (depth < low || depth >= high) continue;
        ctx.moveTo(screen[a * 3] ?? 0, screen[a * 3 + 1] ?? 0);
        ctx.lineTo(screen[b * 3] ?? 0, screen[b * 3 + 1] ?? 0);
      }
      const alpha = 0.08 + high * (0.42 + this.#energy * 3);
      ctx.strokeStyle = `hsla(${String(hue)}, 85%, 60%, ${String(Math.min(0.85, alpha))})`;
      ctx.stroke();
    }
  }

  #dots(hue: number): void {
    const ctx = this.#ctx;
    const screen = this.#screen;
    for (let i = 0; i < POINTS; i += 1) {
      const depth = screen[i * 3 + 2] ?? 0;
      const light = 55 + 25 * sparkle(i, this.#time) * depth;
      const size = 1 + depth * (2 + this.#energy * 10);
      ctx.fillStyle = `hsla(${String((hue + i * 0.15) % 360)}, 90%, ${String(light)}%, ${String(0.25 + depth * 0.75)})`;
      ctx.fillRect(
        (screen[i * 3] ?? 0) - size / 2,
        (screen[i * 3 + 1] ?? 0) - size / 2,
        size,
        size,
      );
    }
  }
}
