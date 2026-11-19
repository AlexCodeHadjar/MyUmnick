/**
 * Чек-лист спутника (просьба пользователя 2026-11-18): что он видит сейчас, сколько баллов у каждого
 * действия «Разума» и готовы ли реакции на действия пользователя. Только чтение состояния — ничего не меняет.
 */
import { locale } from "../../../core";
import type { CompanionController } from "../controller";
import type { DesktopEvent } from "../behavior/desktopEvents";
import { DESKTOP_REACTIONS } from "../settings";

export interface CheckRow {
  id: string;
  name: string;
  /** Условие словами; у датчиков — пусто. */
  when: string;
  /** Выполнено ли сейчас; `null` — не «да/нет» (баллы, режим). */
  ok: boolean | null;
  /** Значение: «да», «0,42 · сейчас», «шанс 90 % · пауза 12 с». */
  value: string;
  /** Баллы 0…1 для полоски (действия «Разума»). */
  score?: number;
}

export interface Checklist {
  sensors: CheckRow[];
  actions: CheckRow[];
  reactions: CheckRow[];
  others: CheckRow[];
}

const REACTIONS: readonly DesktopEvent["kind"][] = [
  "paste",
  "desktop",
  "copy",
  "screenshot",
  "download",
  "close",
];

/** Датчик «да/нет» — без цвета: «нет» у датчика не плохо («вы печатаете: нет»). */
function flag(id: string, name: string, on: boolean): CheckRow {
  const t = locale.t.companion.checklist;
  return { id, name, when: "", ok: null, value: on ? t.yes : t.no };
}

function sensors(c: CompanionController): CheckRow[] {
  const t = locale.t.companion.checklist.sensor;
  const facts = c.mind.facts;
  return [
    flag("shown", t.shown, c.presence.shown),
    {
      id: "behavior",
      name: t.behavior,
      when: "",
      ok: null,
      value: locale.t.companion[c.settings.behavior],
    },
    { id: "app", name: t.app, when: "", ok: null, value: c.scout.app || "—" },
    flag("fullscreen", t.fullscreen, c.presence.world?.fullscreen ?? false),
    flag("video", t.video, facts?.video ?? false),
    flag("desktop", t.desktop, c.presence.world?.focus.kind === "desktop"),
    flag("typing", t.typing, c.escort.caret !== null),
    flag("resting", t.resting, c.brain.phase === "rest"),
    flag("watching", t.watching, c.brain.watching),
    flag("calm", t.calm, c.settings.calm),
  ];
}

function actions(c: CompanionController, now: number): CheckRow[] {
  const t = locale.t.companion.checklist;
  return c.mind.ranking(now / 1000).map((one) => {
    const [name, when] = t.activity[one.id];
    const state = one.current ? t.now : one.available ? "" : t.blocked;
    const value = [one.score.toFixed(2), state].filter(Boolean).join(" · ");
    return {
      id: one.id,
      name: name ?? one.id,
      when: when ?? "",
      ok: one.current,
      value,
      score: one.score,
    };
  });
}

/** Те же условия, что у `subscriptions.ts`: на экране, стоит, не «спокойнее», не фильм, не полный экран. */
function canReact(c: CompanionController, kind: DesktopEvent["kind"]): boolean {
  const direct = ["desktop", "copy", "paste", "close"].includes(kind);
  const typing = !direct && c.escort.caret !== null;
  return (
    c.presence.shown &&
    !c.settings.calm &&
    (!c.presence.world?.fullscreen || c.scout.working(performance.now())) &&
    (c.brain.phase === "rest" || (direct && c.brain.phase === "walk")) &&
    (!c.brain.watching || c.scout.working(performance.now())) &&
    !typing
  );
}

function reactions(c: CompanionController, now: number): CheckRow[] {
  const t = locale.t.companion.checklist;
  return REACTIONS.map((kind) => {
    const [name, when] = t.reaction[kind];
    const wait = Math.ceil(c.desktopReactions.waitLeft(kind, now) / 1000);
    const chance = t.chance.replace(
      "{p}",
      String(Math.round(DESKTOP_REACTIONS[kind].chance * 100)),
    );
    const pause = wait > 0 ? t.pause.replace("{s}", String(wait)) : "";
    const ok = canReact(c, kind) && wait === 0;
    const value = [ok ? t.ready : t.blocked, chance, pause].filter(Boolean).join(" · ");
    return { id: kind, name: name ?? kind, when: when ?? "", ok, value };
  });
}

function others(): CheckRow[] {
  const t = locale.t.companion.checklist.other;
  return Object.entries(t).map(([id, [name, when]]) => ({
    id,
    name: name ?? id,
    when: when ?? "",
    ok: null,
    value: "",
  }));
}

/** Строки чек-листа на момент `now` (мс, `performance.now()`). */
export function checklist(c: CompanionController, now: number): Checklist {
  return {
    sensors: sensors(c),
    actions: actions(c, now),
    reactions: reactions(c, now),
    others: others(),
  };
}
