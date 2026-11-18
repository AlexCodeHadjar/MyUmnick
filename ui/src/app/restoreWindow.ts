/**
 * Режима «персонаж поверх рабочего стола» (S-15.2) больше нет (просьба пользователя 2026-11-18): окно,
 * которое он оставил маленьким и без рамки, становится обычным, а старая запись настроек стирается.
 */
const LEGACY_KEY = "vtuber.desktop";
/** Размеры обычного окна из tauri.conf.json. */
const NORMAL = { width: 1280, height: 760, minWidth: 800, minHeight: 500 } as const;

interface LegacyStorage {
  getItem(key: string): string | null;
  removeItem(key: string): void;
}

/** Была ли включена старая запись «поверх стола». */
export function wasOverlay(raw: string | null): boolean {
  if (raw === null) return false;
  try {
    const saved: unknown = JSON.parse(raw);
    return (
      typeof saved === "object" && saved !== null && "overlay" in saved && saved.overlay === true
    );
  } catch {
    return false;
  }
}

export async function restoreWindow(storage: LegacyStorage | undefined): Promise<void> {
  const raw = storage?.getItem(LEGACY_KEY) ?? null;
  if (raw === null) return;
  storage?.removeItem(LEGACY_KEY);
  if (!wasOverlay(raw)) return;
  const api = await import("@tauri-apps/api/window");
  const current = api.getCurrentWindow();
  await current.setIgnoreCursorEvents(false);
  await current.setAlwaysOnTop(false);
  await current.setDecorations(true);
  await current.setShadow(true);
  await current.setMinSize(new api.LogicalSize(NORMAL.minWidth, NORMAL.minHeight));
  await current.setSize(new api.LogicalSize(NORMAL.width, NORMAL.height));
}
