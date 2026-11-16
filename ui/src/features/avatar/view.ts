/**
 * Вид показа персонажа справа (Этап 23): сфера или окно персонажа. Выбор — в настройках окна
 * (localStorage); Live2D убран (ADR-0042).
 */
export type AvatarView = "orb";

export const AVATAR_VIEWS: readonly AvatarView[] = ["orb"];
export const DEFAULT_VIEW: AvatarView = "orb";

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
