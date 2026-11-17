/**
 * «Смотрим вместе» (BEHAVIOR §11): идёт ли видео. Видеоплеер в фокусе; браузер на весь экран; браузер с
 * выбранной вкладкой видеосайта (название вкладки — UI Automation, адрес не читается). Чистая функция.
 */
import type { RemarkTopic } from "./remarks";
import { siteOf } from "./sites";

/** Видеоплееры по имени exe; OBS сюда не входит: это запись, а не просмотр. */
const PLAYERS: ReadonlySet<string> = new Set([
  "vlc",
  "mpc-hc64",
  "mpc-hc",
  "mpc-be64",
  "potplayermini64",
  "potplayermini",
  "mpv",
  "wmplayer",
  "video.ui",
  "netflix",
  "kodi",
  "plex",
]);

export interface WatchContext {
  app: string;
  topic: RemarkTopic;
  fullscreen: boolean;
  /** Название выбранной вкладки браузера или `null`, пока неизвестно. */
  tab: string | null;
}

export function watching(context: WatchContext): boolean {
  if (PLAYERS.has(context.app)) return true;
  if (context.topic !== "browser") return false;
  return context.fullscreen || (context.tab !== null && siteOf(context.tab) === "video");
}
