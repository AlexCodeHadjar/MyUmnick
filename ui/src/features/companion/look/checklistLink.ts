/**
 * Чек-лист в главном окне (просьба пользователя 2026-11-18): считает его слой спутника (там «Разум» и
 * датчики), главное окно только показывает. Связь — общий канал окон `vtuber-character`: главное окно раз
 * в 2 с просит строки, спутник шлёт их два раза в секунду, пока просьбы идут.
 */
import { characterChannel } from "../../avatar/portrait/picture";
import type { Checklist } from "./checklist";

const PING_MS = 2000;
const SEND_MS = 500;
/** Просьб нет дольше — главное окно закрыли или закрыли панель: перестать слать. */
const STALE_MS = 5000;

interface Ask {
  kind: "checklist";
}
interface Rows {
  kind: "checklist-rows";
  rows: Checklist | null;
}

function kindOf(data: unknown): string | null {
  if (typeof data !== "object" || data === null || !("kind" in data)) return null;
  return typeof data.kind === "string" ? data.kind : null;
}

/** Строки от слоя спутника: вид сообщения и четыре списка (граница между окнами). */
function isRows(data: unknown): data is Rows {
  if (kindOf(data) !== "checklist-rows" || typeof data !== "object" || data === null) return false;
  if (!("rows" in data)) return false;
  if (data.rows === null) return true;
  if (typeof data.rows !== "object") return false;
  const rows = data.rows;
  return ["sensors", "actions", "reactions", "others"].every(
    (key) => key in rows && Array.isArray(Reflect.get(rows, key)),
  );
}

/** Слой спутника: отвечать строками чек-листа, пока главное окно просит. Вернёт отписку. */
export function serveChecklist(build: () => Checklist | null): () => void {
  let askedAt = -Infinity;
  const onMessage = (event: MessageEvent): void => {
    if (kindOf(event.data) === "checklist") askedAt = performance.now();
  };
  const timer = setInterval(() => {
    if (performance.now() - askedAt > STALE_MS) return;
    const message: Rows = { kind: "checklist-rows", rows: build() };
    characterChannel?.postMessage(message);
  }, SEND_MS);
  characterChannel?.addEventListener("message", onMessage);
  return () => {
    clearInterval(timer);
    characterChannel?.removeEventListener("message", onMessage);
  };
}

/** Главное окно: просить строки и получать их в `onRows`. Вернёт отписку (перестать просить). */
export function watchChecklist(onRows: (rows: Checklist | null) => void): () => void {
  const ask = (): void => {
    const message: Ask = { kind: "checklist" };
    characterChannel?.postMessage(message);
  };
  const onMessage = (event: MessageEvent): void => {
    const data: unknown = event.data;
    if (isRows(data)) onRows(data.rows);
  };
  characterChannel?.addEventListener("message", onMessage);
  ask();
  const timer = setInterval(ask, PING_MS);
  return () => {
    clearInterval(timer);
    characterChannel?.removeEventListener("message", onMessage);
  };
}
