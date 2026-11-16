/**
 * Картинка персонажа (Этап 23, ADR-0044): проверка файла, хранение в IndexedDB окна, способ вписать.
 * Хранилище — того же происхождения, что окно: спутник (S-23.5+) увидит ту же картинку.
 */
import { messagesFor, type Messages } from "../../../core";

/** Форматы, которые `<img>` WebView2 показывает сам, включая анимированные GIF, WebP и APNG. */
export const PICTURE_TYPES: readonly string[] = [
  "image/png",
  "image/apng",
  "image/jpeg",
  "image/webp",
  "image/gif",
];
export const MAX_PICTURE_BYTES = 20 * 1024 * 1024;

export type PictureFit = "contain" | "cover";

/** Причина отказа на языке интерфейса или `null`, если файл подходит. */
export function pictureProblem(
  file: { type: string; size: number },
  t: Messages = messagesFor("ru"),
): string | null {
  if (!PICTURE_TYPES.includes(file.type)) return t.character.badType;
  if (file.size > MAX_PICTURE_BYTES) return t.character.tooBig;
  if (file.size === 0) return t.character.broken;
  return null;
}

/** Способ вписать картинку: битое или чужое значение — «вписать целиком». */
export function parseFit(value: string | null): PictureFit {
  return value === "cover" ? "cover" : "contain";
}

const FIT_KEY = "vtuber.character.fit";

export function loadFit(storage: Storage | undefined): PictureFit {
  try {
    return parseFit(storage?.getItem(FIT_KEY) ?? null);
  } catch {
    return "contain";
  }
}

export function saveFit(storage: Storage | undefined, fit: PictureFit): void {
  try {
    storage?.setItem(FIT_KEY, fit);
  } catch {
    // Не запомнится — способ работает до перезапуска.
  }
  pictureChanged.dispatchEvent(new Event("fit"));
}

/** localStorage окна; недоступно (приватный режим WebView) — без хранилища. */
export function windowStorage(): Storage | undefined {
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
}

const DB = "vtuber-character";
const STORE = "pictures";
const KEY = "portrait";

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB, 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE);
    };
    request.onsuccess = () => {
      resolve(request.result);
    };
    request.onerror = () => {
      reject(request.error ?? new Error("IndexedDB is unavailable"));
    };
  });
}

async function run<T>(
  mode: IDBTransactionMode,
  act: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await open();
  try {
    return await new Promise<T>((resolve, reject) => {
      const request = act(db.transaction(STORE, mode).objectStore(STORE));
      request.onsuccess = () => {
        resolve(request.result);
      };
      request.onerror = () => {
        reject(request.error ?? new Error("IndexedDB request failed"));
      };
    });
  } finally {
    db.close();
  }
}

/** Сохранённая картинка; нет её или хранилище недоступно — `null` (стандартный силуэт). */
export async function loadPicture(): Promise<Blob | null> {
  try {
    const value: unknown = await run("readonly", (store) => store.get(KEY));
    return value instanceof Blob ? value : null;
  } catch {
    return null;
  }
}

export async function savePicture(picture: Blob): Promise<void> {
  await run("readwrite", (store) => store.put(picture, KEY));
  pictureChanged.dispatchEvent(new Event("change"));
}

export async function clearPicture(): Promise<void> {
  await run("readwrite", (store) => store.delete(KEY));
  pictureChanged.dispatchEvent(new Event("change"));
}

/** Картинку сменили: рендер окошка перечитывает её без перезапуска сцены. */
export const pictureChanged = new EventTarget();
