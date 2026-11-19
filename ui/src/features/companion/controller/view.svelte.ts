import { checklist, type Checklist } from "../look/checklist";
import { serveChecklist } from "../look/checklistLink";
import { pointerHandlers } from "./pointer";
import { locale } from "../../../core";
import { onMount } from "svelte";

import { characterChannel } from "../../avatar/portrait/picture";
import { CompanionController, tauriPorts } from "./index";
import { CompanionStage, placeMenu } from "../look";
import {
  COMPANION_KEY,
  loadSettings,
  saveSettings,
  type CompanionBehavior,
  type CompanionSettings,
} from "../settings";
import { placeBubble, type Rect } from "../space";
import { subscribe } from "./subscriptions";
interface DeskBindings {
  interactiveRect(): Rect | null;
  tick(now: number): void;
  resetBuilding(): void;
}
/** Как часто обновлять открытый чек-лист, мс. */
const CHECKLIST_EVERY_MS = 500;

export function createView() {
  const controller = new CompanionController(
    tauriPorts,
    window.localStorage,
    loadSettings(window.localStorage),
  );

  let keepsakes: DeskBindings | undefined;
  let canvas: HTMLCanvasElement | undefined = $state();
  let settings = $state<CompanionSettings>(controller.settings);
  let bubble = $state<{ text: string; x: number; y: number } | null>(null);
  /** Облачко на экране: его размер прошлого кадра держит текст в пределах экрана. */
  let bubbleEl = $state<HTMLParagraphElement | null>(null);
  let menu = $state<{ x: number; y: number } | null>(null);
  let menuEl: HTMLElement | undefined = $state();
  // Меню целиком на экране: размер известен только после показа — тогда и сдвигаем.
  $effect(() => {
    if (menu === null || menuEl === undefined) return;
    const box = menuEl.getBoundingClientRect();
    const next = placeMenu(
      menu,
      { w: box.width, h: box.height },
      { w: innerWidth, h: innerHeight },
    );
    if (next.x !== menu.x || next.y !== menu.y) menu = next;
  });
  // Радио (ADR-0049): табличка над головой — станция и ⏮ ⏯ ⏭; кнопки шлют команды главному окну.
  let radio = $state(controller.radio);
  let radioAt = $state<Rect | null>(null);
  let radioEl = $state<HTMLDivElement | null>(null);
  // Чек-лист (2026-11-18): обновляется два раза в секунду, пока открыт.
  let checks = $state<Checklist | null>(null);
  let checklistEl = $state<HTMLDivElement | null>(null);
  let checksAt = 0;

  function toggleChecklist(): void {
    menu = null;
    checks = checks === null ? checklist(controller, performance.now()) : null;
  }

  /** Курсор над чек-листом — слой ловит мышь, чтобы его можно было листать и закрыть. */
  function checklistRect(): Rect | null {
    const p = controller.escort.cursor;
    if (checklistEl === null || p === null) return null;
    const r = checklistEl.getBoundingClientRect();
    const inside = p.x >= r.left && p.x <= r.right && p.y >= r.top && p.y <= r.bottom;
    return inside ? { x: r.left, y: r.top, w: r.width, h: r.height } : null;
  }

  function openMain(): void {
    menu = null;
    tauriPorts.showMain();
  }

  function change(next: Partial<CompanionSettings>): void {
    const resized = next.height !== undefined && next.height !== settings.height;
    settings = { ...settings, ...next };
    saveSettings(window.localStorage, settings);
    if (resized) void controller.stage?.load(settings.height);
    controller.setSettings(settings);
  }

  function behave(behavior: CompanionBehavior): void {
    change({ behavior });
    menu = null;
  }

  /** Кнопки на корпусе музбокса, речевое облачко над персонажем. */
  function place(now: number): void {
    radio = controller.radio;
    const box = controller.stage?.bounds ?? null;
    const view = { w: innerWidth, h: innerHeight };
    radioAt = controller.stage?.radioControls ?? null;
    const text = controller.speech.text(now, locale.t.companion.listening);
    if (box === null || text === "") {
      bubble = null;
      return;
    }
    const size =
      bubbleEl === null ? { w: 280, h: 60 } : { w: bubbleEl.offsetWidth, h: bubbleEl.offsetHeight };
    bubble = { text, ...placeBubble(box, size, view) };
  }

  function cardRect(): Rect | null {
    if (radioEl === null) return null;
    const r = radioEl.getBoundingClientRect();
    return { x: r.left, y: r.top, w: r.width, h: r.height };
  }

  function frame(dt: number, now: number): void {
    controller.frame(dt, now, {
      menuOpen: menu !== null,
      card: cardRect(),
      direct: keepsakes?.interactiveRect() ?? checklistRect(),
    });
    if (checks !== null && now >= checksAt) {
      checksAt = now + CHECKLIST_EVERY_MS;
      checks = checklist(controller, now);
    }
    if (
      controller.presence.shown &&
      !settings.calm &&
      controller.brain.music === "off" &&
      (!controller.presence.world?.fullscreen || controller.scout.working(now))
    ) {
      const stage = controller.stage;
      const effect = controller.desktopReactions.draw(
        canvas?.getContext("2d") ?? null,
        stage?.bounds ?? null,
        now,
        locale.t.companion.pastedStamp,
        controller.escort.caret !== null,
      );
      if (effect !== null) stage?.includePainted(effect);
    }
    keepsakes?.tick(now);
    place(now);
  }

  onMount(() => {
    document.documentElement.classList.add("companion-layer");
    // Живая отладка в режиме разработки: контроллер спутника через консоль WebView2.
    if (import.meta.env.DEV) Reflect.set(window, "companionDebug", controller);
    if (canvas === undefined) return;
    const stage = new CompanionStage(canvas);
    controller.stage = stage;
    stage.resize(innerWidth, innerHeight);
    void stage.load(settings.height);
    const unlisten = subscribe(
      controller,
      () => settings,
      () => menu !== null,
      change,
    );
    void tauriPorts.world().then((raw) => {
      if (raw !== null) controller.onWorld(raw);
    });
    // Только своя настройка: тема, раскладка и прочее главного окна кадры не перезагружают.
    const onStorage = (event: StorageEvent): void => {
      if (event.key !== COMPANION_KEY) return;
      const next = loadSettings(window.localStorage);
      if (next.height !== settings.height) void stage.load(next.height);
      settings = next;
      controller.setSettings(next);
    };
    // На общем канале окон теперь и чек-лист: позы перезагружаются только по «pack».
    const onPack = (event: MessageEvent): void => {
      if (event.data === "pack") void stage.load(settings.height);
    };
    const stopChecklist = serveChecklist(() =>
      controller.settings.when === "off" ? null : checklist(controller, performance.now()),
    );
    const onResize = (): void => {
      controller.presence.scale = devicePixelRatio || 1;
      stage.resize(innerWidth, innerHeight);
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener("resize", onResize);
    characterChannel?.addEventListener("message", onPack);
    let last = performance.now();
    let handle = requestAnimationFrame(function loop(now) {
      // Ошибка одного кадра не должна останавливать спутника навсегда: следующий кадр — всё равно.
      handle = requestAnimationFrame(loop);
      // Ресурсы (COMPANION.md, часть IV): не по частоте монитора (до 144), а сколько нужно.
      if (now - last < 1000 / controller.fps()) return;
      try {
        frame((now - last) / 1000, now);
      } catch (error) {
        console.error("[companion] кадр", error);
      }
      last = now;
    });
    return () => {
      cancelAnimationFrame(handle);
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("resize", onResize);
      characterChannel?.removeEventListener("message", onPack);
      stopChecklist();
      for (const one of unlisten)
        void one.then((stop) => {
          stop();
        });
    };
  });
  return {
    controller,
    openMain,
    change,
    behave,
    ...pointerHandlers(
      controller,
      () => canvas,
      () => {
        menu = null;
      },
      openMain,
    ),
    get canvas() {
      return canvas;
    },
    set canvas(value: HTMLCanvasElement | undefined) {
      canvas = value;
    },
    get keepsakes() {
      return keepsakes;
    },
    set keepsakes(value: DeskBindings | undefined) {
      keepsakes = value;
    },
    get bubbleEl() {
      return bubbleEl;
    },
    set bubbleEl(value: HTMLParagraphElement | null) {
      bubbleEl = value;
    },
    toggleChecklist,
    get checks() {
      return checks;
    },
    get checklistEl() {
      return checklistEl;
    },
    set checklistEl(value: HTMLDivElement | null) {
      checklistEl = value;
    },
    get menuEl() {
      return menuEl;
    },
    set menuEl(value: HTMLElement | undefined) {
      menuEl = value;
    },
    get radioEl() {
      return radioEl;
    },
    set radioEl(value: HTMLDivElement | null) {
      radioEl = value;
    },
    get menu() {
      return menu;
    },
    set menu(value: { x: number; y: number } | null) {
      menu = value;
    },
    get bubble() {
      return bubble;
    },
    get settings() {
      return settings;
    },
    get radio() {
      return radio;
    },
    get radioAt() {
      return radioAt;
    },
  };
}
export type CompanionView = ReturnType<typeof createView>;
