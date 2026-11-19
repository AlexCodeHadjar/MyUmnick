/**
 * Инициатива спутника (просьба пользователя 2026-11-17): сам время от времени говорит что-нибудь
 * в облачке — к месту (какая программа активна, время суток, долгий простой). Тексты — в словарях
 * интерфейса (`companion.remarks`), здесь только выбор: мгновенно и без LLM, офлайн.
 */
import type { Messages } from "../../../core";
import type { Rect } from "../space";

export type RemarkTopic =
  | "browser"
  | "code"
  | "chat"
  | "music"
  | "video"
  | "game"
  | "office"
  | "terminal"
  | "files"
  | "desktop"
  | "other";

/** Программы по имени exe (без `.exe`, нижний регистр) → тема комментария. */
const APPS: readonly (readonly [RemarkTopic, readonly string[]])[] = [
  [
    "browser",
    ["chrome", "msedge", "firefox", "opera", "brave", "browser", "vivaldi", "arc", "yandex"],
  ],
  [
    "code",
    [
      "code",
      "cursor",
      "windsurf",
      "idea64",
      "pycharm64",
      "webstorm64",
      "devenv",
      "rider64",
      "notepad++",
      "sublime_text",
      "zed",
      "claude",
      "codex",
    ],
  ],
  [
    "chat",
    [
      "chatgpt",
      "telegram",
      "discord",
      "whatsapp",
      "slack",
      "teams",
      "ms-teams",
      "zoom",
      "skype",
      "viber",
    ],
  ],
  ["music", ["spotify", "yandexmusic", "aimp", "foobar2000", "musicbee", "itunes", "applemusic"]],
  ["video", ["vlc", "mpc-hc64", "mpc-be64", "potplayermini64", "mpv", "obs64"]],
  [
    "game",
    [
      "steam",
      "steamwebhelper",
      "epicgameslauncher",
      "battle.net",
      "riotclientservices",
      "minecraft",
      "javaw",
    ],
  ],
  [
    "office",
    ["winword", "excel", "powerpnt", "onenote", "outlook", "obsidian", "notion", "acrobat"],
  ],
  [
    "terminal",
    ["windowsterminal", "cmd", "powershell", "pwsh", "wezterm-gui", "alacritty", "conhost"],
  ],
  ["files", ["explorer", "totalcmd64", "far", "everything"]],
];

export function topicOf(app: string, desktop: boolean): RemarkTopic {
  if (desktop) return "desktop";
  return APPS.find(([, names]) => names.includes(app))?.[0] ?? "other";
}

export type TimeOfDay = "morning" | "day" | "evening" | "night";

export function timeOfDay(hour: number): TimeOfDay {
  if (hour >= 5 && hour < 12) return "morning";
  if (hour >= 12 && hour < 18) return "day";
  if (hour >= 18 && hour < 23) return "evening";
  return "night";
}

type Random = () => number;

function pick(list: readonly string[], random: Random, last: string): string {
  const fresh = list.filter((line) => line !== last);
  const from = fresh.length > 0 ? fresh : list;
  return from[Math.floor(random() * from.length)] ?? "";
}

/** Комментарий: чаще — про программу, иногда — про время суток или простой; без повтора подряд. */
export function remark(
  t: Messages,
  context: { topic: RemarkTopic; hour: number; idleS: number },
  random: Random,
  last = "",
): string {
  const lists = t.companion.remarks;
  const roll = random();
  if (context.idleS > 600 && roll < 0.4) return pick(lists.idle, random, last);
  if (roll < 0.65) return pick(lists[context.topic], random, last);
  return pick(lists[timeOfDay(context.hour)], random, last);
}

/** Пауза до следующего комментария сам по себе, секунды: не часто, чтобы не надоедал. */
export function nextPause(random: Random): number {
  return 120 + random() * 180;
}

/** Элемент экрана от оболочки (`companion_targets`, ADR-0048): кнопка, ссылка, вкладка, значок. */
export interface Target {
  name: string;
  rect: Rect;
  kind: string;
  /** Выбранная вкладка (только у `tab`). */
  selected?: boolean;
}

/**
 * Что потыкать: случайный элемент целиком на экране. Палец — к ближнему краю элемента, тело — с той
 * стороны, где хватает места (кадр `poke` смотрит вправо, влево — отражение).
 */
export function choosePoke(
  targets: readonly Target[],
  screen: Rect,
  random: () => number = Math.random,
): { x: number; y: number; facing: 1 | -1; name: string } | null {
  const inside = targets.filter(
    (one) =>
      one.rect.x >= screen.x &&
      one.rect.y >= screen.y + 40 &&
      one.rect.x + one.rect.w <= screen.x + screen.w &&
      one.rect.y + one.rect.h <= screen.y + screen.h,
  );
  const chosen = inside[Math.floor(random() * inside.length)];
  if (chosen === undefined) return null;
  const { x, y, w, h } = chosen.rect;
  const roomLeft = x - screen.x;
  const facing: 1 | -1 = roomLeft > 220 ? 1 : -1;
  return { x: facing === 1 ? x : x + w, y: y + h / 2, facing, name: chosen.name };
}
