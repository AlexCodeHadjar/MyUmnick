import type { Phase } from "../body";
import { DIVERSION } from "../settings";
export type Diversion = "peek" | "knock" | "read" | "draw" | "juggle" | "bug" | "trip";
export interface Scene {
  kind: Diversion;
  progress: number;
}
const hobbies = ["knock", "read", "draw", "juggle", "bug"] as const;

export class Diversions {
  readonly #random: () => number;
  #next = 0;
  #tripAt = -Infinity;
  #phase: Phase = "hidden";
  #scene: { kind: Diversion; start: number; duration: number } | null = null;
  constructor(random = Math.random) {
    this.#random = random;
  }

  frame(now: number, phase: Phase, free: boolean, windowEdge: boolean): Scene | null {
    const entered = this.#phase !== phase;
    this.#phase = phase;
    if (!free || (phase !== "rest" && phase !== "walk")) {
      this.#scene = null;
      this.#next = now + DIVERSION.idleMs;
      return null;
    }
    if (entered) {
      this.#scene = null;
      this.#next = now + DIVERSION.idleMs;
      if (
        phase === "walk" &&
        now - this.#tripAt >= DIVERSION.cooldown &&
        this.#random() < DIVERSION.tripChance
      ) {
        this.#scene = { kind: "trip", start: now, duration: DIVERSION.tripMs };
        this.#tripAt = now;
      }
    }
    if (phase === "rest" && now >= this.#next) {
      this.#next = now + DIVERSION.cooldown;
      if (this.#random() < DIVERSION.chance) {
        const kind = windowEdge
          ? "peek"
          : (hobbies[Math.floor(this.#random() * hobbies.length)] ?? "read");
        this.#scene = { kind, start: now, duration: kind === "knock" ? 2000 : 4200 };
      }
    }
    if (!this.#scene) return null;
    const progress = (now - this.#scene.start) / this.#scene.duration;
    if (progress >= 1) {
      this.#scene = null;
      return null;
    }
    return { kind: this.#scene.kind, progress };
  }
}
