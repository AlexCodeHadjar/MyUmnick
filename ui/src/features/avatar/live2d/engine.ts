/**
 * Подключение движка Live2D: Cubism Core → Pixi и движок (динамически, отдельным чанком) →
 * регистрация плагина. И то, что нужно от внутренней модели Cubism: индексы параметров рта.
 */
import { loadCubismCore } from "./core-loader";

export type Engine = typeof import("untitled-pixi-live2d-engine/cubism");
export type Pixi = typeof import("pixi.js");
export type Model = Awaited<ReturnType<Engine["Live2DModel"]["from"]>>;
export type CubismInternal = InstanceType<Engine["CubismInternalModel"]>;

/** Рот, если в model3.json нет группы `LipSync`: стандартные id Cubism 3+ и 2.1. */
const DEFAULT_MOUTH_IDS = ["ParamMouthOpenY", "PARAM_MOUTH_OPEN_Y"];

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
  const wanted = new Set(declared.length > 0 ? declared : DEFAULT_MOUTH_IDS);
  const core = internal.coreModel;
  const indices: number[] = [];
  for (let i = 0; i < core.getParameterCount(); i++) {
    if (wanted.has(core.getParameterId(i).getString().s)) {
      indices.push(i);
    }
  }
  return indices;
}
