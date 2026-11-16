/**
 * Логика панели «Навыки» (Этап 23, ADR-0043): группы, поиск, подтверждение сети, подписи счётчиков.
 * Разметка — в `SkillsPanel.svelte` (компоненты не тестируются автоматически).
 */
import type { Messages, SkillData } from "../../core";

export type SkillGroup = "on" | "off" | "idle";

/** Включён — «on»; выключен, но плагин работает — «off»; плагин установлен, но не запущен — «idle». */
export function groupOf(skill: SkillData): SkillGroup {
  if (!skill.loaded) return "idle";
  return skill.enabled ? "on" : "off";
}

/** Навыки по группам в порядке панели; поиск — по названию, описанию и примерам, без регистра. */
export function grouped(
  skills: readonly SkillData[],
  query: string,
): { group: SkillGroup; skills: SkillData[] }[] {
  const needle = query.trim().toLowerCase();
  const found = skills.filter((skill) =>
    needle === ""
      ? true
      : [skill.title, skill.summary, ...skill.examples].some((text) =>
          text.toLowerCase().includes(needle),
        ),
  );
  const order: SkillGroup[] = ["on", "off", "idle"];
  return order
    .map((group) => ({ group, skills: found.filter((skill) => groupOf(skill) === group) }))
    .filter((part) => part.skills.length > 0);
}

/** Включение навыка, который ходит в интернет, — только после явного «да» (NFR-06). */
export function needsConfirm(skill: SkillData, enabling: boolean): boolean {
  return enabling && skill.network;
}

/** Строка счётчиков: «сработал 3 раза · 12 мс · не успел 1»; не срабатывал — пусто. */
export function statsLine(skill: SkillData, t: Messages): string {
  const parts: string[] = [];
  if (skill.uses > 0) parts.push(t.skills.uses(skill.uses));
  if (skill.average_ms !== null) parts.push(t.skills.ms(Math.round(skill.average_ms)));
  if (skill.timeouts > 0) parts.push(t.skills.timeouts(skill.timeouts));
  return parts.join(" · ");
}

type KeyInfo = Pick<KeyboardEvent, "code" | "ctrlKey" | "shiftKey" | "altKey" | "metaKey">;

/** Ctrl+Shift+K по `code`: в русской раскладке `key` у этой клавиши — «Л». */
export function isSkillsHotkey(event: KeyInfo): boolean {
  return (
    event.code === "KeyK" && event.ctrlKey && event.shiftKey && !event.altKey && !event.metaKey
  );
}
