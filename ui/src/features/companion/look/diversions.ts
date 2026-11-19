import type { Body } from "../body";
import type { Scene } from "../behavior/diversions";
import type { Pose } from "../space";

/** Поза сцены (FRAMES-6): у каждой сцены свои кадры; `peek` — поза остаётся (её режет край окна). */
const SCENE_POSE: Readonly<Record<Scene["kind"], Pose | null>> = {
  bug: "chase",
  trip: "trip",
  knock: "knock",
  juggle: "juggle",
  read: "read",
  draw: "draw",
  peek: null,
};

export function poseScene(body: Body, scene: Scene, height: number): void {
  const pose = SCENE_POSE[scene.kind];
  if (pose !== null) body.pose = pose;
  if (scene.kind === "bug") {
    // Бежит за жуком: несколько шагов вперёд и назад, кадры бега — `chase_1…6`.
    body.x += body.facing * height * 0.23 * Math.sin(Math.PI * scene.progress);
  }
}

/** Props are painted in unit coordinates relative to the boots. */
export function drawDiversion(
  ctx: CanvasRenderingContext2D,
  body: Body,
  scene: Scene,
  height: number,
): void {
  const t = scene.progress;
  ctx.save();
  ctx.translate(body.x, body.y);
  ctx.scale(height * body.facing, height);
  ctx.lineWidth = 0.009;
  ctx.lineJoin = "round";
  ctx.strokeStyle = "#172343";
  ctx.fillStyle = "#f3dfad";
  const rect = (x: number, y: number, w: number, h: number) => {
    ctx.fillRect(x, y, w, h);
    ctx.strokeRect(x, y, w, h);
  };
  const dot = (x: number, y: number, r: number) => {
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  };
  switch (scene.kind) {
    case "knock": {
      const pulse = (t * 3) % 1;
      ctx.strokeStyle = "#9ae8ff";
      ctx.globalAlpha = 1 - pulse;
      ctx.beginPath();
      // Кулак кадра `knock` (FRAMES-6 §5.3): чуть впереди и на уровне головы.
      ctx.arc(0.14, -0.64, 0.025 + pulse * 0.15, 0, Math.PI * 2);
      ctx.stroke();
      break;
    }
    case "juggle":
      for (let i = 0; i < 3; i++) {
        const p = (t * 3 + i / 3) % 1;
        ctx.fillStyle = ["#82daf8", "#eccd91", "#ad9cef"][i] ?? "#fff";
        // Ладони кадров `juggle` — у груди; иконки взлетают над головой.
        rect(-0.16 + 0.34 * p, -0.55 - 0.32 * Math.sin(Math.PI * p), 0.045, 0.058);
      }
      break;
    case "bug":
      ctx.translate(0.2 + 0.06 * Math.sin(t * 9), -0.065 - 0.08 * Math.abs(Math.sin(t * 10)));
      ctx.fillStyle = "#19334c";
      dot(0, 0, 0.025);
      ctx.fillStyle = "#7be4ff";
      dot(0.013, -0.022, 0.018);
      dot(-0.018, -0.018, 0.014);
      break;
  }
  ctx.restore();
}
