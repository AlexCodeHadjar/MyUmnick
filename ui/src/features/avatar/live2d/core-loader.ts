/**
 * Загрузка Cubism Core (проприетарный, кладёт пользователь — ADR-0011). Движок проверяет
 * `window.Live2DCubismCore` прямо при импорте, поэтому Core подключается раньше движка, а
 * отсутствие файла — понятная ошибка на сцене, а не падение всего окна.
 */

/** Где Vite отдаёт Core из `ui/public/live2d/`. */
export const CUBISM_CORE_URL = "/live2d/live2dcubismcore.min.js";

export const CORE_MISSING_MESSAGE =
  "Нет Cubism Core: положите live2dcubismcore.min.js из Cubism SDK for Web в ui/public/live2d/";

/**
 * Старший номер Core, с которым работает движок: Core 6 (SDK 5-r.5) убрал
 * `drawables.renderOrders`, и движок 1.4 падает в каждом кадре (его issue #11). Нужен Core из
 * SDK 5-r.4 (Core 5.1); поднять — вместе с обновлением движка.
 */
export const MAX_CORE_MAJOR = 5;

/** Версия Core из `csmGetVersion()`: 0xMMmmpppp. */
export function formatCoreVersion(version: number): string {
  return `${String(version >>> 24)}.${String((version >>> 16) & 0xff)}.${String(version & 0xffff)}`;
}

export function unsupportedCoreMessage(version: number): string {
  return (
    `Cubism Core ${formatCoreVersion(version)} не поддерживается движком: положите ` +
    "live2dcubismcore.min.js из Cubism SDK for Web 5-r.4 в ui/public/live2d/"
  );
}

/** Части `window`/`document`, нужные загрузчику: в тестах — подмена. */
export interface ScriptHost {
  hasCore(): boolean;
  /** `Live2DCubismCore.Version.csmGetVersion()`; null — если Core не отвечает на вопрос. */
  coreVersion(): number | null;
  appendScript(url: string, onLoad: () => void, onError: () => void): void;
}

const isObject = (value: unknown): value is object =>
  (typeof value === "object" || typeof value === "function") && value !== null;

/** Глобал Core не типизирован — читаем через Reflect с проверками, без приведений (R-62). */
function readCoreVersion(): number | null {
  const core: unknown = Reflect.get(window, "Live2DCubismCore");
  const version: unknown = isObject(core) ? Reflect.get(core, "Version") : undefined;
  const getter: unknown = isObject(version) ? Reflect.get(version, "csmGetVersion") : undefined;
  if (typeof getter !== "function" || !isObject(version)) {
    return null;
  }
  const value: unknown = Reflect.apply(getter, version, []);
  return typeof value === "number" ? value : null;
}

export const browserHost: ScriptHost = {
  hasCore: () => "Live2DCubismCore" in window,
  coreVersion: readCoreVersion,
  appendScript(url, onLoad, onError) {
    const script = document.createElement("script");
    script.src = url;
    script.async = true;
    script.addEventListener("load", onLoad, { once: true });
    script.addEventListener("error", onError, { once: true });
    document.head.append(script);
  },
};

let pending: Promise<void> | null = null;

/** Core есть и подходящей версии; иначе — ошибка с тем, что положить. */
function checkCore(host: ScriptHost): void {
  if (!host.hasCore()) {
    throw new Error(CORE_MISSING_MESSAGE);
  }
  const version = host.coreVersion();
  if (version !== null && version >>> 24 > MAX_CORE_MAJOR) {
    throw new Error(unsupportedCoreMessage(version));
  }
}

/** Подключить Core один раз на окно; повторные вызовы ждут ту же загрузку. */
export function loadCubismCore(
  host: ScriptHost = browserHost,
  url = CUBISM_CORE_URL,
): Promise<void> {
  if (host.hasCore()) {
    return Promise.resolve().then(() => {
      checkCore(host);
    });
  }
  pending ??= new Promise<void>((resolve, reject) => {
    host.appendScript(
      url,
      () => {
        try {
          checkCore(host);
          resolve();
        } catch (error) {
          reject(error instanceof Error ? error : new Error(String(error)));
        }
      },
      () => {
        reject(new Error(CORE_MISSING_MESSAGE));
      },
    );
  }).finally(() => {
    // Обещание нужно только на время загрузки: после успеха отвечает `hasCore()`, а неудачу
    // не запоминаем — пользователь положит файл, и следующая попытка загрузит.
    pending = null;
  });
  return pending;
}
