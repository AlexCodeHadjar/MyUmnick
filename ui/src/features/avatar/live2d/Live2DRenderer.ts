/**
 * Live2D-реализация `AvatarRenderer` на PixiJS 8 + untitled-pixi-live2d-engine (ADR-0011).
 * Движок и Pixi грузятся динамически после Cubism Core: основной бандл (чат) их не ждёт.
 * Автообновление движка и его слежение за курсором выключены — кадрами управляет `AvatarLoop`
 * (R-66), взглядом — `lookAt()`. Покой, моргание, дыхание и физику движок делает сам.
 */
import type { AvatarRenderer, AvatarSource, StageSize } from "../AvatarRenderer";
import { loadCubismCore } from "./core-loader";
import { fitModel } from "./fit";

type Engine = typeof import("untitled-pixi-live2d-engine/cubism");
type Pixi = typeof import("pixi.js");
type Model = Awaited<ReturnType<Engine["Live2DModel"]["from"]>>;

/** Группа моушенов покоя по соглашению Cubism (`Idle` в model3.json). */
const IDLE_GROUP = "Idle";
/** Рот, если в model3.json нет группы `LipSync`: стандартные id Cubism 3+ и 2.1. */
const DEFAULT_MOUTH_IDS = ["ParamMouthOpenY", "PARAM_MOUTH_OPEN_Y"];

type CubismInternal = InstanceType<Engine["CubismInternalModel"]>;

/** Индексы параметров рта: ищутся один раз при загрузке, в кадре — запись по индексу. */
function mouthIndices(internal: CubismInternal): number[] {
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

async function loadEngine(): Promise<{ pixi: Pixi; engine: Engine }> {
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

export class Live2DRenderer implements AvatarRenderer {
  readonly #app: InstanceType<Pixi["Application"]>;
  readonly #engine: Engine;
  #model: Model | null = null;
  #size: StageSize;
  #mouth = 0;

  private constructor(app: InstanceType<Pixi["Application"]>, engine: Engine, size: StageSize) {
    this.#app = app;
    this.#engine = engine;
    this.#size = size;
  }

  /** Холст создаётся здесь: `host` — элемент сцены, холст займёт его целиком. */
  static async create(host: HTMLElement, size: StageSize): Promise<Live2DRenderer> {
    const { pixi, engine } = await loadEngine();
    const app = new pixi.Application();
    await app.init({
      width: size.width,
      height: size.height,
      preference: "webgl",
      backgroundAlpha: 0,
      antialias: true,
      autoDensity: true,
      resolution: window.devicePixelRatio,
      autoStart: false,
    });
    host.append(app.canvas);
    return new Live2DRenderer(app, engine, size);
  }

  async load(source: AvatarSource): Promise<void> {
    const model = await this.#engine.Live2DModel.from(source.modelUrl, {
      autoUpdate: false,
      autoFocus: false,
      autoHitTest: false,
    });
    this.#unload();
    model.anchor.set(0.5, 0.5);
    this.#hookMouth(model);
    this.#app.stage.addChild(model);
    this.#model = model;
    this.#place();
    void model.motion(IDLE_GROUP);
  }

  setEmotion(): void {
    // Маппинг эмоция → выражение — S-6.3 (mapping.json); до него эмоции не показываются.
  }

  setMouth(openness: number): void {
    this.#mouth = Math.max(0, Math.min(1, openness));
  }

  lookAt(x: number, y: number): void {
    this.#model?.internalModel.focusController.focus(x, y);
  }

  react(): void {
    // Реакции на ход — S-6.3 (mapping.json).
  }

  update(deltaMs: number): void {
    this.#model?.update(deltaMs);
    this.#app.render();
  }

  resize(size: StageSize): void {
    this.#size = size;
    this.#app.renderer.resize(size.width, size.height);
    this.#place();
  }

  dispose(): void {
    this.#unload();
    this.#app.destroy({ removeView: true }, { children: true, texture: true, textureSource: true });
  }

  #place(): void {
    const model = this.#model;
    if (model === null) {
      return;
    }
    // Размер модели — в её собственных единицах, без текущего масштаба.
    const natural = { width: model.width / model.scale.x, height: model.height / model.scale.y };
    const placement = fitModel(natural, this.#size);
    model.scale.set(placement.scale);
    model.position.set(placement.x, placement.y);
  }

  /** После моушенов и физики, до отрисовки: наш липсинк перекрывает рот из моушена. */
  #hookMouth(model: Model): void {
    const internal = model.internalModel;
    // Точка входа `/cubism` грузит только Cubism 3–5, но тип модели — общий базовый.
    if (!(internal instanceof this.#engine.CubismInternalModel)) {
      return;
    }
    const indices = mouthIndices(internal);
    internal.on("beforeModelUpdate", () => {
      for (const index of indices) {
        internal.coreModel.setParameterValueByIndex(index, this.#mouth);
      }
    });
  }

  #unload(): void {
    if (this.#model !== null) {
      this.#app.stage.removeChild(this.#model);
      this.#model.destroy({ children: true });
      this.#model = null;
    }
  }
}
