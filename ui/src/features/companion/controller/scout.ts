/**
 * Органы чувств спутника в мире (BEHAVIOR §4–§6, §11): какая программа активна, какая вкладка выбрана,
 * какие значки видны на рабочем столе, что играет в системе. Только наблюдение — решения принимает «Разум».
 */
import type { Brain } from "../body";
import {
  siteOf,
  keepWatching,
  mediaVideo,
  musicPlaying,
  loudMoment,
  pickMedia,
  topicOf,
  watching,
  type Media,
  type RemarkTopic,
  type Target,
} from "../senses";
import type { Focus, Rect } from "../space";
import type { Ports } from "./ports";

const TAB_EVERY_MS = 15_000;
const MEDIA_EVERY_MS = 2000;
const NONE: Media = { state: "none", app: "" };

/** Смена состояния того, что играет: для реплик «пауза» / «продолжаем». */
export type MediaChange = "paused" | "resumed" | "music" | "loud" | null;

export class Scout {
  readonly #ports: Ports;
  readonly #brain: Brain;
  readonly #toCss: (rect: Rect) => Rect;
  topic: RemarkTopic = "other";
  desktop = false;
  icons: Target[] = [];
  #app = "";

  /** Программа в фокусе (имя exe без пути) — для чек-листа. */
  get app(): string {
    return this.#app;
  }
  #tab: string | null = null;
  #tabAt = 0;
  #media: Media = NONE;
  #mediaAt = 0;
  #mediaBusy = false;
  #pausedSince = 0;
  #music = false;
  /** Сглаженная громкость источника видео — для «громкого места». */
  #avgPeak = 0;

  /** `toCss` — физические пиксели экрана → CSS-пиксели слоя (монитор и масштаб знает присутствие). */
  constructor(ports: Ports, brain: Brain, toCss: (rect: Rect) => Rect) {
    this.#ports = ports;
    this.#brain = brain;
    this.#toCss = toCss;
  }

  /** Сменилось активное окно. Вернёт `true`, если сменилась тема программы. */
  focus(focus: Focus): boolean {
    this.#app = focus.kind === "desktop" ? "" : focus.app;
    const next = topicOf(this.#app, focus.kind === "desktop");
    void this.#enterDesktop(focus.kind === "desktop");
    if (next === this.topic) return false;
    this.topic = next;
    this.#tab = null;
    this.#tabAt = 0;
    return true;
  }

  async refreshIcons(): Promise<void> {
    const found = await this.#ports.targets();
    if (!this.desktop) return;
    this.icons = found
      .filter((one) => one.kind === "item")
      .map((one) => ({ ...one, rect: this.#toCss(one.rect) }));
    this.#brain.setIcons(this.icons.map((one) => one.rect));
  }

  /** Видимые цели активного окна в CSS-пикселях слоя. */
  async targets(): Promise<Target[]> {
    const found = await this.#ports.targets();
    return found.map((one) => ({ ...one, rect: this.#toCss(one.rect) }));
  }

  /** Названия вкладок браузера — для шуток про сайты. */
  async tabs(): Promise<string[]> {
    const found = await this.#ports.targets();
    return found.filter((one) => one.kind === "tab").map((one) => one.name);
  }

  /**
   * Идёт ли видео (раз в кадр). Полный экран считается только у браузера, плеера, игры или незнакомой
   * программы: развёрнутые на весь экран чат и редактор — обычные окна.
   */
  #copiedUntil = 0;
  textCopied(now: number): void {
    this.#copiedUntil = now + 12_000;
  }
  working(now: number): boolean {
    return (
      (now < this.#copiedUntil && this.topic !== "game" && this.topic !== "video") ||
      this.topic === "code" ||
      this.topic === "chat" ||
      this.topic === "desktop" ||
      (this.topic === "browser" && this.#tab !== null && siteOf(this.#tab) === "ai")
    );
  }
  video(now: number, fullscreenRaw: boolean): { video: boolean; fullscreen: boolean } {
    this.#refreshTab(now);
    const topic = this.topic;
    if (this.working(now)) return { video: false, fullscreen: false };
    const wide = topic === "browser" || topic === "video" || topic === "game" || topic === "other";
    const fullscreen = wide && fullscreenRaw;
    // Начать — только по сильному признаку (живой тест 2026-11-17: звук фоновой вкладки браузера
    // сажал смотреть «фильм» на Википедии): плеер, полный экран или видеосайт, где правда играет.
    const sign = watching({ app: this.#app, topic, fullscreen, tab: this.#tab });
    const sounding = mediaVideo(this.#media, this.#tab) && this.#media.state === "playing";
    const start = sign && (topic !== "browser" || sounding);
    const playing = keepWatching({
      media: this.#media,
      pausedS: this.#media.state === "paused" ? (now - this.#pausedSince) / 1000 : 0,
      tab: this.#tab,
      focusVideo: start,
      already: this.#brain.watching,
    });
    return { video: start || playing, fullscreen };
  }

  /** Раз в 2 с — что играет в системе; `onChange` — пауза или продолжение. */
  pollMedia(now: number, onChange: (change: MediaChange) => void): void {
    if (this.#mediaBusy || now < this.#mediaAt) return;
    this.#mediaAt = now + MEDIA_EVERY_MS;
    this.#mediaBusy = true;
    void this.#ports.media().then((list) => {
      this.#mediaBusy = false;
      const before = this.#media.state;
      this.#media = pickMedia(list, this.#tab);
      // Заиграла музыка в плеере (этап 5) — сказать «музыка!» и потанцевать.
      const peak = this.#media.peak ?? 0;
      if (this.#brain.watching && loudMoment(peak, this.#avgPeak)) onChange("loud");
      this.#avgPeak = this.#avgPeak * 0.8 + peak * 0.2;
      const music = musicPlaying(list);
      if (music && !this.#music) onChange("music");
      this.#music = music;
      const state = this.#media.state;
      if (state === "paused" && before !== "paused") this.#pausedSince = performance.now();
      if (before === "playing" && state === "paused") onChange("paused");
      else if (before === "paused" && state === "playing") onChange("resumed");
    });
  }

  async #enterDesktop(desktop: boolean): Promise<void> {
    this.desktop = desktop;
    if (desktop) {
      await this.refreshIcons();
      return;
    }
    this.icons = [];
    this.#brain.setIcons([]);
  }

  /** Название выбранной вкладки браузера — раз в 15 с, пока браузер активен. */
  #refreshTab(now: number): void {
    if (this.topic !== "browser" || now < this.#tabAt) return;
    this.#tabAt = now + TAB_EVERY_MS;
    void this.#ports.targets().then((found) => {
      if (this.topic !== "browser") return;
      this.#tab = found.find((one) => one.kind === "tab" && one.selected === true)?.name ?? null;
    });
  }
}
