/**
 * Загрузка Cubism Core (проприетарный, кладёт пользователь — ADR-0011). Движок проверяет
 * `window.Live2DCubismCore` прямо при импорте, поэтому Core подключается раньше движка, а
 * отсутствие файла — понятная ошибка на сцене, а не падение всего окна.
 */

/** Где Vite отдаёт Core из `ui/public/live2d/`. */
export const CUBISM_CORE_URL = "/live2d/live2dcubismcore.min.js";

export const CORE_MISSING_MESSAGE =
  "Нет Cubism Core: положите live2dcubismcore.min.js из Cubism SDK for Web в ui/public/live2d/";

/** Части `window`/`document`, нужные загрузчику: в тестах — подмена. */
export interface ScriptHost {
  hasCore(): boolean;
  appendScript(url: string, onLoad: () => void, onError: () => void): void;
}

export const browserHost: ScriptHost = {
  hasCore: () => "Live2DCubismCore" in window,
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

/** Подключить Core один раз на окно; повторные вызовы ждут ту же загрузку. */
export function loadCubismCore(
  host: ScriptHost = browserHost,
  url = CUBISM_CORE_URL,
): Promise<void> {
  if (host.hasCore()) {
    return Promise.resolve();
  }
  pending ??= new Promise<void>((resolve, reject) => {
    host.appendScript(
      url,
      () => {
        if (host.hasCore()) {
          resolve();
        } else {
          reject(new Error(CORE_MISSING_MESSAGE));
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
