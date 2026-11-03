import { invoke, isTauri } from "@tauri-apps/api/core";

/**
 * Модели подхватываются при старте ядра, поэтому после установки приложение перезапускается.
 * Вне Tauri (Vite в браузере) перезапускать нечего: false — пусть пользователь сделает это сам.
 */
export async function restartApp(): Promise<boolean> {
  if (!isTauri()) {
    return false;
  }
  await invoke("restart_app");
  return true;
}
