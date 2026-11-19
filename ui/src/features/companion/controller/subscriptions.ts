import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import type { CompanionController, Feed } from "./controller";
import type { MainState } from "./presence";
import type { DesktopEvent } from "../behavior/desktopEvents";
import { DESKTOP_REACTIONS } from "../settings";
import type { CompanionSettings } from "../settings";
import type { Rect, World } from "../space";
export function subscribe(
  controller: CompanionController,
  settings: () => CompanionSettings,
  menuOpen: () => boolean,
  change: (next: Partial<CompanionSettings>) => void,
): Promise<UnlistenFn>[] {
  const ready = () => calm(controller, settings(), menuOpen());
  return [
    listen<DesktopEvent>("companion-desktop-event", ({ payload }) => {
      if (payload.kind === "paste" || payload.kind === "copy")
        controller.scout.textCopied(performance.now());
      react(controller, payload, ready);
    }),
    listen<World>("companion-world", (event) => {
      controller.onWorld(event.payload);
    }),
    listen<[number, Rect | null]>("companion-host", (event) => {
      controller.onHost(...event.payload);
    }),
    listen<MainState>("companion-main", (event) => {
      controller.onMain(event.payload);
    }),
    listen("companion-called", () => {
      controller.onCalled();
    }),
    // Двойной щелчок по персонажу в режиме «Не мешать кликам» — снова можно трогать.
    listen("companion-wake", () => {
      if (settings().hologram) change({ hologram: false });
    }),
    listen<Rect | null>("companion-typing", (event) => {
      controller.onTyping(event.payload);
    }),
    listen<[number, number]>("companion-cursor", (event) => {
      controller.onCursor(...event.payload);
    }),
    listen<Feed>("companion-feed", (event) => {
      controller.onFeed(event.payload);
    }),
  ];
}

/** Можно ли сейчас реагировать на действие пользователя (кроме фазы тела). */
function calm(
  controller: CompanionController,
  settings: CompanionSettings,
  menuOpen: boolean,
): boolean {
  return (
    controller.presence.shown &&
    controller.brain.music === "off" &&
    !settings.calm &&
    (!controller.presence.world?.fullscreen || controller.scout.working(performance.now())) &&
    !controller.gestures.active &&
    !menuOpen &&
    (!controller.brain.watching || controller.scout.working(performance.now()))
  );
}

/**
 * Реакция на событие рабочего стола. Ctrl+V нажимают за набором текста — печать её не глушит; Win+D
 * уносит окно из-под ног, персонаж падает — реакция ждёт приземления (`landWaitMs`).
 */
function react(controller: CompanionController, payload: DesktopEvent, ready: () => boolean): void {
  const deadline = performance.now() + DESKTOP_REACTIONS.landWaitMs;
  const direct = ["desktop", "copy", "paste", "close"].includes(payload.kind);
  const tryNow = (): void => {
    const now = performance.now();
    const resting = controller.brain.phase === "rest";
    // Сигнал Win+D и картина окон приходят от разных опросов, в любом порядке.
    const waitingForDesktop =
      payload.kind === "desktop" && controller.presence.world?.focus.kind !== "desktop";
    if (waitingForDesktop || (direct && !resting && controller.brain.phase !== "walk")) {
      if (now < deadline) setTimeout(tryNow, LAND_POLL_MS);
      return;
    }
    const typing = controller.escort.caret !== null && !direct;
    const enabled =
      ready() && (resting || (direct && controller.brain.phase === "walk")) && !typing;
    const pose = controller.desktopReactions.offer(payload, now, enabled, Math.random());
    if (pose !== null) {
      if (direct && controller.brain.body().pose === "peek") controller.brain.rescue();
      const seconds = DESKTOP_REACTIONS.duration / 1000;
      if (!controller.brain.stopForPose(pose, seconds)) controller.brain.emote(pose, seconds);
    }
  };
  tryNow();
}

/** Как часто проверять, приземлился ли персонаж после Win+D, мс. */
const LAND_POLL_MS = 150;
