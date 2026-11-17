/**
 * Сторож «Разума» (COMPANION.md, часть III): раз в секунду сверяет состояние тела и решений с правилами
 * и, если правило нарушено, предлагает починку. Не управляет поведением — вмешивается только при беде:
 * координаты вне экрана, падение без конца, застрял в пути или портале, «держат» без мыши, пропал при
 * показанном слое, метания и болтливость. Чистый класс — проверяется тестами; чинит контроллер.
 */
export type Fix = "land" | "arrive" | "release" | "hide" | "calm" | "hush";

/** Что сторож видит в кадре. */
export interface Snapshot {
  phase: string;
  x: number;
  y: number;
  /** Экран слоя (CSS-пиксели). */
  screen: { x: number; y: number; w: number; h: number };
  /** Слой показан (персонаж должен быть на экране). */
  shown: boolean;
  /** Мышь сейчас держит персонажа. */
  holding: boolean;
  /** Текущее действие «Разума». */
  activity: string;
}

/** Сколько секунд фаза может длиться, прежде чем считаться застрявшей. */
const STUCK_S: Readonly<Record<string, number>> = {
  fall: 6,
  walk: 25,
  jump: 4,
  bolt: 4,
  climb: 40,
  portal_out: 4,
  portal_in: 4,
};
const HELD_ALONE_S = 1;
const HIDDEN_S = 3;
const MAX_SWITCHES_PER_MIN = 12;
const MAX_LINES_PER_5_MIN = 6;
const CALM_S = 60;
const HUSH_S = 120;
const MARGIN = 300;

export class Sanity {
  #checkAt = 0;
  #phase = "";
  #phaseSince = 0;
  #hiddenSince: number | null = null;
  #heldAloneSince: number | null = null;
  #activity = "";
  #switches: number[] = [];
  #lines: number[] = [];
  #calmUntil = 0;
  #hushUntil = 0;
  /** Сколько раз чинил — для журнала и тестов. */
  repairs = 0;

  /** Успокоен сторожем до этого момента (с). */
  calm(now: number): boolean {
    return now < this.#calmUntil;
  }

  /** Голос заглушён сторожем до этого момента (с). */
  hushed(now: number): boolean {
    return now < this.#hushUntil;
  }

  /** Сказана своя фраза. */
  noteLine(now: number): void {
    this.#lines = [...this.#lines.filter((t) => now - t < 300), now];
  }

  /** Раз в кадр; проверки — раз в секунду. Вернёт починки (обычно пусто). */
  observe(s: Snapshot, now: number): Fix[] {
    this.#track(s, now);
    if (now < this.#checkAt) return [];
    this.#checkAt = now + 1;
    const fixes = [...this.#body(s, now), ...this.#mind(now)];
    this.repairs += fixes.length;
    return fixes;
  }

  #track(s: Snapshot, now: number): void {
    if (s.phase !== this.#phase) {
      this.#phase = s.phase;
      this.#phaseSince = now;
    }
    if (s.activity !== this.#activity) {
      this.#activity = s.activity;
      this.#switches = [...this.#switches.filter((t) => now - t < 60), now];
    }
    this.#hiddenSince = s.shown && s.phase === "hidden" ? (this.#hiddenSince ?? now) : null;
    this.#heldAloneSince = s.phase === "held" && !s.holding ? (this.#heldAloneSince ?? now) : null;
  }

  #body(s: Snapshot, now: number): Fix[] {
    if (!Number.isFinite(s.x) || !Number.isFinite(s.y) || this.#offScreen(s)) return ["land"];
    if (this.#heldAloneSince !== null && now - this.#heldAloneSince > HELD_ALONE_S)
      return ["release"];
    if (this.#hiddenSince !== null && now - this.#hiddenSince > HIDDEN_S) {
      this.#hiddenSince = now;
      return ["arrive"];
    }
    const limit = STUCK_S[s.phase];
    if (limit === undefined || now - this.#phaseSince <= limit) return [];
    this.#phaseSince = now;
    return [s.phase === "portal_in" ? "hide" : "land"];
  }

  #mind(now: number): Fix[] {
    const fixes: Fix[] = [];
    if (this.#switches.length > MAX_SWITCHES_PER_MIN && !this.calm(now)) {
      this.#calmUntil = now + CALM_S;
      this.#switches = [];
      fixes.push("calm");
    }
    if (this.#lines.length > MAX_LINES_PER_5_MIN && !this.hushed(now)) {
      this.#hushUntil = now + HUSH_S;
      this.#lines = [];
      fixes.push("hush");
    }
    return fixes;
  }

  #offScreen(s: Snapshot): boolean {
    if (s.phase === "hidden" || s.phase === "held") return false;
    const { screen } = s;
    return (
      s.x < screen.x - MARGIN ||
      s.x > screen.x + screen.w + MARGIN ||
      s.y < screen.y - MARGIN ||
      s.y > screen.y + screen.h + MARGIN
    );
  }
}
