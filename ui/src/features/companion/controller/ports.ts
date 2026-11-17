/**
 * Порты оболочки для спутника (SOLID, инверсия зависимостей): классы контроллера знают только этот
 * интерфейс, а не Tauri. Реализация — `tauriPorts`; в тестах — подделка.
 */
import { invoke } from "@tauri-apps/api/core";

import type { Media, Target } from "../senses";
import type { Rect, World } from "../space";

export interface Ports {
  /** Показать или спрятать слой спутника. */
  setVisible(visible: boolean): Promise<void>;
  /** Где персонаж (клики по нему не уходят сквозь слой) и держат ли его мышью. */
  hit(hit: Rect | null, capture: boolean): void;
  /** Окно, на котором он сидит: оболочка следит за его сдвигом. */
  attach(host: number | null): void;
  /** Видимые элементы активного окна или значки рабочего стола (ADR-0048, ADR-0052). */
  targets(): Promise<Target[]>;
  /** Что играет в системе (ADR-0052). */
  media(): Promise<Media[]>;
  /** Картина окон сейчас (первый кадр после загрузки слоя). */
  world(): Promise<World | null>;
  /** Открыть главное окно. */
  showMain(): void;
}

export const tauriPorts: Ports = {
  async setVisible(visible) {
    await invoke("companion_set", { visible });
  },
  hit(hit, capture) {
    void invoke("companion_hit", { hit, capture });
  },
  attach(host) {
    void invoke("companion_attach", { host });
  },
  targets: () => invoke<Target[]>("companion_targets").catch((): Target[] => []),
  media: () => invoke<Media[]>("companion_media").catch((): Media[] => []),
  world: () => invoke<World | null>("companion_world").catch(() => null),
  showMain() {
    void invoke("main_show");
  },
};
