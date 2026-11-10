/**
 * Где окно хранит выбор издания и как запускает ядро нужного издания (Этап 20, ADR-0032).
 * В Tauri — команды оболочки (`launcher.json` в папке настроек, ядро с `--edition`); в браузере
 * (Vite без окна) — localStorage, а ядро запускают руками: `python -m vtuber serve --edition <id>`.
 */
import { invoke, isTauri } from "@tauri-apps/api/core";

import { DEFAULT_LAUNCHER, parseLauncher, type EditionId, type LauncherState } from "./editions";

export interface LauncherPort {
  load(): Promise<LauncherState>;
  save(state: LauncherState): Promise<void>;
  /** Ядро нужного издания: то же, что уже запущено, — без перезапуска (предзапуск). */
  startCore(edition: EditionId): Promise<void>;
  /** Остановить ядро перед сменой издания: два ядра с LLM в 16 ГБ не поместятся. */
  stopCore(): Promise<void>;
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
}

export function launcher(): LauncherPort {
  return isTauri() ? new TauriLauncher() : new BrowserLauncher();
}

/** Запрос экрана выбора при перезагрузке окна (смена издания из строки статуса). */
export const PICK_PARAM = "pick";

export function pickRequested(search: string): boolean {
  return new URLSearchParams(search).has(PICK_PARAM);
}
