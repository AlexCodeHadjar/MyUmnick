/**
 * Плеер радио главного окна (ADR-0049). Поток играет `<audio>`; если станция отдаёт CORS, звук идёт через
 * `AnalyserNode` — рот спутника поёт по настоящей громкости. Без CORS элемент, подключённый к AudioContext,
 * молчит, поэтому для такой станции берётся отдельный элемент без анализа и псевдоритм.
 */
import {
  loadRadio,
  saveRadio,
  station as makeStation,
  stationsOf,
  step,
  type RadioCommand,
  type RadioFeed,
  type RadioMode,
  type RadioSettings,
  type Station,
} from "./stations";

const START_TIMEOUT_MS = 12_000;

export class RadioPlayer {
  readonly #storage: Storage | undefined;
  #settings: RadioSettings;
  #mode: RadioMode = "off";
  #audio: HTMLAudioElement | null = null;
  #ctx: AudioContext | null = null;
  #analyser: AnalyserNode | null = null;
  #data = new Uint8Array(512);
  /** Номер попытки: ответ старой загрузки не перебивает новую станцию. */
  #attempt = 0;
  readonly #listeners = new Set<() => void>();

  constructor(storage: Storage | undefined) {
    this.#storage = storage;
    this.#settings = loadRadio(storage);
  }

  get mode(): RadioMode {
    return this.#mode;
  }

  get stations(): Station[] {
    return stationsOf(this.#settings);
  }

  get index(): number {
    return this.#settings.index;
  }

  get volume(): number {
    return this.#settings.volume;
  }

  get station(): Station | undefined {
    return this.stations[this.#settings.index];
  }

  /** Подписка на смену состояния; возвращает отписку. */
  subscribe(listener: () => void): () => void {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  command(command: RadioCommand): void {
    if (command === "toggle") this.toggle();
    else if (command === "next") this.select(step(this.index, 1, this.stations.length));
    else if (command === "prev") this.select(step(this.index, -1, this.stations.length));
    else this.off();
  }

  toggle(): void {
    if (this.#mode === "playing" || this.#mode === "loading") this.pause();
    else void this.play();
  }

  select(index: number): void {
    this.#update({ ...this.#settings, index });
    void this.play();
  }

  setVolume(volume: number): void {
    this.#update({ ...this.#settings, volume: Math.min(1, Math.max(0, volume)) });
    if (this.#audio !== null) this.#audio.volume = this.#settings.volume;
  }

  /** Своя станция; неверная ссылка — `false`. */
  add(name: string, url: string): boolean {
    const made = makeStation(name, url);
    if (made === null) return false;
    const custom = [...this.#settings.custom, made];
    this.#update({
      ...this.#settings,
      custom,
      index: stationsOf({ ...this.#settings, custom }).length - 1,
    });
    void this.play();
    return true;
  }

  async play(): Promise<void> {
    const chosen = this.station;
    if (chosen === undefined) return;
    const attempt = ++this.#attempt;
    this.#stopAudio();
    this.#set("loading");
    const played = (await this.#start(chosen.url, true)) || (await this.#start(chosen.url, false));
    if (attempt !== this.#attempt) return;
    this.#set(played ? "playing" : "failed");
  }

  pause(): void {
    this.#attempt++;
    this.#audio?.pause();
    this.#set("paused");
  }

  off(): void {
    this.#attempt++;
    this.#stopAudio();
    this.#set("off");
  }

  /** Громкость 0…1: по анализатору или псевдоритм, если поток без CORS. */
  level(time: number): number {
    if (this.#mode !== "playing") return 0;
    const analyser = this.#analyser;
    if (analyser === null) return 0.3 + 0.4 * Math.abs(Math.sin(time * 7.3) * Math.sin(time * 2.1));
    analyser.getByteTimeDomainData(this.#data);
    let sum = 0;
    for (const value of this.#data) sum += ((value - 128) / 128) ** 2;
    // Громкость элемента действует до анализатора: делим на неё — тихое радио не даёт «немой» рот.
    const volume = Math.max(0.15, this.#settings.volume);
    return Math.min(1, (Math.sqrt(sum / this.#data.length) * 4) / volume);
  }

  feed(time: number): RadioFeed {
    return { mode: this.#mode, title: this.station?.name ?? "", level: this.level(time) };
  }

  dispose(): void {
    this.off();
    void this.#ctx?.close();
    this.#ctx = null;
  }

  async #start(url: string, cors: boolean): Promise<boolean> {
    const audio = new Audio();
    audio.preload = "none";
    audio.volume = this.#settings.volume;
    if (cors) audio.crossOrigin = "anonymous";
    audio.src = url;
    this.#audio = audio;
    this.#analyser = cors ? this.#analyse(audio) : null;
    // Поток молчит дольше 12 с — «волна пропала», а не вечная «настройка».
    const timeout = new Promise<boolean>((resolve) => setTimeout(resolve, START_TIMEOUT_MS, false));
    const started = await Promise.race([
      audio.play().then(
        () => true,
        () => false,
      ),
      timeout,
    ]);
    if (!started && this.#audio === audio) this.#stopAudio();
    return started;
  }

  #analyse(audio: HTMLAudioElement): AnalyserNode | null {
    try {
      this.#ctx ??= new AudioContext();
      void this.#ctx.resume();
      const analyser = this.#ctx.createAnalyser();
      analyser.fftSize = 512;
      this.#ctx.createMediaElementSource(audio).connect(analyser).connect(this.#ctx.destination);
      return analyser;
    } catch {
      return null;
    }
  }

  #stopAudio(): void {
    const audio = this.#audio;
    if (audio === null) return;
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    this.#audio = null;
    this.#analyser = null;
  }

  #update(next: RadioSettings): void {
    this.#settings = next;
    saveRadio(this.#storage, next);
    this.#emit();
  }

  #set(mode: RadioMode): void {
    this.#mode = mode;
    this.#emit();
  }

  #emit(): void {
    for (const listener of this.#listeners) listener();
  }
}
