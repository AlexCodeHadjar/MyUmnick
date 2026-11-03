/**
 * Подключение движка Live2D: Cubism Core → Pixi и движок (динамически, отдельным чанком) →
 * регистрация плагина. И то, что нужно от внутренней модели Cubism: индексы параметров рта и
 * наклона головы.
 */
import type { HeadAxis } from "../gesture";
import { loadCubismCore } from "./core-loader";

export type Engine = typeof import("untitled-pixi-live2d-engine/cubism");
export type Pixi = typeof import("pixi.js");
export type Model = Awaited<ReturnType<Engine["Live2DModel"]["from"]>>;
export type CubismInternal = InstanceType<Engine["CubismInternalModel"]>;

/** Рот, если в model3.json нет группы `LipSync`: стандартные id Cubism 3+ и 2.1. */
const DEFAULT_MOUTH_IDS = ["ParamMouthOpenY", "PARAM_MOUTH_OPEN_Y"];
/** Наклон головы вверх-вниз (кивок): стандартные id Cubism 3+ и 2.1. */
const HEAD_PITCH_IDS = ["ParamAngleY", "PARAM_ANGLE_Y"];
const HEAD_YAW_IDS = ["ParamAngleX", "PARAM_ANGLE_X"];
const HEAD_ROLL_IDS = ["ParamAngleZ", "PARAM_ANGLE_Z"];

export async function loadEngine(): Promise<{ pixi: Pixi; engine: Engine }> {
  await loadCubismCore();
  // Pixi 8 без `unsafe-eval` не работает под CSP окна (нет 'unsafe-eval') — полифилл до рендера.
  const [pixi, engine] = await Promise.all([
    import("pixi.js"),
    import("untitled-pixi-live2d-engine/cubism"),
    import("pixi.js/unsafe-eval"),
  ]);
  // Плагин регистрируется до создания рендера — требование движка.
  pixi.extensions.add(engine.Live2DPlugin);
  return { pixi, engine };
}

/** Индексы параметров рта: ищутся один раз при загрузке, в кадре — запись по индексу. */
export function mouthIndices(internal: CubismInternal): number[] {
  const declared = internal.motionManager.lipSyncIds;
  return parameterIndices(internal, declared.length > 0 ? declared : DEFAULT_MOUTH_IDS);
}

/** Индексы наклона головы для кивка; у модели без параметра — пусто, кивка нет. */
export function headPitchIndices(internal: CubismInternal): number[] {
  return parameterIndices(internal, HEAD_PITCH_IDS);
}

/** Индексы параметров головы по осям для жестов; нет параметра — жест по этой оси не виден. */
export function headAxisIndices(internal: CubismInternal): Record<HeadAxis, number[]> {
  return {
    pitch: parameterIndices(internal, HEAD_PITCH_IDS),
    yaw: parameterIndices(internal, HEAD_YAW_IDS),
    roll: parameterIndices(internal, HEAD_ROLL_IDS),
  };
}

function parameterIndices(internal: CubismInternal, ids: readonly string[]): number[] {
  const wanted = new Set(ids);
  const core = internal.coreModel;
  const indices: number[] = [];
  for (let i = 0; i < core.getParameterCount(); i++) {
    if (wanted.has(core.getParameterId(i).getString().s)) {
      indices.push(i);
    }
  }
  return indices;
}
