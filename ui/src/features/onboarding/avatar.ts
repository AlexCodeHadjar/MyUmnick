/** Выбранный в мастере аватар; недоступное хранилище — просто без выбора. */
const KEY = "vtuber.avatar";

export function chosenAvatar(storage: Storage | undefined): string | null {
  return storage?.getItem(KEY) ?? null;
}

export function chooseAvatar(storage: Storage | undefined, name: string): void {
  storage?.setItem(KEY, name);
}
