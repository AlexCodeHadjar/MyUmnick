/**
 * Список чатов слева (Этап 21, ADR-0037): группировка по категориям и свёрнутость панели.
 * Логика здесь, разметка — в `ChatSidebar.svelte` (компоненты не тестируются автоматически).
 */
import type { CategoryData, ChatItemData } from "../../core";

export interface ChatGroup {
  /** null — чаты без категории (идут первыми, как в Claude). */
  category: CategoryData | null;
  chats: ChatItemData[];
}

/** Без категории — сверху, затем категории в порядке создания; пустые категории тоже видны. */
export function groupChats(
  chats: readonly ChatItemData[],
  categories: readonly CategoryData[],
): ChatGroup[] {
  const known = new Set(categories.map((category) => category.id));
  const loose = chats.filter((chat) => chat.category === null || !known.has(chat.category));
  return [
    { category: null, chats: loose },
    ...categories.map((category) => ({
      category,
      chats: chats.filter((chat) => chat.category === category.id),
    })),
  ];
}

/** Название в списке: пустое — «Новый чат» на языке интерфейса. */
export function chatLabel(chat: ChatItemData, untitled: string): string {
  return chat.title.trim() === "" ? untitled : chat.title;
}

export interface SettingStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

const COLLAPSED_KEY = "vtuber.chats.collapsed";

/** Свёрнута ли панель чатов; хранилище недоступно — развёрнута. */
export function readCollapsed(storage: SettingStorage | null): boolean {
  try {
    return storage?.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeCollapsed(storage: SettingStorage | null, collapsed: boolean): void {
  try {
    storage?.setItem(COLLAPSED_KEY, collapsed ? "1" : "0");
  } catch {
    // Хранилище недоступно (приватный режим WebView) — свёрнутость просто не запомнится.
  }
}
