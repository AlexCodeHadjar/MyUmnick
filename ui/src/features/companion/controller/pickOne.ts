export function pickOne(list: readonly string[]): string {
  return list[Math.floor(Math.random() * list.length)] ?? "";
}
