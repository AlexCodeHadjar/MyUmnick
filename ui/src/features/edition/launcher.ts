/**
 * Где окно хранит выбор издания и как запускает ядро нужного издания (Этап 20, ADR-0032).
 * В Tauri — команды оболочки (`launcher.json` в папке настроек, ядро с `--edition`); в браузере
 * (Vite без окна) — localStorage, а ядро запускают руками: `python -m vtuber serve --edition <id>`.
 */
import { invoke, isTauri } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

import { DEFAULT_LAUNCHER, parseLauncher, type EditionId, type LauncherState } from "./editions";

export interface LauncherPort {
  load(): Promise<LauncherState>;
  save(state: LauncherState): Promise<void>;
  /** Ядро нужного издания: то же, что уже запущено, — без перезапуска (предзапуск). */
  startCore(edition: EditionId): Promise<void>;
  /** Остановить ядро перед сменой издания: два ядра с LLM в 16 ГБ не поместятся. */
  stopCore(): Promise<void>;
  /** Окно запущено в фоне (автозапуск с Windows, ADR-0041): без экрана выбора, ждёт зова. */
  background(): Promise<boolean>;
  /** Показать скрытое или свёрнутое окно: витюбера позвали. */
  reveal(): Promise<void>;
  /** Окно показали или спрятали в трей: WebView2 сам `visibilitychange` при этом не шлёт. */
  onShown(sink: (shown: boolean) => void): void;
}

const STORAGE_KEY = "vtuber.launcher";

class TauriLauncher implements LauncherPort {
  async load(): Promise<LauncherState> {
    try {
      return parseLauncher(JSON.parse(await invoke<string>("launcher_load")));
    } catch {
      return DEFAULT_LAUNCHER;
    }
  }

  async save(state: LauncherState): Promise<void> {
    await invoke("launcher_save", { json: JSON.stringify(state) });
  }

  async startCore(edition: EditionId): Promise<void> {
    await invoke("core_start", { edition });
  }

  async stopCore(): Promise<void> {
    await invoke("core_stop");
  }

  async background(): Promise<boolean> {
    try {
      return await invoke<boolean>("background_mode");
    } catch {
      return false;
    }
  }

  async reveal(): Promise<void> {
    await invoke("window_reveal");
  }

  onShown(sink: (shown: boolean) => void): void {
    void listen<boolean>("window-shown", (event) => {
      sink(event.payload);
    });
  }
}

class BrowserLauncher implements LauncherPort {
  load(): Promise<LauncherState> {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return Promise.resolve(raw === null ? DEFAULT_LAUNCHER : parseLauncher(JSON.parse(raw)));
    } catch {
      return Promise.resolve(DEFAULT_LAUNCHER);
    }
  }

  save(state: LauncherState): Promise<void> {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Хранилище недоступно (приватный режим WebView) — выбор просто не запомнится.
    }
    return Promise.resolve();
  }

  startCore(): Promise<void> {
    return Promise.resolve();
  }

  stopCore(): Promise<void> {
    return Promise.resolve();
  }

  background(): Promise<boolean> {
    return Promise.resolve(false); // у вкладки браузера нет трея
  }

  reveal(): Promise<void> {
    return Promise.resolve();
  }

  onShown(): void {
    // Вкладка браузера скрывается сама — хватает `visibilitychange`.
  }
}

export function launcher(): LauncherPort {
  return isTauri() ? new TauriLauncher() : new BrowserLauncher();
}

/** Запрос экрана выбора при перезагрузке окна (смена издания из строки статуса). */
export const PICK_PARAM = "pick";

export function pickRequested(search: string): boolean {
  return new URLSearchParams(search).has(PICK_PARAM);
}
