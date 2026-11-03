/**
 * Логика мастера первого запуска (S-13.2): что выбрано, сколько качать, можно ли начинать.
 * Загрузка начинается только с явного согласия: без галочки кнопка не активна.
 */
import type { SetupData } from "../../core";

export type SetupItem = SetupData["items"][number];

export function initialSelection(setup: SetupData): Set<string> {
  return new Set(setup.items.filter((item) => item.recommended || item.installed).map((i) => i.id));
}

/** Обязательное снять нельзя: без него диалог не заработает. */
export function toggled(selection: ReadonlySet<string>, item: SetupItem): Set<string> {
  const next = new Set(selection);
  if (item.required) {
    next.add(item.id);
  } else if (next.has(item.id)) {
    next.delete(item.id);
  } else {
    next.add(item.id);
  }
  return next;
}

/** Сколько байт ещё скачивать: уже стоящее не считается. */
export function downloadSize(items: readonly SetupItem[], selection: ReadonlySet<string>): number {
  return items
    .filter((item) => selection.has(item.id) && !item.installed)
    .reduce((sum, item) => sum + item.size, 0);
}

export function canInstall(
  setup: SetupData,
  selection: ReadonlySet<string>,
  agreed: boolean,
): boolean {
  return agreed && setup.items.every((item) => !item.required || selection.has(item.id));
}

export function formatSize(bytes: number): string {
  const gb = bytes / 1024 ** 3;
  return gb >= 1
    ? `${gb.toFixed(1)} ГБ`
    : `${Math.max(1, Math.round(bytes / 1024 ** 2)).toString()} МБ`;
}

export function percent(done: number, total: number): number {
  return total > 0 ? Math.min(100, Math.floor((done / total) * 100)) : 0;
}

/** Список аватаров из `avatars/index.json`; файла нет или он не JSON — только встроенный. */
export function parseAvatars(raw: unknown, fallback: string): string[] {
  return isNameList(raw) && raw.length > 0 ? raw : [fallback];
}

function isNameList(raw: unknown): raw is string[] {
  return Array.isArray(raw) && raw.every((name) => typeof name === "string");
}

/** Dev-сервер на отсутствующий файл отдаёт index.html: такой ответ — тоже «файла нет». */
export async function loadAvatars(fallback: string): Promise<string[]> {
  try {
    const response = await fetch("/avatars/index.json");
    const raw: unknown = await response.json();
    return parseAvatars(raw, fallback);
  } catch {
    return [fallback];
  }
}
