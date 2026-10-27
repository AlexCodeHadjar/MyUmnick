/**
 * Тексты статус-бара. Транспорт при потере ядра чередует «connecting» и «closed» каждые
 * полсекунды–пять секунд; пользователю это одно состояние — «нет связи, переподключаюсь».
 * Различаем только первое подключение после запуска и потерю уже бывшей связи.
 */
import type { BackendState, ConnectionState } from "../core";

export type Tone = "ok" | "wait" | "bad" | "off";

export interface Indicator {
  label: string;
  tone: Tone;
}

export function connectionIndicator(state: ConnectionState, everOpen: boolean): Indicator {
  switch (state) {
    case "open":
      return { label: "на связи", tone: "ok" };
    case "replaced":
      return { label: "открыто другое окно", tone: "off" };
    case "connecting":
    case "closed":
      return everOpen
        ? { label: "нет связи — переподключаюсь", tone: "bad" }
        : { label: "подключение…", tone: "wait" };
  }
}

const BACKEND: Record<BackendState | "unknown", Indicator> = {
  loading: { label: "загрузка…", tone: "wait" },
  ready: { label: "готов", tone: "ok" },
  failed: { label: "ошибка", tone: "bad" },
  unknown: { label: "—", tone: "off" },
};

/** Состояние бэкенда, пока связи нет, — устаревшее: показываем «—», а не последнее известное. */
export function backendIndicator(state: BackendState | "unknown", online: boolean): Indicator {
  return BACKEND[online ? state : "unknown"];
}
