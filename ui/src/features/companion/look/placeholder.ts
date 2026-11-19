/**
 * Временные позы спутника (раздел 5.2): силуэты из линий на холсте 512×1024, пока пользователь не
 * загрузил свои картинки. По ним видно, какая поза где включается; рисуются в коде — файлов нет.
 */
import type { Pose } from "../space";
import type { ScenePose } from "./scenePoses";

type Joint = readonly [number, number];

/** Голова, шея, таз, локти, кисти, колени, ступни — координаты холста 512×1024. */
interface Figure {
  head: Joint;
  neck: Joint;
  hip: Joint;
  elbows: readonly [Joint, Joint];
  hands: readonly [Joint, Joint];
  knees: readonly [Joint, Joint];
  feet: readonly [Joint, Joint];
}

const STAND: Figure = {
  head: [256, 150],
  neck: [256, 260],
  hip: [256, 560],
  elbows: [
    [190, 420],
    [322, 420],
  ],
  hands: [
    [170, 560],
    [342, 560],
  ],
  knees: [
    [220, 780],
    [292, 780],
  ],
  feet: [
    [210, 990],
    [302, 990],
  ],
};

const SIT: Figure = {
  head: [256, 230],
  neck: [256, 330],
  hip: [256, 630],
  elbows: [
    [200, 480],
    [312, 480],
  ],
  hands: [
    [200, 620],
    [312, 620],
  ],
  knees: [
    [330, 650],
    [370, 650],
  ],
  feet: [
    [320, 900],
    [360, 900],
  ],
};

/** Силуэты сцен FRAMES-6 — стоя (у сцен свои кадры; силуэт нужен только до загрузки пакета). */
const SCENE_FIGURES: Record<ScenePose, Figure> = {
  purr: STAND,
  knock: STAND,
  carry_box: STAND,
  stamp: STAND,
  hug_paper: STAND,
  flinch: STAND,
  blown: STAND,
  read: STAND,
  draw: STAND,
  juggle: STAND,
  trip: STAND,
  chase: STAND,
  inspect: STAND,
  pocket: STAND,
  put_back: STAND,
  throw: STAND,
  dust_hands: STAND,
  build: STAND,
  note_put: STAND,
  note_take: STAND,
};

const FIGURES: Record<Pose, Figure> = {
  stand: STAND,
  walk: {
    ...STAND,
    knees: [
      [200, 770],
      [310, 770],
    ],
    feet: [
      [160, 980],
      [340, 970],
    ],
  },
  lean_side: {
    ...STAND,
    head: [300, 160],
    neck: [290, 270],
    elbows: [
      [230, 400],
      [380, 330],
    ],
    hands: [
      [200, 540],
      [420, 250],
    ],
  },
  sit_edge: SIT,
  perch_corner: {
    ...SIT,
    knees: [
      [310, 660],
      [300, 640],
    ],
    feet: [
      [300, 900],
      [280, 880],
    ],
  },
  sit_corner: {
    ...SIT,
    knees: [
      [360, 760],
      [380, 720],
    ],
    feet: [
      [460, 950],
      [470, 930],
    ],
    hip: [256, 940],
    neck: [240, 640],
    head: [236, 540],
    elbows: [
      [190, 780],
      [300, 780],
    ],
    hands: [
      [230, 900],
      [320, 900],
    ],
  },
  laydown: {
    head: [80, 860],
    neck: [150, 880],
    hip: [330, 900],
    elbows: [
      [200, 840],
      [230, 950],
    ],
    hands: [
      [120, 800],
      [280, 960],
    ],
    knees: [
      [400, 870],
      [410, 910],
    ],
    feet: [
      [480, 900],
      [490, 930],
    ],
  },
  sleep: {
    head: [90, 880],
    neck: [150, 890],
    hip: [330, 905],
    elbows: [
      [210, 870],
      [230, 950],
    ],
    hands: [
      [120, 880],
      [260, 960],
    ],
    knees: [
      [390, 880],
      [400, 910],
    ],
    feet: [
      [470, 900],
      [480, 930],
    ],
  },
  held: {
    head: [256, 170],
    neck: [256, 120],
    hip: [256, 520],
    elbows: [
      [200, 260],
      [312, 260],
    ],
    hands: [
      [230, 70],
      [282, 70],
    ],
    knees: [
      [230, 740],
      [300, 730],
    ],
    feet: [
      [240, 950],
      [290, 960],
    ],
  },
  hang_side: {
    head: [256, 200],
    neck: [256, 290],
    hip: [256, 600],
    elbows: [
      [210, 150],
      [302, 150],
    ],
    hands: [
      [230, 40],
      [282, 40],
    ],
    knees: [
      [240, 800],
      [280, 800],
    ],
    feet: [
      [245, 1000],
      [275, 1000],
    ],
  },
  pet: STAND,
  reach: STAND,
  sing: STAND,
  radio_idle: STAND,
  dizzy: STAND,
  wave: STAND,
  yawn: STAND,
  dance: STAND,
  watch: STAND,
  jukebox: STAND,
  peek: STAND,
  // Сцены FRAMES-6: силуэт стоя; рисуется, только пока пакет не загрузился.
  ...SCENE_FIGURES,
  // Силуэт «лезет» не рисуется: пока нет кадров, берётся силуэт `hang_side` (FALLBACK).
  climb: STAND,
  poke: {
    ...STAND,
    elbows: [
      [200, 420],
      [380, 400],
    ],
    hands: [
      [180, 560],
      [450, 430],
    ],
  },
  float: {
    ...STAND,
    elbows: [
      [160, 340],
      [352, 340],
    ],
    hands: [
      [110, 240],
      [402, 240],
    ],
    knees: [
      [200, 700],
      [330, 700],
    ],
    feet: [
      [230, 860],
      [300, 860],
    ],
  },
};

function limb(ctx: OffscreenCanvasRenderingContext2D, a: Joint, b: Joint, c: Joint): void {
  ctx.beginPath();
  ctx.moveTo(a[0], a[1]);
  ctx.lineTo(b[0], b[1]);
  ctx.lineTo(c[0], c[1]);
  ctx.stroke();
}

/** Силуэт позы: широкие линии с градиентом палитры окна, круг головы, подпись с именем позы. */
export async function placeholderPose(pose: Pose, height: number): Promise<ImageBitmap> {
  const canvas = new OffscreenCanvas(512, 1024);
  const ctx = canvas.getContext("2d");
  if (ctx === null) return createImageBitmap(canvas);
  const f = FIGURES[pose];
  const paint = ctx.createLinearGradient(0, 0, 0, 1024);
  paint.addColorStop(0, "#a7b8ff");
  paint.addColorStop(1, "#7c6cff");
  ctx.strokeStyle = paint;
  ctx.fillStyle = paint;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.lineWidth = 46;
  ctx.beginPath();
  ctx.moveTo(f.neck[0], f.neck[1]);
  ctx.lineTo(f.hip[0], f.hip[1]);
  ctx.stroke();
  ctx.lineWidth = 34;
  for (const i of [0, 1] as const) {
    limb(ctx, f.neck, f.elbows[i], f.hands[i]);
    limb(ctx, f.hip, f.knees[i], f.feet[i]);
  }
  ctx.beginPath();
  ctx.arc(f.head[0], f.head[1], 70, 0, Math.PI * 2);
  ctx.fill();
  ctx.font = "28px sans-serif";
  ctx.fillStyle = "rgba(233, 234, 244, 0.6)";
  ctx.textAlign = "center";
  ctx.fillText(pose, 256, 1016);
  return createImageBitmap(canvas, {
    resizeHeight: Math.round(height * (1024 / 960) * devicePixelRatio),
    resizeQuality: "high",
  });
}
