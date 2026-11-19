import type { CompanionController } from "../controller";
import { KEEPSAKE_TIMING as timing } from "../settings";
import { dayProgress, type Workday } from "./keepsakes";
export function createBuilding(controller: CompanionController) {
  const buildKey = "companion.build.v1";
  let day = $state<Workday | null>(null);
  try {
    const raw: unknown = JSON.parse(localStorage.getItem(buildKey) ?? "null");
    if (
      typeof raw === "object" &&
      raw !== null &&
      "day" in raw &&
      typeof raw.day === "string" &&
      "seconds" in raw &&
      typeof raw.seconds === "number"
    )
      day = dayProgress(null, raw.day, raw.seconds);
  } catch {
    /* empty day */
  }
  let house = $state<HTMLDivElement>();
  let nextAccount = 0,
    lastActivity = 0;
  let buildingVisible = $state(false);
  let previousWorld: CompanionController["presence"]["world"] = null;
  let previousIcons: CompanionController["scout"]["icons"] | null = null;
  let previousCursor: { x: number; y: number } | null = null;

  const date = () => new Intl.DateTimeFormat("en-CA").format(Date.now());
  const persist = () => {
    localStorage.setItem(buildKey, JSON.stringify(day));
  };

  const block = (value: Workday | null) => Math.floor((value?.seconds ?? 0) / timing.stepSecs);

  function resetBuilding(): void {
    day = { day: date(), seconds: 0 };
    persist();
  }
  function account(now: number) {
    if (controller.presence.shown) {
      if (controller.escort.caret || previousCursor !== controller.escort.cursor) {
        lastActivity = now;
        previousCursor = controller.escort.cursor;
      }
      if (now >= nextAccount) {
        const active = lastActivity > 0 && now - lastActivity <= timing.activeMs;
        const updated = dayProgress(
          day,
          date(),
          active && nextAccount > 0 ? timing.accountMs / 1000 : 0,
        );
        nextAccount = now + timing.accountMs;
        // Новый блок постройки — строит его на глазах, если стоит без дела (`build_1…4`, FRAMES-6).
        if (block(updated) > block(day)) controller.brain.emote("build", timing.buildS);
        if (day?.seconds !== updated.seconds || day.day !== updated.day) {
          day = updated;
          persist();
        }
      }
    }
  }
  function place(world: NonNullable<CompanionController["presence"]["world"]>) {
    const hx = world.work.x + world.work.w - 88,
      hy = world.work.y + world.work.h - 64;
    if (world !== previousWorld || controller.scout.icons !== previousIcons) {
      previousWorld = world;
      previousIcons = controller.scout.icons;
      buildingVisible = !controller.scout.icons.some(
        (i) =>
          i.rect.x < hx + 80 &&
          i.rect.x + i.rect.w > hx &&
          i.rect.y < hy + 55 &&
          i.rect.y + i.rect.h > hy,
      );
    }
    if (house) house.style.transform = "translate(" + String(hx) + "px," + String(hy) + "px)";
  }
  return {
    account,
    place,
    resetBuilding,
    get day() {
      return day;
    },
    get visible() {
      return buildingVisible;
    },
    get house() {
      return house;
    },
    set house(value: HTMLDivElement | undefined) {
      house = value;
    },
  };
}
