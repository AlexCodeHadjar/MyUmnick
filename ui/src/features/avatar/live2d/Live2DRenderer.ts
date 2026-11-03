/**
 * Live2D-реализация `AvatarRenderer` на PixiJS 8 + untitled-pixi-live2d-engine (ADR-0011).
 * Автообновление движка и его слежение за курсором выключены — кадрами управляет `AvatarLoop`
 * (R-66), взглядом — `lookAt()`. Покой, моргание, дыхание и физику движок делает сам; эмоции,
 * реакции и кадр — по `mapping.json` модели; кивок и рот — поверх моушенов, перед отрисовкой.
 */
import type { Emotion, Gesture } from "../../../core";
import type { AvatarReaction, AvatarRenderer, AvatarSource, StageSize } from "../AvatarRenderer";
import { gestureAngle, type GestureSpec } from "../gesture";
import { DEFAULT_MAPPING, expressionFor, type AvatarMapping } from "../mapping";
import { NOD_MS, nodAngle } from "../nod";
import {
  headAxisIndices,
  headPitchIndices,
  loadEngine,
  mouthFormIndices,
  mouthIndices,
  type Engine,
  type Model,
  type Pixi,
} from "./engine";
import { applyFrame, fitModel } from "./fit";
import { loadMapping, loadSettings } from "./settings";

/** Группа моушенов покоя по соглашению Cubism (`Idle` в model3.json). */
const IDLE_GROUP = "Idle";
/** Интервал моргания, с: по умолчанию Cubism — 4; в речи люди моргают примерно вдвое чаще. */
const CALM_BLINK_S = 4;
const SPEAKING_BLINK_S = 2;
/** Рот ниже этого — закрыт: после речи липсинк отпускает рот выражению. */
const MOUTH_EPSILON = 0.01;

export class Live2DRenderer implements AvatarRenderer {
  readonly #app: InstanceType<Pixi["Application"]>;
  readonly #engine: Engine;
  #model: Model | null = null;
  #mapping: AvatarMapping = DEFAULT_MAPPING;
  #size: StageSize;
  #mouth = 0;
  #mouthForm = 0;
  #speaking = false;
  /** Сколько мс идёт кивок; null — кивка нет. */
  #nodMs: number | null = null;
  /** Идущий жест и сколько мс он длится. */
  #gesture: { spec: GestureSpec; ms: number } | null = null;
  #emotion: Emotion = "neutral";
  #reaction: AvatarReaction = "idle";
  /** Выражение на лице сейчас: движок не дёргается, пока нужное выражение не изменилось. */
  #expression: string | null = null;

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
    const mapping = await loadMapping(source.mappingUrl);
    const settings = await loadSettings(source.modelUrl, mapping);
    const model = await this.#engine.Live2DModel.from(settings, {
      autoUpdate: false,
      autoFocus: false,
      autoHitTest: false,
    });
    this.#unload();
    this.#mapping = mapping;
    model.anchor.set(0.5, 0.5);
    this.#hookParameters(model);
    this.#app.stage.addChild(model);
    this.#model = model;
    this.#place();
    void model.motion(IDLE_GROUP);
    this.#applyExpression();
  }

  setEmotion(emotion: Emotion, intensity: number): void {
    // Выражение Live2D — целиком или никак: частичного веса у движка нет. Плавность возврата к
    // нейтральному — fade-out самого выражения (FadeOutTime в exp3.json).
    this.#emotion = intensity > 0 ? emotion : "neutral";
    this.#applyExpression();
  }

  nod(): void {
    this.#nodMs = 0;
  }

  gesture(gesture: Gesture): void {
    const spec = this.#mapping.gestures[gesture];
    if (spec !== undefined) {
      this.#gesture = { spec, ms: 0 };
    }
  }

  setSpeaking(speaking: boolean): void {
    this.#speaking = speaking;
    const internal = this.#model?.internalModel;
    if (internal instanceof this.#engine.CubismInternalModel) {
      internal.eyeBlink?.setBlinkingInterval(speaking ? SPEAKING_BLINK_S : CALM_BLINK_S);
    }
  }

  setMouth(openness: number): void {
    this.#mouth = Math.max(0, Math.min(1, openness));
  }

  setMouthForm(form: number): void {
    this.#mouthForm = Math.max(-1, Math.min(1, form));
  }

  lookAt(x: number, y: number): void {
    this.#model?.internalModel.focusController.focus(x, y);
  }

  react(reaction: AvatarReaction): void {
    if (reaction === this.#reaction) {
      return;
    }
    this.#reaction = reaction;
    const motion = this.#mapping.reactions[reaction]?.motion;
    if (motion !== undefined && this.#model !== null) {
      // Моушен не сбрасывает выражение: «думаю» на лице держится, пока идёт жест.
      // NORMAL — выше покоя, но не перебивает принудительные моушены.
      void this.#model.motion(motion.group, motion.index, this.#engine.MotionPriority.NORMAL, {
        resetExpression: false,
      });
    }
    this.#applyExpression();
  }

  update(deltaMs: number): void {
    if (this.#nodMs !== null) {
      this.#nodMs += deltaMs;
      if (this.#nodMs >= NOD_MS) {
        this.#nodMs = null;
      }
    }
    if (this.#gesture !== null) {
      this.#gesture.ms += deltaMs;
      if (this.#gesture.ms >= this.#gesture.spec.ms) {
        this.#gesture = null;
      }
    }
    this.#model?.update(deltaMs);
    this.#app.render();
  }

  contains(x: number, y: number): boolean {
    return this.#model?.getBounds().rectangle.contains(x, y) ?? false;
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

  #applyExpression(): void {
    const model = this.#model;
    const wanted = expressionFor(this.#mapping, this.#emotion, this.#reaction);
    if (model === null || wanted === this.#expression) {
      return;
    }
    this.#expression = wanted;
    if (wanted === null) {
      model.internalModel.motionManager.expressionManager?.resetExpression();
    } else {
      void model.expression(wanted);
    }
  }

  #place(): void {
    const model = this.#model;
    if (model === null) {
      return;
    }
    // Размер модели — в её собственных единицах, без текущего масштаба.
    const natural = { width: model.width / model.scale.x, height: model.height / model.scale.y };
    const placement = applyFrame(fitModel(natural, this.#size), this.#size, this.#mapping.frame);
    model.scale.set(placement.scale);
    model.position.set(placement.x, placement.y);
  }

  /**
   * После моушенов и физики, до отрисовки: наш липсинк перекрывает рот из моушена и выражения,
   * кивок добавляется к наклону головы (покой и взгляд остаются). Рот перекрывается только в
   * речи: иначе выражение с открытым ртом (у Haru «Smile») после речи стало бы плоским.
   */
  #hookParameters(model: Model): void {
    const internal = model.internalModel;
    // Точка входа `/cubism` грузит только Cubism 3–5, но тип модели — общий базовый.
    if (!(internal instanceof this.#engine.CubismInternalModel)) {
      return;
    }
    const mouth = mouthIndices(internal);
    const { formParam, strength } = this.#mapping.lipsync;
    const form = mouthFormIndices(internal, formParam);
    const head = headPitchIndices(internal);
    const axes = headAxisIndices(internal);
    internal.on("beforeModelUpdate", () => {
      const core = internal.coreModel;
      if (this.#speaking || this.#mouth > MOUTH_EPSILON) {
        for (const index of mouth) {
          core.setParameterValueByIndex(index, this.#mouth);
        }
        for (const index of form) {
          core.setParameterValueByIndex(index, this.#mouthForm * strength);
        }
      }
      const angle = this.#nodMs === null ? 0 : nodAngle(this.#nodMs);
      for (const index of head) {
        core.addParameterValueByIndex(index, angle);
      }
      const gesture = this.#gesture;
      if (gesture !== null) {
        const offset = gestureAngle(gesture.spec, gesture.ms);
        for (const index of axes[gesture.spec.axis]) {
          core.addParameterValueByIndex(index, offset);
        }
      }
    });
  }

  #unload(): void {
    if (this.#model !== null) {
      this.#app.stage.removeChild(this.#model);
      this.#model.destroy({ children: true });
      this.#model = null;
      this.#expression = null;
    }
  }
}
