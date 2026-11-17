/**
 * Сайты в браузере (BEHAVIOR §5): тема — по названию вкладки, которое и так видно на экране (UI
 * Automation, вид `tab`). Адреса и содержимое страниц не читаются. Чистые функции — проверяются тестами.
 */
export type SiteTopic =
  | "video"
  | "code"
  | "mail"
  | "maps"
  | "shop"
  | "news"
  | "social"
  | "music"
  | "search"
  | "ai"
  | "docs";

/** Слова в названии вкладки → тема; сравнение без регистра. Первое совпадение выигрывает. */
const SITES: readonly (readonly [SiteTopic, readonly string[]])[] = [
  ["video", ["youtube", "twitch", "rutube", "кинопоиск", "netflix", "vk видео", "ivi", "okko"]],
  ["code", ["github", "gitlab", "stack overflow", "stackoverflow", "habr", "хабр", "npm", "pypi"]],
  ["mail", ["gmail", "почта", "inbox", "входящие", "outlook", "mail.ru"]],
  ["maps", ["карты", "maps", "2гис", "2gis"]],
  ["shop", ["ozon", "wildberries", "amazon", "aliexpress", "авито", "avito", "маркет", "market"]],
  ["news", ["новости", "news", "лента", "рбк", "bbc", "cnn", "meduza", "медуза"]],
  [
    "social",
    ["вконтакте", "telegram", "twitter", "reddit", "instagram", "facebook", "tiktok", " / x"],
  ],
  ["music", ["spotify", "яндекс музыка", "soundcloud", "yandex music", "bandcamp"]],
  ["ai", ["chatgpt", "claude", "gemini", "perplexity", "deepseek", "copilot"]],
  ["docs", ["википедия", "wikipedia", "notion", "docs", "документ", "confluence"]],
  ["search", ["google", "яндекс", "yandex", "bing", "duckduckgo", "поиск"]],
];

export function siteOf(title: string): SiteTopic | null {
  const lower = title.toLowerCase();
  return SITES.find(([, words]) => words.some((word) => lower.includes(word)))?.[0] ?? null;
}

/** Сколько вкладок «много» — шутка про вкладки. */
const MANY_TABS = 20;

/**
 * Что сказать про браузер по названиям вкладок: «много вкладок», тема узнанного сайта или `null` (тогда
 * обычный комментарий про браузер).
 */
export function browserTopic(
  tabs: readonly string[],
  random: () => number,
): SiteTopic | "many" | null {
  if (tabs.length > MANY_TABS && random() < 0.35) return "many";
  const known = tabs.map(siteOf).filter((one) => one !== null);
  return known[Math.floor(random() * known.length)] ?? null;
}
