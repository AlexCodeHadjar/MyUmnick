/**
 * Вид показа персонажа справа (Этап 23): окно персонажа с картинкой или сфера. Выбор — в меню по
 * правой кнопке (localStorage); по умолчанию — картинка (ADR-0044). Live2D убран (ADR-0042).
 */
export type AvatarView = "portrait" | "orb";

export const AVATAR_VIEWS: readonly AvatarView[] = ["portrait", "orb"];
export const DEFAULT_VIEW: AvatarView = "portrait";

const KEY = "vtuber.avatar.view";

export function parseView(value: string | null): AvatarView {
  return AVATAR_VIEWS.find((view) => view === value) ?? DEFAULT_VIEW;
}

/** Сохранённый вид; хранилище недоступно — вид по умолчанию. */
export function loadView(storage: Storage | undefined): AvatarView {
  try {
    return parseView(storage?.getItem(KEY) ?? null);
  } catch {
    return DEFAULT_VIEW;
  }
}

export function saveView(storage: Storage | undefined, view: AvatarView): void {
  try {
    storage?.setItem(KEY, view);
  } catch {
    // Не запомнится — вид работает до перезапуска.
  }
}
