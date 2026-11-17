/**
 * Голос спутника (MIND §3.5): все его фразы — через один регулятор. Прямые ответы (гладят, трясут) —
 * сразу; реакции — не чаще раза в 12 с; «сам по себе» — по жетонам (2, новый раз в 90 с) и не чаще раза
 * в 25 с. Устаревшее выбрасывается, очередь — не больше 3. Две фразы подряд из разных мест больше не
 * вылетают.
 */
export type VoiceKind = "direct" | "reaction" | "ambient";

const RANK: Record<VoiceKind, number> = { direct: 0, reaction: 1, ambient: 2 };
const TTL_S: Record<VoiceKind, number> = { direct: 3, reaction: 6, ambient: 20 };
const GAP_S: Record<VoiceKind, number> = { direct: 1.5, reaction: 12, ambient: 25 };
const TOKENS = 2;
const REFILL_S = 90;
const QUEUE = 3;

interface Line {
  text: string;
  kind: VoiceKind;
  at: number;
}

export interface VoiceState {
  /** Говорит ассистент, держат мышью, персонажа нет на экране — молчит совсем. */
  blocked: boolean;
  /** Висит облачко — ждут все, кроме прямых ответов. */
  bubble: boolean;
}

export class Voice {
  /** «Спокойнее»: жетоны «сам по себе» копятся втрое дольше, реакции — вдвое реже. */
  calm = false;
  #queue: Line[] = [];
  #lastAt = -Infinity;
  readonly #lastKind = new Map<VoiceKind, number>();
  #tokens = TOKENS;
  #refilledAt = 0;

  offer(text: string, kind: VoiceKind, now: number): void {
    if (text === "") return;
    this.#queue = [...this.#queue.filter((one) => one.text !== text), { text, kind, at: now }]
      .sort((a, b) => RANK[a.kind] - RANK[b.kind] || a.at - b.at)
      .slice(0, QUEUE);
  }

  /** Секунд с последней сказанной фразы. */
  quietFor(now: number): number {
    return now - this.#lastAt;
  }

  /** Есть ли жетон для фразы «сам по себе» — арбитру: стоит ли выбирать «поговорить». */
  canChat(now: number): boolean {
    this.#refill(now);
    return this.#tokens >= 1 && now - this.#lastAt >= GAP_S.ambient;
  }

  /** Следующая фраза, которую можно сказать сейчас, или `null`. */
  next(now: number, state: VoiceState): string | null {
    this.#refill(now);
    this.#queue = this.#queue.filter((one) => now - one.at <= TTL_S[one.kind]);
    if (state.blocked) return null;
    const line = this.#queue.find((one) => this.#allowed(one, now, state.bubble));
    if (line === undefined) return null;
    this.#queue = this.#queue.filter((one) => one !== line);
    if (line.kind === "ambient") this.#tokens -= 1;
    this.#lastAt = now;
    this.#lastKind.set(line.kind, now);
    return line.text;
  }

  #allowed(line: Line, now: number, bubble: boolean): boolean {
    const sinceKind = now - (this.#lastKind.get(line.kind) ?? -Infinity);
    if (line.kind === "direct") return sinceKind >= GAP_S.direct;
    if (bubble || now - this.#lastAt < 4) return false;
    if (line.kind === "reaction") return sinceKind >= GAP_S.reaction * (this.calm ? 2 : 1);
    // «Сам по себе» — после любой фразы не раньше 25 с и только с жетоном.
    return now - this.#lastAt >= GAP_S.ambient && this.#tokens >= 1;
  }

  #refill(now: number): void {
    const every = REFILL_S * (this.calm ? 3 : 1);
    const steps = Math.floor((now - this.#refilledAt) / every);
    if (steps <= 0) return;
    this.#tokens = Math.min(TOKENS, this.#tokens + steps);
    this.#refilledAt += steps * every;
  }
}
