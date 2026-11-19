/**
 * Метки хронометража запуска (2026-11-19): оболочка пишет их в `startup.log` (`startup.rs`). Вне Tauri
 * и при ошибке — тишина: замер не должен мешать запуску.
 */
import { invoke, isTauri } from "@tauri-apps/api/core";

export function startupMark(name: string): void {
  if (!isTauri()) return;
  invoke("startup_mark", { name }).catch(() => undefined);
}
