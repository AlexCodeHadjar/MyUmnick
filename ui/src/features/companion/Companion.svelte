<script lang="ts">
  import { locale, isLang } from "../../core";
  // Слой «Сопровождения» (Этап 23, ADR-0045): спутник поверх экрана. Картину окон и зов присылает
  // оболочка, речь и эмоцию — главное окно (`companion-feed`): к ядру слой не подключается.
  import { invoke } from "@tauri-apps/api/core";
  import { listen, type UnlistenFn } from "@tauri-apps/api/event";
  import { onMount } from "svelte";

  import { EMOTION_HUE } from "../avatar/orb/palette";
  import { characterChannel } from "../avatar/portrait/picture";
  import { floorSpot, ICONS, snap, type Spot } from "./anchors";
  import { Life } from "./life";
  import { Brain } from "./brain";
  import {
    bubbleText,
    dropTarget,
    followSpot,
    hostOf,
    placeBubble,
    release,
    velocityOf,
  } from "./control";
  import {
    COMPANION_KEY,
    HEIGHTS,
    loadSettings,
    saveSettings,
    shouldShow,
    type CompanionBehavior,
    type CompanionSettings,
  } from "./settings";
  import { CANVAS_RATIO } from "./pack";
  import { choosePoke, remark, topicOf, type RemarkTopic, type Target } from "./remarks";
  import { Mind, type ActivityId, type Senses, type VoiceKind } from "./mind";
  import { sendRadioCommand, type RadioFeed, type RadioMode } from "../radio";
  import { Reactions } from "./reactions";
  import { keepWatching, mediaVideo, pickMedia, watching, type Media } from "./watch";
  import { watchPhrases } from "./phrases";
  import { CompanionStage } from "./stage";
  import { rectToCss, worldToCss, type Focus, type Rect, type World } from "./world";

  interface Feed {
    mouth: number;
    speaking: boolean;
    emotion: string;
    text: string;
    lang: string;
    radio?: RadioFeed;
  }

  const HOLD_MS = 150;
  const MOVE_PX = 6;

  let canvas: HTMLCanvasElement | undefined = $state();
  let settings = $state<CompanionSettings>(loadSettings(window.localStorage));
  let bubble = $state<{ text: string; x: number; y: number } | null>(null);
  /** Облачко на экране: его размер прошлого кадра держит текст в пределах экрана. */
  let bubbleEl = $state<HTMLParagraphElement | null>(null);
  let menu = $state<{ x: number; y: number } | null>(null);
  // Радио (ADR-0049): табличка над головой — станция и ⏮ ⏯ ⏭; кнопки шлют команды главному окну.
  let radio = $state<RadioFeed | null>(null);
  let radioAt = $state<{ x: number; y: number } | null>(null);
  let radioEl = $state<HTMLDivElement | null>(null);

  const brain = new Brain();
  let stage: CompanionStage | null = null;
  let world: World | null = null;
  let scale = devicePixelRatio || 1;
  let mainShown = true;
  let mainRect: Rect | null = null;
  /** Монитор слоя в физических пикселях: окно приложения приходит в них же. */
  let monitor: Rect | null = null;
  let shown = false;
  let lastFocus = "";
  let attachedHost: number | null = null;
  const look = { mouth: 0, speaking: false, hue: EMOTION_HUE.neutral, attention: 0 };
  let replyText = "";
  let bubbleUntil = 0;
  let listening = false;
  // «Разум» (MIND.md, ADR-0051): одно место, где решается, что делать и когда говорить.
  const mind = new Mind();
  let assistant = false;
  /** Фраза о программе (привычка дня, «мечешься») для ближайшего «поговорить». */
  let topicLine: string | null = null;
  let watchLineAt = 0;
  /** Когда последний раз двигалась мышь: пользователь занят — общаться хочется меньше. */
  let movedAt = 0;
  let lastRemark = "";
  let topic: RemarkTopic = "other";
  let poking = false;
  /** Куда закрепится при отпускании перетаскиваемого персонажа. */
  let drop: Spot | null = null;
  let onDesktop = false;
  let icons: Target[] = [];
  // Триггеры и реакции (BEHAVIOR §3): тряска, бросок, возвращение, ночь, поглаживания.
  const reactions = new Reactions(brain, (text, kind) => {
    speak(text, kind);
  });
  // Настроение, привычки, сайты, любимый значок (BEHAVIOR §2, §4.4, §5, §6).
  const life = new Life(brain, window.localStorage);
  reactions.onMood = (event) => {
    life.event(event);
  };
  // «Смотрим вместе» (BEHAVIOR §11): выбранная вкладка браузера, проверка раз в секунду.
  let tab: string | null = null;
  let tabAt = 0;
  let cornerPending = false;
  // Что играет в системе (ADR-0052): опрос раз в 2 с; пауза — часть просмотра.
  let media: Media = { state: "none", app: "" };
  let mediaAt = 0;
  let mediaBusy = false;
  let pausedSince = 0;
  let cursor: { x: number; y: number } | null = null;
  let cursorFedAt = 0;
  let lastPhase = brain.phase;
  // Мышь: удержание — молния, движение сразу — «держат», как у Capri.
  let press: { x: number; y: number; t: number } | null = null;
  let gesture: "none" | "held" | "aim" = "none";
  let aim: { x: number; y: number; ghost: Spot | null } | null = null;
  let trail: { x: number; y: number; t: number }[] = [];
  let lastHit = "";

  function css(next: World): World {
    return worldToCss(next, scale);
  }

  function applyBehavior(): void {
    // Когда гулять, решает «Разум» (MIND §4), а не таймер тела.
    brain.wander = false;
    brain.calm = settings.behavior === "follow";
    brain.chest = settings.height * 0.55;
    brain.figure = settings.height * CANVAS_RATIO;
  }

  async function setShown(next: boolean): Promise<void> {
    if (next === shown) return;
    shown = next;
    if (next) {
      await invoke("companion_set", { visible: true });
      arrive();
      // Вышел из портала — поздоровался (T6).
      setTimeout(() => {
        reactions.greet(performance.now() / 1000);
      }, 900);
      return;
    }
    if (world?.fullscreen) {
      brain.hide();
      await invoke("companion_set", { visible: false });
      return;
    }
    brain.portalIn();
  }

  /** Окно хоть частью на мониторе слоя (физические пиксели экрана). */
  function onScreen(rect: Rect): boolean {
    const m = monitor;
    if (m === null) return rect.x > -10000 && rect.y > -10000;
    return (
      rect.x + rect.w > m.x && rect.y + rect.h > m.y && rect.x < m.x + m.w && rect.y < m.y + m.h
    );
  }

  /** Ушли из окна: выходим из портала там, где было окно (внутри экрана); иначе — сразу на место. */
  function arrive(): void {
    if (world === null) return;
    const surfaceList = brain.surfaceList;
    const m = world.monitor;
    if (mainRect !== null && !mainShown) {
      const rect = rectToCss(mainRect, monitor ?? { x: 0, y: 0, w: 0, h: 0 }, scale);
      const x = Math.min(m.x + m.w - 80, Math.max(m.x + 80, rect.x + rect.w * 0.75));
      const y = Math.min(m.y + m.h - 80, Math.max(m.y + 260, rect.y + rect.h * 0.5));
      brain.portalOut(x, y);
      return;
    }
    const spot =
      followSpot(world, surfaceList, world.focus) ??
      followSpot(world, surfaceList, { kind: "desktop" });
    if (spot !== null) brain.portalOut(spot.x, spot.y - 20);
  }

  function refresh(): void {
    applyBehavior();
    void setShown(shouldShow(settings, mainShown));
  }

  function onWorld(raw: World): void {
    const before = monitor;
    monitor = raw.monitor;
    world = css(raw);
    brain.setWorld(world);
    // Пользователь перешёл на другой монитор — спутник переходит туда же через портал.
    const moved =
      before !== null &&
      (before.x !== raw.monitor.x || before.y !== raw.monitor.y || before.w !== raw.monitor.w);
    if (moved && shown && gesture === "none") {
      // Портал — на новом мониторе, а не там, где было окно приложения на старом.
      mainRect = null;
      brain.hide();
      arrive();
    }
    refresh();
    // Показали раньше, чем пришла картина окон: выйти сейчас (иначе персонаж так и не появлялся).
    if (shown && brain.phase === "hidden") arrive();
    const key = JSON.stringify(raw.focus);
    if (key !== lastFocus) {
      lastFocus = key;
      noticeTopic(world.focus);
      void enterDesktop(world.focus.kind === "desktop");
    }
  }

  /** Радио сменило состояние: поёт или слушает, фраза на включение, смену станции, паузу, выключение. */
  function onRadio(next: RadioFeed | null, speaking: boolean): void {
    const before: RadioMode = radio?.mode ?? "off";
    const mode: RadioMode = next?.mode ?? "off";
    brain.music = mode === "playing" ? "playing" : mode === "off" ? "off" : "paused";
    const lines = locale.t.radio.lines;
    const list =
      before === "off" && mode !== "off"
        ? lines.start
        : before !== "off" && mode === "off"
          ? lines.stop
          : before === "playing" && mode === "paused"
            ? lines.pause
            : next !== null && radio !== null && next.title !== radio.title
              ? lines.switch
              : null;
    const line = list?.[Math.floor(Math.random() * list.length)];
    if (line !== undefined && shown) speak(line, "reaction");
    radio = mode === "off" ? null : next;
    // Поёт: рот — по громкости потока, «говорит» — значит, не комментирует и не гуляет.
    if (mode === "playing" && next !== null && !speaking) {
      look.mouth = next.level;
      look.speaking = true;
    }
  }

  function onFeed(feed: Feed): void {
    if (isLang(feed.lang) && locale.lang !== feed.lang) locale.set(feed.lang);
    look.mouth = feed.mouth;
    look.speaking = feed.speaking;
    assistant = feed.speaking;
    onRadio(feed.radio ?? null, feed.speaking);
    const hue = new Map<string, number>(Object.entries(EMOTION_HUE)).get(feed.emotion);
    look.hue = hue ?? EMOTION_HUE.neutral;
    if (feed.speaking) {
      brain.wake();
      listening = false;
      // Новый ответ ассистента — с ним говорят, радость чуть растёт (BEHAVIOR §2).
      if (
        feed.text !== replyText &&
        replyText !== lastRemark &&
        feed.text.length < replyText.length
      )
        life.event("talk");
      replyText = feed.text;
      bubbleUntil = performance.now() + 4000;
    }
  }

  function onCalled(): void {
    // Зов «Умник», пока спутник на экране (решение пользователя): облачко вместо окна.
    listening = true;
    look.attention = 1;
    bubbleUntil = performance.now() + 5000;
    brain.wake();
  }

  function sendHit(): void {
    const box = stage?.bounds ?? null;
    const capture = gesture !== "none" || menu !== null;
    const hit = settings.hologram || box === null ? null : withCard(box);
    const key = JSON.stringify([
      hit && [Math.round(hit.x), Math.round(hit.y), Math.round(hit.w)],
      capture,
    ]);
    if (key === lastHit) return;
    lastHit = key;
    void invoke("companion_hit", { hit, capture });
  }

  /** Табличка радио — тоже область кликов слоя (её кнопки нажимаются). */
  function withCard(box: Rect): Rect {
    if (radioEl === null) return box;
    const card = radioEl.getBoundingClientRect();
    const x = Math.min(box.x, card.left);
    const y = Math.min(box.y, card.top);
    const w = Math.max(box.x + box.w, card.right) - x;
    const h = Math.max(box.y + box.h, card.bottom) - y;
    return { x, y, w, h };
  }

  function syncHost(): void {
    const host = hostOf(brain.spot);
    if (host === attachedHost) return;
    attachedHost = host;
    void invoke("companion_attach", { host });
  }

  /** Рабочий стол: значки — опоры и цели; спутник садится на них и иногда перепрыгивает или тычет. */
  async function enterDesktop(desktop: boolean): Promise<void> {
    onDesktop = desktop;
    if (!desktop) {
      icons = [];
      brain.setIcons([]);
      return;
    }
    await refreshIcons();
  }

  async function refreshIcons(): Promise<void> {
    if (monitor === null) return;
    const origin = monitor;
    const found = await invoke<Target[]>("companion_targets").catch(() => []);
    if (!onDesktop) return;
    icons = found
      .filter((one) => one.kind === "item")
      .map((one) => ({ ...one, rect: rectToCss(one.rect, origin, scale) }));
    brain.setIcons(icons.map((one) => one.rect));
  }

  /** «Прыжок по значкам» (MIND §4): перепрыгнуть на значок с репликой или ткнуть в него. */
  async function hop(): Promise<void> {
    await refreshIcons();
    const chosen = life.icon(icons);
    if (chosen === undefined || brain.phase !== "rest" || gesture !== "none") return;
    if (Math.random() < 0.4) {
      void poke();
      return;
    }
    const spot = snap(brain.surfaceList, chosen.rect.x + chosen.rect.w / 2, chosen.rect.y + 6, 30);
    if (spot === null) return;
    brain.goTo(spot);
    const lines = locale.t.companion.perch;
    const perch = lines[Math.floor(Math.random() * lines.length)];
    const line = life.iconLine(chosen.name, icons.length) ?? perch?.(chosen.name);
    if (line !== undefined) speak(line, "reaction");
  }

  /** Сменилась программа — стимул «Разуму» (MIND §3.3): сам решит, идти ли к окну и что сказать. */
  function noticeTopic(focus: Focus): void {
    const app = focus.kind === "desktop" ? "" : focus.app;
    const next = topicOf(app, focus.kind === "desktop");
    const now = performance.now() / 1000;
    mind.feel("focus", now);
    if (next === topic) return;
    topic = next;
    tab = null;
    tabAt = 0;
    // Первый раз за день в программе или мечется — фраза для ближайшего «поговорить» (BEHAVIOR §4.4).
    topicLine = life.focus(next, now) ?? topicLine;
  }

  /**
   * Предложить фразу голосу «Разума» (MIND §3.5): когда сказать — решает он. Смотрим фильм — только
   * ответы на ваши действия и фразы самого просмотра (`watchLine`): ни тычков, ни реакций на мышь.
   */
  function speak(text: string, kind: VoiceKind, watchLine = false): void {
    if (text === "" || (brain.watching && kind !== "direct" && !watchLine)) return;
    mind.voice.offer(text, kind, performance.now() / 1000);
  }

  /** Показать фразу в облачке (её отпустил голос). */
  function show(text: string, now: number): void {
    listening = false;
    replyText = text;
    bubbleUntil = now + 6000;
    lastRemark = text;
  }

  function pickOne(list: readonly string[]): string {
    return list[Math.floor(Math.random() * list.length)] ?? "";
  }

  function appName(): string {
    const focus = world?.focus;
    return focus === undefined || focus.kind === "desktop" ? "" : focus.app;
  }

  /** Название выбранной вкладки браузера (UI Automation): по нему видно, что идёт видео. */
  async function refreshTab(): Promise<void> {
    const found = await invoke<Target[]>("companion_targets").catch(() => []);
    if (topic !== "browser") return;
    tab = found.find((one) => one.kind === "tab" && one.selected === true)?.name ?? null;
  }

  /** Что видит спутник в этом кадре — сырьё для «Разума» (сглаживает он сам). */
  function senses(now: number): Senses {
    if (topic === "browser" && now >= tabAt) {
      tabAt = now + 15_000;
      void refreshTab();
    }
    // Полный экран — у браузера, плеера, игры или незнакомой программы. Развёрнутые на весь экран чат,
    // редактор, офис (панель задач скрыта) — обычные окна, а не «тихо в углу» (проверено вживую 2026-11-17).
    const wide = topic === "browser" || topic === "video" || topic === "game" || topic === "other";
    const fullscreen = shown && wide && (world?.fullscreen ?? false);
    pollMedia(now);
    const focusVideo = watching({ app: appName(), topic, fullscreen, tab });
    const playing = keepWatching({
      media,
      pausedS: media.state === "paused" ? (now - pausedSince) / 1000 : 0,
      tab,
      focusVideo:
        focusVideo || (mediaVideo(media, tab) && (topic === "browser" || topic === "video")),
      already: brain.watching,
    });
    return {
      resting: shown && brain.phase === "rest" && gesture === "none" && !poking,
      listening: assistant || listening,
      singing: shown && brain.music === "playing",
      // Видео: признаки в фокусе (плеер, видеосайт, полный экран) или то, что играет в системе.
      video: shown && (focusVideo || playing),
      fullscreen,
      desktop: onDesktop,
      behavior: settings.behavior,
      energy: life.mood.energy,
      userBusy: now - movedAt < 60_000,
      hour: new Date().getHours(),
      calm: settings.calm || brain.watching,
    };
  }

  /** Раз в 2 с — что играет в системе; пауза и продолжение во время просмотра — реплика. */
  function pollMedia(now: number): void {
    if (mediaBusy || now < mediaAt) return;
    mediaAt = now + 2000;
    mediaBusy = true;
    void invoke<Media[]>("companion_media")
      .catch((): Media[] => [])
      .then((list) => {
        const next = pickMedia(list, tab);
        mediaBusy = false;
        const before = media.state;
        media = next;
        if (next.state === "paused" && before !== "paused") pausedSince = performance.now();
        if (!brain.watching) return;
        const lines = watchPhrases(locale.lang);
        if (before === "playing" && next.state === "paused")
          speak(pickOne(lines.pause), "reaction", true);
        if (before === "paused" && next.state === "playing")
          speak(pickOne(lines.resume), "reaction", true);
      });
  }

  /** Исполнить действие, выбранное «Разумом» (MIND §4), и выйти из прежнего. */
  function act(id: ActivityId, previous: string, now: number): void {
    if (previous === "watch") {
      brain.watching = false;
      speak(pickOne(watchPhrases(locale.lang).end), "reaction");
    }
    if (previous === "hush") {
      brain.quiet = false;
      // Вышли из полного экрана (T14) — по сглаженному факту «Разума», а не по миганию сигнала.
      reactions.fire("back", now / 1000);
    }
    if ((previous === "watch" || previous === "hush") && world !== null && gesture === "none") {
      const home = followSpot(world, brain.surfaceList, world.focus);
      if (home !== null) brain.goTo(home);
    }
    if (id === "watch" || id === "hush") {
      brain.watching = id === "watch";
      brain.quiet = id === "hush";
      cornerPending = true;
      // Первая тихая реплика — через 4–7 мин, дальше реже (BEHAVIOR §11.2).
      watchLineAt = now + (240 + Math.random() * 180) * 1000;
      if (id === "watch") speak(pickOne(watchPhrases(locale.lang).start), "reaction", true);
      else if (Math.random() < 0.5) speak(pickOne(locale.t.companion.watch.quiet), "reaction");
    } else if (id === "follow") goFollow();
    else if (id === "chat") void chat();
    else if (id === "poke") void poke();
    else if (id === "hop") void hop();
    else if (id === "wander") brain.stroll();
  }

  function goFollow(): void {
    if (world === null) return;
    const spot = followSpot(world, brain.surfaceList, world.focus);
    if (spot !== null && hostOf(spot) !== hostOf(brain.spot)) brain.goTo(spot);
  }

  /** «Поговорить»: фраза о программе, привычке, сайте или по настроению. */
  async function chat(): Promise<void> {
    const ready = topicLine ?? life.remark(topic);
    topicLine = null;
    if (ready !== null) {
      speak(ready, "ambient");
      return;
    }
    const hour = new Date().getHours();
    let line: string | null = null;
    if (topic === "browser") {
      const found = await invoke<Target[]>("companion_targets").catch(() => []);
      line = life.browser(found.filter((one) => one.kind === "tab").map((one) => one.name));
    }
    line ??= remark(locale.t, { topic, hour, idleS: brain.idleSeconds }, Math.random, lastRemark);
    speak(line, "ambient");
  }

  /** Раз в кадр: решение «Разума», режимы в углу, голос. */
  function think(now: number): void {
    const choice = mind.update(now / 1000, senses(now));
    if (choice !== null) act(choice.id, choice.previous, now);
    if (cornerPending && brain.phase === "rest" && gesture === "none") {
      cornerPending = false;
      const corner = floorSpot(brain.surfaceList, true);
      if (corner !== null) brain.goTo(corner);
    }
    // Смотрим вместе: редкая тихая реплика, если голос разрешит.
    if (brain.watching && now >= watchLineAt) {
      watchLineAt = now + (480 + Math.random() * 360) * 1000;
      speak(pickOne(watchPhrases(locale.lang).during), "ambient", true);
    }
    // Дошёл, допрыгнул, долез — 2–4 с «осматривается», выходки не начинаются (MIND §3.4).
    if (brain.phase === "rest" && lastPhase !== "rest" && lastPhase !== "hidden") {
      mind.settle(now / 1000, 2 + Math.random() * 2);
    }
    const line = mind.voice.next(now / 1000, {
      blocked: !shown || assistant || listening || gesture !== "none",
      bubble: now < bubbleUntil,
    });
    if (line !== null) show(line, now);
  }

  /** Подлететь к элементу экрана, ткнуть, сказать его название и вернуться. Нечего тыкать — фраза. */
  async function poke(): Promise<void> {
    if (world === null || monitor === null) return;
    poking = true;
    const origin = monitor;
    const found = await invoke<Target[]>("companion_targets").catch(() => []);
    const near = choosePoke(
      found.map((one) => ({ ...one, rect: rectToCss(one.rect, origin, scale) })),
      world.monitor,
    );
    if (near === null || brain.phase !== "rest" || !shown) {
      poking = false;
      const hour = new Date().getHours();
      const idleS = brain.idleSeconds;
      speak(remark(locale.t, { topic, hour, idleS }, Math.random, lastRemark), "ambient");
      return;
    }
    const back = brain.spot;
    brain.visit(near.x, near.y, "poke", near.facing);
    const lines = locale.t.companion.poke;
    const line = lines[Math.floor(Math.random() * lines.length)];
    if (line !== undefined) speak(line(near.name), "reaction");
    setTimeout(() => {
      poking = false;
      if (brain.phase !== "rest" || gesture !== "none") return;
      const home =
        back ?? (world === null ? null : followSpot(world, brain.surfaceList, { kind: "desktop" }));
      if (home !== null) brain.goTo(home);
    }, 5200);
  }

  function updateBubble(now: number): void {
    let box = stage?.bounds;
    radioAt = null;
    if (box !== null && box !== undefined && radio !== null) {
      // Табличка — над головой; облачко — над табличкой.
      const card =
        radioEl === null ? { w: 230, h: 58 } : { w: radioEl.offsetWidth, h: radioEl.offsetHeight };
      radioAt = placeBubble(box, card, { w: innerWidth, h: innerHeight });
      box = { ...box, y: radioAt.y - 6 - box.h * 0.08 };
    }
    const text = listening ? locale.t.companion.listening : bubbleText(replyText);
    if (box === null || box === undefined || now > bubbleUntil || text === "") {
      bubble = null;
      return;
    }
    const size =
      bubbleEl === null ? { w: 280, h: 60 } : { w: bubbleEl.offsetWidth, h: bubbleEl.offsetHeight };
    const at = placeBubble(box, size, { w: innerWidth, h: innerHeight });
    bubble = { text, x: at.x, y: at.y };
  }

  function frame(dt: number, now: number): void {
    think(now);
    // Своя инициатива — фраза в облачке или «тыканье»: на мышь в это время не смотрит.
    brain.busy = poking || (!listening && now < bubbleUntil && replyText === lastRemark);
    if (press !== null && gesture === "none" && now - press.t >= HOLD_MS) {
      gesture = "aim";
      aim = { x: press.x, y: press.y, ghost: null };
    }
    brain.tick(dt);
    reactions.tick(now / 1000);
    const long = life.tick(now / 1000);
    if (long !== null) speak(long, "ambient");
    if (brain.phase === "climb" && lastPhase !== "climb") reactions.climbing();
    lastPhase = brain.phase;
    // Курсор стоит — событий нет, а «что смотришь?» (T8) ждёт 4 с: подкармливаем 4 раза в секунду.
    if (cursor !== null && now - cursorFedAt > 250) {
      cursorFedAt = now;
      reactions.cursor(cursor.x, cursor.y, now / 1000, shown);
    }
    look.attention = Math.max(0, look.attention - dt * 0.8);
    const body = brain.body();
    // Где закрепится, если отпустить: кольцо у опоры (перетаскивание и молния).
    const mark = gesture === "held" ? drop : (aim?.ghost ?? null);
    if (mark !== null)
      body.effects = [...body.effects, { kind: "mark", x: mark.x, y: mark.y, t: 0 }];
    if (aim !== null) {
      body.effects = [
        ...body.effects,
        { kind: "bolt", from: [brain.x, brain.y - brain.chest], to: [aim.x, aim.y], t: 0 },
      ];
    }
    stage?.draw(body, look, dt);
    if (brain.phase === "hidden" && !shown) void invoke("companion_set", { visible: false });
    sendHit();
    syncHost();
    updateBubble(now);
  }

  function down(event: PointerEvent): void {
    if (event.button !== 0 || canvas === undefined) return;
    menu = null;
    press = { x: event.clientX, y: event.clientY, t: performance.now() };
    trail = [{ ...press }];
    try {
      canvas.setPointerCapture(event.pointerId);
    } catch {
      // Указатель уже отпущен (короткий клик) — захват не нужен.
    }
    brain.wake();
  }

  function move(event: PointerEvent): void {
    if (press === null) return;
    const now = performance.now();
    trail = [
      ...trail.filter((p) => now - p.t < 200),
      { x: event.clientX, y: event.clientY, t: now },
    ];
    const moved = Math.hypot(event.clientX - press.x, event.clientY - press.y);
    if (gesture === "none" && moved > MOVE_PX) {
      gesture = "held";
      brain.hold(event.clientX, event.clientY);
    }
    if (gesture === "held") {
      brain.moveHeld(event.clientX, event.clientY);
      reactions.held(event.clientX, event.clientY, now / 1000);
      drop = dropTarget(brain.surfaceList, event.clientX, event.clientY);
    }
    if (gesture === "aim") {
      const ghost = dropTarget(brain.surfaceList, event.clientX, event.clientY);
      aim = { x: ghost?.x ?? event.clientX, y: ghost?.y ?? event.clientY, ghost };
    }
  }

  function up(event: PointerEvent): void {
    if (press === null) return;
    if (gesture === "held") {
      const point = {
        x: event.clientX,
        y: event.clientY,
        shift: event.shiftKey,
        ctrl: event.ctrlKey,
      };
      const velocity = velocityOf(trail);
      reactions.released(Math.hypot(velocity.vx, velocity.vy), performance.now() / 1000);
      const done = release(brain.surfaceList, point, velocity);
      if (done.kind === "place") brain.place(done.spot);
      else if (done.kind === "hang") brain.hang(done.x, done.y);
      else brain.toss(done.vx, done.vy);
    } else if (gesture === "none") {
      // Короткий клик без движения — погладить (удержание — молния, движение — «держат»).
      petNow(performance.now());
    } else if (aim !== null) {
      // Отпустили на самом персонаже — отмена; иначе — разряд по молнии к цели.
      if (Math.hypot(aim.x - brain.x, aim.y - (brain.y - brain.chest)) > 60)
        brain.bolt(aim.ghost, [aim.x, aim.y]);
    }
    press = null;
    gesture = "none";
    aim = null;
    drop = null;
    trail = [];
  }

  /** Погладили: сердечки, прыжок радости; чем чаще гладят подряд — тем довольнее реплика. */
  function petNow(now: number): void {
    brain.pet();
    look.attention = Math.max(look.attention, 0.5);
    reactions.pet(now / 1000);
    // Гладят на значке — значок становится любимее (BEHAVIOR §6).
    const spot = brain.spot;
    if (spot?.surface.kind === "edge" && spot.surface.host === ICONS) {
      const under = icons.find(
        (one) => brain.x >= one.rect.x - 10 && brain.x <= one.rect.x + one.rect.w + 10,
      );
      if (under !== undefined) life.petOn(under.name);
    }
  }

  function cancelAim(event: KeyboardEvent): void {
    if (event.key !== "Escape") return;
    menu = null;
    if (gesture === "aim") {
      press = null;
      gesture = "none";
      aim = null;
    }
  }

  function change(next: Partial<CompanionSettings>): void {
    settings = { ...settings, ...next };
    saveSettings(window.localStorage, settings);
    if (next.height !== undefined) void stage?.load(settings.height);
    refresh();
  }

  function behave(behavior: CompanionBehavior): void {
    change({ behavior });
    menu = null;
  }

  onMount(() => {
    document.documentElement.classList.add("companion-layer");
    // Живая отладка в режиме разработки: состояние тела и «Разума» через консоль WebView2.
    if (import.meta.env.DEV) {
      Reflect.set(window, "companionDebug", {
        brain,
        mind,
        state: () => ({ shown, mainShown, world, phase: brain.phase, x: brain.x, y: brain.y }),
      });
    }
    if (canvas === undefined) return;
    const created = new CompanionStage(canvas);
    stage = created;
    created.resize(innerWidth, innerHeight);
    void created.load(settings.height);
    const unlisten: Promise<UnlistenFn>[] = [
      listen<World>("companion-world", (event) => {
        onWorld(event.payload);
      }),
      listen<[number, Rect | null]>("companion-host", (event) => {
        const [id, rect] = event.payload;
        if (world === null) return;
        const css = rect === null ? null : rectToCss(rect, world.monitor, scale);
        brain.hostMoved(id, css);
        if (id === attachedHost) reactions.host(css, performance.now() / 1000);
      }),
      listen<{ shown: boolean; focused: boolean; rect: Rect }>("companion-main", (event) => {
        // «Ушли» из окна — свернули его или переключились на другую программу: спутник выходит.
        mainShown = event.payload.shown && event.payload.focused;
        // Свёрнутое окно Windows уносит к (−32000, −32000): портал там не открыть — помним последнее
        // видимое место окна (из-за этого персонаж иногда «не появлялся», падая из-за края экрана).
        if (event.payload.shown && onScreen(event.payload.rect)) mainRect = event.payload.rect;
        refresh();
      }),
      listen("companion-called", onCalled),
      listen<[number, number]>("companion-cursor", (event) => {
        brain.cursorX = event.payload[0];
        cursor = { x: event.payload[0], y: event.payload[1] };
        cursorFedAt = performance.now();
        movedAt = cursorFedAt;
        reactions.cursor(cursor.x, cursor.y, cursorFedAt / 1000, shown);
      }),
      listen<Feed>("companion-feed", (event) => {
        onFeed(event.payload);
      }),
    ];
    void invoke<World | null>("companion_world").then((raw) => {
      if (raw !== null) onWorld(raw);
    });
    // Только своя настройка: тема, раскладка и прочее главного окна кадры не перезагружают (это и
    // была заметная задержка — 48 картинок заново на каждое сохранение).
    const onStorage = (event: StorageEvent): void => {
      if (event.key !== COMPANION_KEY) return;
      const next = loadSettings(window.localStorage);
      const resized = next.height !== settings.height;
      settings = next;
      if (resized) void stage?.load(settings.height);
      refresh();
    };
    const onPack = (): void => {
      void stage?.load(settings.height);
    };
    const onResize = (): void => {
      scale = devicePixelRatio || 1;
      stage?.resize(innerWidth, innerHeight);
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener("resize", onResize);
    characterChannel?.addEventListener("message", onPack);
    let last = performance.now();
    let handle = requestAnimationFrame(function loop(now) {
      frame((now - last) / 1000, now);
      last = now;
      handle = requestAnimationFrame(loop);
    });
    return () => {
      cancelAnimationFrame(handle);
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("resize", onResize);
      characterChannel?.removeEventListener("message", onPack);
      for (const one of unlisten)
        void one.then((stop) => {
          stop();
        });
    };
  });
</script>

<svelte:window onkeydown={cancelAim} />

<canvas
  bind:this={canvas}
  class="layer"
  onpointerdown={down}
  onpointermove={move}
  onpointerup={up}
  ondblclick={() => void invoke("main_show")}
  oncontextmenu={(event) => {
    event.preventDefault();
    menu = { x: event.clientX, y: event.clientY };
  }}
></canvas>

{#if bubble !== null}
  <p
    class="bubble"
    bind:this={bubbleEl}
    style:left={`${String(bubble.x)}px`}
    style:top={`${String(bubble.y)}px`}
  >
    {bubble.text}
  </p>
{/if}

{#if radio !== null && radioAt !== null}
  <div
    class="radio-card"
    bind:this={radioEl}
    style:left={`${String(radioAt.x)}px`}
    style:top={`${String(radioAt.y)}px`}
  >
    <span class="station" class:long={radio.title.length > 24} title={radio.title}>
      <span
        >♪ {radio.mode === "loading"
          ? locale.t.radio.loading
          : radio.mode === "failed"
            ? locale.t.radio.failed
            : radio.title}</span
      >
    </span>
    <span class="buttons">
      <button
        type="button"
        title={locale.t.radio.prev}
        onclick={() => {
          sendRadioCommand("prev");
        }}>⏮</button
      >
      <button
        type="button"
        title={radio.mode === "playing" ? locale.t.radio.pause : locale.t.radio.play}
        onclick={() => {
          sendRadioCommand("toggle");
        }}>{radio.mode === "playing" || radio.mode === "loading" ? "⏸" : "▶"}</button
      >
      <button
        type="button"
        title={locale.t.radio.next}
        onclick={() => {
          sendRadioCommand("next");
        }}>⏭</button
      >
    </span>
  </div>
{/if}

{#if menu !== null}
  <div
    class="menu u-frame"
    role="menu"
    style:left={`${String(menu.x)}px`}
    style:top={`${String(menu.y)}px`}
  >
    {#each [["follow", locale.t.companion.follow], ["stay", locale.t.companion.stay], ["wander", locale.t.companion.wander]] as const as [value, label] (value)}
      <button
        type="button"
        role="menuitemradio"
        aria-checked={settings.behavior === value}
        onclick={() => {
          behave(value);
        }}>{settings.behavior === value ? "● " : "○ "}{label}</button
      >
    {/each}
    <hr />
    <p class="label">{locale.t.companion.size}</p>
    <div class="sizes">
      {#each HEIGHTS as height (height)}
        <button
          type="button"
          class:on={settings.height === height}
          onclick={() => {
            change({ height });
          }}>{height}</button
        >
      {/each}
    </div>
    <button
      type="button"
      role="menuitemcheckbox"
      aria-checked={settings.hologram}
      onclick={() => {
        change({ hologram: !settings.hologram });
        menu = null;
      }}>{settings.hologram ? "☑ " : "☐ "}{locale.t.companion.hologram}</button
    >
    <button
      type="button"
      role="menuitemcheckbox"
      aria-checked={settings.calm}
      onclick={() => {
        change({ calm: !settings.calm });
        menu = null;
      }}>{settings.calm ? "☑ " : "☐ "}{locale.t.companion.calm}</button
    >
    <hr />
    <button
      type="button"
      role="menuitem"
      onclick={() => {
        menu = null;
        void invoke("main_show");
      }}>{locale.t.companion.openWindow}</button
    >
    <button
      type="button"
      role="menuitem"
      onclick={() => {
        menu = null;
        change({ when: "off" });
      }}>{locale.t.companion.hide}</button
    >
  </div>
{/if}

<style>
  :global(html.companion-layer),
  :global(html.companion-layer body) {
    margin: 0;
    overflow: hidden;
    background: transparent;
    /* Текст спутника не выделяется ни кликом, ни протяжкой: это персонаж, а не страница. */
    user-select: none;
    -webkit-user-select: none;
  }

  .layer {
    /* Над персонажем — рука: его можно погладить (над пустым местом клики идут сквозь слой). */
    cursor: pointer;
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
  }

  .bubble {
    position: fixed;
    max-width: 280px;
    margin: 0;
    padding: 8px 12px;
    border-radius: 10px 10px 10px 2px;
    background: var(--panel);
    box-shadow: inset 0 0 0 1px var(--rule);
    color: var(--text);
    font-family: var(--font);
    font-size: 15px;
    line-height: 1.3;
    pointer-events: none;
    user-select: none;
    -webkit-user-select: none;
    overflow-wrap: anywhere;
  }

  .radio-card {
    position: fixed;
    display: flex;
    flex-direction: column;
    gap: 4px;
    align-items: center;
    width: 230px;
    padding: 6px 10px;
    border-radius: 12px;
    background: var(--panel);
    box-shadow: inset 0 0 0 1px var(--accent);
    color: var(--text);
    font-family: var(--font);
    font-size: 13px;
    user-select: none;
    -webkit-user-select: none;
  }

  .station {
    max-width: 100%;
    overflow: hidden;
    white-space: nowrap;
  }

  /* Длинное название — бегущей строкой. */
  .station.long > span {
    display: inline-block;
    padding-left: 100%;
    animation: marquee 9s linear infinite;
  }

  @keyframes marquee {
    to {
      transform: translateX(-100%);
    }
  }

  .buttons {
    display: flex;
    gap: 8px;
  }

  .buttons button {
    min-width: 34px;
    padding: 2px 8px;
    border: 1px solid var(--edge);
    border-radius: 8px;
    background: var(--plate);
    color: inherit;
    font: inherit;
    cursor: pointer;
  }

  .menu {
    position: fixed;
    z-index: 2;
    display: flex;
    flex-direction: column;
    min-width: 200px;
    padding: 6px;
    font-family: var(--font);
    font-size: 14px;
  }

  .menu button {
    padding: 5px 10px;
    border: none;
    background: none;
    color: var(--text);
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  .menu button:hover {
    background: var(--hover);
  }

  .label {
    margin: 2px 10px;
    color: var(--title);
    font-size: 12px;
    text-transform: uppercase;
  }

  .sizes {
    display: flex;
    gap: 4px;
    padding: 2px 8px 6px;
  }

  .sizes button {
    flex: 1;
    text-align: center;
    background: var(--plate);
  }

  .sizes button.on {
    box-shadow: inset 0 0 0 1px var(--value);
    color: var(--value);
  }

  hr {
    width: 100%;
    margin: 4px 0;
    border: none;
    border-top: 1px solid var(--rule-dim);
  }
</style>
