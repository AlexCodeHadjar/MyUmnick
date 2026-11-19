export interface Keepsake {
  name: string;
  icon: string;
}
export interface Workday {
  day: string;
  seconds: number;
}
const LIMIT = 12;

function valid(value: unknown): value is Keepsake {
  return (
    typeof value === "object" &&
    value !== null &&
    "name" in value &&
    typeof value.name === "string" &&
    value.name.length > 0 &&
    value.name.length <= 160 &&
    "icon" in value &&
    typeof value.icon === "string" &&
    value.icon.length < 64000 &&
    /^[a-zA-Z0-9+/]+=*$/.test(value.icon)
  );
}

export function parsePocket(text: string | null): Keepsake[] {
  try {
    const raw: unknown = JSON.parse(text ?? "[]");
    return Array.isArray(raw) ? raw.filter(valid).slice(0, LIMIT) : [];
  } catch {
    return [];
  }
}

export function addItem(items: Keepsake[], item: Keepsake): Keepsake[] {
  return [item, ...items.filter((other) => other.name !== item.name)].slice(0, LIMIT);
}

export function dayProgress(old: Workday | null, day: string, elapsed: number): Workday {
  const previous = old?.day === day && Number.isFinite(old.seconds) ? Math.max(0, old.seconds) : 0;
  return { day, seconds: previous + elapsed };
}
