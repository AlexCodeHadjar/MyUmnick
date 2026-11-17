/**
 * Окно персонажа (Этап 23, ADR-0044): картинка пользователя вместо модели. Жизнь — процедурная, без
 * кадров от художника: дыхание, покачивание, подскок в такт речи, свечение по эмоции, вспышка на зов,
 * лёгкий наклон к курсору. Всё — CSS-трансформации одного `<img>`: браузер сам декодирует и
 * масштабирует картинку, GIF/WebP/APNG анимируются без нашего кода, GPU почти не тратится.
 */
import type { Emotion } from "../../../core";
import type { AvatarReaction, AvatarRenderer } from "../AvatarRenderer";
import { EMOTION_HUE, mixHue } from "../orb/palette";
import { loadFit, loadPicture, pictureChanged, windowStorage, type PictureFit } from "./picture";
import silhouette from "./silhouette.svg";

/** Персонаж по умолчанию — поза «стоит» встроенного персонажа (Этап 23); не загрузилась — силуэт. */
const DEFAULT_PICTURE = "/characters/default/stand.webp";

const BREATH_PERIOD_S = 3.5;
const BREATH_SCALE = 0.012;
const SWAY_DEG = 0.6;
const BOUNCE_PX = 6;
const TILT_DEG = 4;

function approach(current: number, target: number, rate: number, dt: number): number {
  return current + (target - current) * Math.min(1, rate * dt);
}

/** Поза кадра: чистая функция времени и состояния — проверяется тестами. */
export function portraitPose(state: {
  time: number;
  mouth: number;
  pulse: number;
  lookX: number;
  lookY: number;
}): { scaleY: number; rotate: number; lift: number; tiltX: number; tiltY: number } {
  const breath = Math.sin((state.time / BREATH_PERIOD_S) * Math.PI * 2);
  return {
    scaleY: 1 + BREATH_SCALE * (breath + 1) * 0.5 + state.pulse * 0.02,
    rotate: SWAY_DEG * Math.sin(state.time * 0.7),
    lift: -(state.mouth * BOUNCE_PX + state.pulse * 8),
    tiltX: state.lookY * TILT_DEG,
    tiltY: state.lookX * TILT_DEG,
  };
}

export class PortraitRenderer implements AvatarRenderer {
  readonly #root: HTMLDivElement;
  readonly #glow: HTMLDivElement;
  readonly #image: HTMLImageElement;
  readonly #dots: HTMLDivElement;
  #url: string | null = null;
  #time = 0;
  #mouth = 0;
  #mouthTarget = 0;
  #pulse = 0;
  #attention = 0;
  #hue = EMOTION_HUE.neutral;
  #targetHue = EMOTION_HUE.neutral;
  #look = { x: 0, y: 0 };
  #lookTarget = { x: 0, y: 0 };
  #speaking = false;
  readonly #onChange = (): void => {
    void this.load();
  };
  readonly #onFit = (): void => {
    this.setFit(loadFit(windowStorage()));
  };

  private constructor(host: HTMLElement, fit: PictureFit) {
    this.#root = document.createElement("div");
    this.#root.className = "portrait";
    this.#root.style.cssText =
      "position:absolute;inset:0;display:flex;align-items:center;justify-content:center;" +
      "perspective:900px;pointer-events:none";
    this.#glow = document.createElement("div");
    this.#glow.style.cssText = "position:absolute;inset:8%;border-radius:50%;filter:blur(40px)";
    this.#image = document.createElement("img");
    this.#image.alt = "";
    this.#image.draggable = false;
    this.#image.style.cssText =
      "position:relative;max-width:92%;max-height:92%;transform-origin:50% 100%;will-change:transform";
    this.#dots = document.createElement("div");
    this.#dots.className = "portrait-thinking";
    this.#dots.textContent = "• • •";
    this.#dots.style.cssText =
      "position:absolute;top:6%;left:50%;transform:translateX(-50%);font-size:22px;" +
      "letter-spacing:4px;opacity:0;transition:opacity .2s;color:#cfe0ff";
    this.#root.append(this.#glow, this.#image, this.#dots);
    host.append(this.#root);
    this.setFit(fit);
    pictureChanged.addEventListener("change", this.#onChange);
    pictureChanged.addEventListener("fit", this.#onFit);
  }

  static create(host: HTMLElement): Promise<PortraitRenderer> {
    return Promise.resolve(new PortraitRenderer(host, loadFit(windowStorage())));
  }

  /** Сохранённая картинка или стандартный силуэт; повторный вызов — после смены картинки. */
  async load(): Promise<void> {
    const picture = await loadPicture();
    const next = picture === null ? null : URL.createObjectURL(picture);
    await new Promise<void>((resolve) => {
      this.#image.onload = () => {
        resolve();
      };
      this.#image.onerror = () => {
        // Битый файл не ломает окошко: показываем силуэт.
        this.#image.onerror = null;
        this.#image.src = silhouette;
        resolve();
      };
      this.#image.src = next ?? DEFAULT_PICTURE;
    });
    if (this.#url !== null) URL.revokeObjectURL(this.#url);
    this.#url = next;
  }

  /** «Вписать целиком» или «заполнить окошко». */
  setFit(fit: PictureFit): void {
    const cover = fit === "cover";
    this.#image.style.objectFit = cover ? "cover" : "contain";
    this.#image.style.width = cover ? "100%" : "auto";
    this.#image.style.height = cover ? "100%" : "auto";
    this.#image.style.maxWidth = cover ? "100%" : "92%";
    this.#image.style.maxHeight = cover ? "100%" : "92%";
  }

  setEmotion(emotion: Emotion, intensity: number): void {
    this.#targetHue = mixHue(EMOTION_HUE.neutral, EMOTION_HUE[emotion], intensity);
  }

  nod(): void {
    this.#pulse = Math.max(this.#pulse, 0.5);
  }

  gesture(): void {
    this.#pulse = Math.max(this.#pulse, 0.8);
  }

  setSpeaking(speaking: boolean): void {
    this.#speaking = speaking;
  }

  setMouth(openness: number): void {
    this.#mouthTarget = Math.min(1, Math.max(0, openness));
  }

  setMouthForm(): void {
    // Формы рта у картинки нет: только громкость.
  }

  attend(): void {
    this.#attention = 1;
    this.#pulse = 1;
  }

  lookAt(x: number, y: number): void {
    this.#lookTarget = { x, y };
  }

  react(reaction: AvatarReaction): void {
    this.#dots.style.opacity = reaction === "thinking" ? "0.85" : "0";
  }

  update(deltaMs: number): void {
    const dt = Math.min(0.1, deltaMs / 1000);
    this.#time += dt;
    this.#mouth = approach(
      this.#mouth,
      this.#mouthTarget,
      this.#mouthTarget > this.#mouth ? 25 : 8,
      dt,
    );
    this.#pulse = approach(this.#pulse, 0, 3, dt);
    this.#attention = approach(this.#attention, 0, 0.8, dt);
    this.#hue = mixHue(this.#hue, this.#targetHue, dt * 2);
    this.#look.x = approach(this.#look.x, this.#lookTarget.x, 3, dt);
    this.#look.y = approach(this.#look.y, this.#lookTarget.y, 3, dt);
    this.#draw();
  }

  contains(x: number, y: number): boolean {
    const box = this.#image.getBoundingClientRect();
    const host = this.#root.getBoundingClientRect();
    const px = x + host.left;
    const py = y + host.top;
    return px >= box.left && px <= box.right && py >= box.top && py <= box.bottom;
  }

  resize(): void {
    // Размер ведёт CSS: картинка вписывается в окошко сама.
  }

  dispose(): void {
    pictureChanged.removeEventListener("change", this.#onChange);
    pictureChanged.removeEventListener("fit", this.#onFit);
    if (this.#url !== null) URL.revokeObjectURL(this.#url);
    this.#root.remove();
  }

  #draw(): void {
    const pose = portraitPose({
      time: this.#time,
      mouth: this.#mouth,
      pulse: this.#pulse,
      lookX: this.#look.x,
      lookY: this.#look.y,
    });
    this.#image.style.transform =
      `translateY(${pose.lift.toFixed(2)}px) rotate(${pose.rotate.toFixed(3)}deg) ` +
      `rotateX(${pose.tiltX.toFixed(2)}deg) rotateY(${pose.tiltY.toFixed(2)}deg) ` +
      `scaleY(${pose.scaleY.toFixed(4)})`;
    const talk = this.#speaking ? this.#mouth * 0.35 : 0;
    const alpha = Math.min(0.75, 0.18 + talk + this.#attention * 0.45);
    const hue = Math.round(this.#hue);
    this.#glow.style.background = `radial-gradient(closest-side, hsla(${String(hue)}, 85%, 60%, ${alpha.toFixed(3)}), transparent)`;
    this.#image.style.filter =
      this.#attention > 0.01
        ? `brightness(${(1 + this.#attention * 0.35).toFixed(3)}) drop-shadow(0 0 ${(this.#attention * 24).toFixed(1)}px hsl(${String(hue)} 90% 70%))`
        : "";
  }
}
