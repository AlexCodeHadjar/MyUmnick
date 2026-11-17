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

/** Что играет в системе (`companion_media`, ADR-0052). */
export interface Media {
  state: "playing" | "paused" | "none";
  /** Источник в нижнем регистре: `chrome.exe`, `msedge`, `spotify.exe`… */
  app: string;
}

const MUSIC_APPS = [
  "spotify",
  "yandexmusic",
  "yandex.music",
  "aimp",
  "foobar",
  "musicbee",
  "itunes",
  "zunemusic",
  "applemusic",
  "deezer",
  "soundcloud",
];
const VIDEO_APPS = [
  "vlc",
  "mpc",
  "potplayer",
  "mpv",
  "zunevideo",
  "netflix",
  "kinopoisk",
  "kodi",
  "plex",
  "wmplayer",
  "video.ui",
];
const BROWSERS = [
  "chrome",
  "msedge",
  "firefox",
  "opera",
  "brave",
  "browser",
  "vivaldi",
  "yandex",
  "arc",
];

/** Музыка играет в музыкальной программе (Spotify, Яндекс Музыка, AIMP…) — для «потанцевать». */
export function musicPlaying(list: readonly Media[]): boolean {
  return list.some(
    (one) => one.state === "playing" && MUSIC_APPS.some((name) => one.app.includes(name)),
  );
}

/** Пауза — часть просмотра: столько секунд на паузе он ещё «смотрит». */
export const PAUSE_KEEP_S = 90;

/**
 * Видео по сеансам мультимедиа Windows (ADR-0052): играет (или недавно встал на паузу) браузер или
 * видеоплеер, а не музыкальная программа; браузер с выбранной музыкальной вкладкой — тоже музыка.
 */
export function mediaVideo(media: Media, tab: string | null): boolean {
  if (media.state === "none") return false;
  const from = (names: readonly string[]): boolean =>
    names.some((name) => media.app.includes(name));
  // Встроенный веб-движок (окна приложений, само окно витюбера) — не браузер, хоть и «msedge…».
  if (media.app.includes("webview") || from(MUSIC_APPS)) return false;
  if (from(VIDEO_APPS)) return true;
  return from(BROWSERS) && (tab === null || siteOf(tab) !== "music");
}

/**
 * Из всех источников звука (`companion_media`) — видео: играющее важнее стоящего на паузе; нет —
 * «ничего не играет».
 */
export function pickMedia(list: readonly Media[], tab: string | null): Media {
  const video = list.filter((one) => mediaVideo(one, tab));
  return (
    video.find((one) => one.state === "playing") ??
    video.find((one) => one.state === "paused") ?? { state: "none", app: "" }
  );
}

/**
 * Начать смотреть — видео в фокусе или на весь экран; уже смотрим — держимся, пока фильм идёт или стоит
 * на паузе недолго, куда бы ни ушёл фокус (щелчок по рабочему столу не прерывает фильм).
 */
export function keepWatching(context: {
  media: Media;
  pausedS: number;
  tab: string | null;
  focusVideo: boolean;
  already: boolean;
}): boolean {
  const { media, pausedS, tab, focusVideo, already } = context;
  if (!mediaVideo(media, tab)) return false;
  if (media.state === "paused" && pausedS > PAUSE_KEEP_S) return false;
  return already || focusVideo;
}
