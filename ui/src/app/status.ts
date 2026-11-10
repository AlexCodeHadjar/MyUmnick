/**
 * Тексты статус-бара. Транспорт при потере ядра чередует «connecting» и «closed» каждые
 * полсекунды–пять секунд; пользователю это одно состояние — «нет связи, переподключаюсь».
 * Различаем только первое подключение после запуска и потерю уже бывшей связи.
 */
import { messagesFor, type BackendState, type ConnectionState, type Messages } from "../core";

export type Tone = "ok" | "wait" | "bad" | "off";

export interface Indicator {
  label: string;
  tone: Tone;
}

export function connectionIndicator(
  state: ConnectionState,
  everOpen: boolean,
  t: Messages = messagesFor("ru"),
): Indicator {
  switch (state) {
    case "open":
      return { label: t.status.online, tone: "ok" };
    case "replaced":
      return { label: t.status.replaced, tone: "off" };
    case "connecting":
    case "closed":
      return everOpen
        ? { label: t.status.reconnecting, tone: "bad" }
        : { label: t.status.connecting, tone: "wait" };
  }
}

function backendIndicators(t: Messages): Record<BackendState | "unknown", Indicator> {
  return {
    loading: { label: t.status.loading, tone: "wait" },
    ready: { label: t.status.ready, tone: "ok" },
    failed: { label: t.status.failed, tone: "bad" },
    unknown: { label: "—", tone: "off" },
  };
}

/** Состояние бэкенда, пока связи нет, — устаревшее: показываем «—», а не последнее известное. */
export function backendIndicator(
  state: BackendState | "unknown",
  online: boolean,
  t: Messages = messagesFor("ru"),
): Indicator {
  return backendIndicators(t)[online ? state : "unknown"];
}

/** Подсказка над счётчиком: кто и что написал; решение — за ведущим (`/пауза`, FR-31). */
export function blockedDetails(blocked: readonly { author: string; text: string }[]): string {
  return blocked.map(({ author, text }) => `${author}: ${text}`).join("\n");
}
