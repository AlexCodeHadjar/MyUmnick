/**
 * Форма рта по спектру звучащего сигнала (ADR-0023, S-18.3). Громкость говорит, насколько рот
 * открыт, а гласную видно по тому, где лежит её энергия: у «о» и «у» она внизу, у «а» посередине,
 * у «э» и «и» заметна сверху. Считается из того же буфера, что звучит, поэтому не отстаёт от звука
 * и не зависит от движка речи.
 */

/** Границы полос, Гц: первая и вторая форманты русских гласных. */
const LOW_HZ = 200;
const MID_HZ = 650;
const HIGH_HZ = 1500;
const TOP_HZ = 3200;
/** Выше — шипящие и свистящие: у «с», «ш» зубы сомкнуты, хотя звук громкий. */
const HISS_FROM_HZ = 4000;
const HISS_TO_HZ = 8000;
/** Рот при шипящей: почти закрыт, но не схлопнут, между гласными нет щелчка. */
const HISS_OPENNESS = 0.3;
/** Даже «и» с минимумом энергии в средней полосе открывает рот наполовину. */
const MIN_OPENNESS = 0.5;
/** Доля верхней полосы, с которой рот уже растянут полностью: в речи она всегда меньше нижней. */
const WIDE_AT_SHARE = 1 / 3;

export interface MouthShape {
  /** Форма: -1 — округлён («о», «у»), 0 — нейтрально («а»), 1 — растянут («э», «и»). */
  form: number;
  /** На что умножить открытие по громкости, 0…1. */
  openness: number;
}

export const NEUTRAL_SHAPE: MouthShape = { form: 0, openness: 1 };

/** Амплитуда полосы: корень сглаживает разницу формант, в речи вторая намного тише первой. */
function band(spectrumDb: Float32Array, binHz: number, fromHz: number, toHz: number): number {
  const last = Math.min(spectrumDb.length, Math.ceil(toHz / binHz));
  let power = 0;
  for (let i = Math.floor(fromHz / binHz); i < last; i++) {
    const db = spectrumDb[i] ?? -Infinity;
    if (Number.isFinite(db)) {
      power += 10 ** (db / 10);
    }
  }
  return Math.sqrt(power);
}

/** Спектр в дБ (`getFloatFrequencyData`) → форма рта; пустой спектр — откат к громкости. */
export function mouthShape(spectrumDb: Float32Array, binHz: number): MouthShape {
  const low = band(spectrumDb, binHz, LOW_HZ, MID_HZ);
  const mid = band(spectrumDb, binHz, MID_HZ, HIGH_HZ);
  const high = band(spectrumDb, binHz, HIGH_HZ, TOP_HZ);
  const voiced = low + mid + high;
  if (voiced <= 0) {
    return NEUTRAL_SHAPE;
  }
  if (band(spectrumDb, binHz, HISS_FROM_HZ, HISS_TO_HZ) > voiced) {
    return { form: 0, openness: HISS_OPENNESS };
  }
  const wide = Math.min(1, high / voiced / WIDE_AT_SHARE);
  const round = (low / voiced) * (1 - wide);
  return { form: wide - round, openness: MIN_OPENNESS + (1 - MIN_OPENNESS) * (mid / voiced) };
}

/** Сглаживание формы: быстрее смены слогов, но без дрожи от кадра к кадру. */
const FORM_TAU_MS = 60;

export class FormFollower {
  #value = 0;

  /** Новая форма за `deltaMs`; вне речи (`null`) рот возвращается к нейтральной. */
  update(form: number | null, deltaMs: number): number {
    const k = 1 - Math.exp(-Math.max(0, deltaMs) / FORM_TAU_MS);
    this.#value += ((form ?? 0) - this.#value) * k;
    return this.#value;
  }
}
