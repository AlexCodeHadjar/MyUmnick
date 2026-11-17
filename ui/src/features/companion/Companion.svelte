<script lang="ts">
  import { locale, isLang } from "../../core";
  // Слой «Сопровождения» (Этап 23, ADR-0045): спутник поверх экрана. Картину окон и зов присылает
  // оболочка, речь и эмоцию — главное окно (`companion-feed`): к ядру слой не подключается.
  import { invoke } from "@tauri-apps/api/core";
  import { listen, type UnlistenFn } from "@tauri-apps/api/event";
  import { onMount } from "svelte";

  import { EMOTION_HUE } from "../avatar/orb/palette";
  import { characterChannel } from "../avatar/portrait/picture";
  import { snap, type Spot } from "./anchors";
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
  import { choosePoke, nextPause, remark, topicOf, type RemarkTopic, type Target } from "./remarks";
  import { CompanionStage } from "./stage";
  import { rectToCss, worldToCss, type Focus, type Rect, type World } from "./world";

  interface Feed {
    mouth: number;
    speaking: boolean;
    emotion: string;
    text: string;
    lang: string;
  }

  const HOLD_MS = 150;
  const MOVE_PX = 6;
  const FOLLOW_DELAY_MS = 250;

  let canvas: HTMLCanvasElement | undefined = $state();
  let settings = $state<CompanionSettings>(loadSettings(window.localStorage));
  let bubble = $state<{ text: string; x: number; y: number } | null>(null);
  /** Облачко на экране: его размер прошлого кадра держит текст в пределах экрана. */
  let bubbleEl = $state<HTMLParagraphElement | null>(null);
  let menu = $state<{ x: number; y: number } | null>(null);

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
  let followTimer: ReturnType<typeof setTimeout> | undefined;
  let attachedHost: number | null = null;
  const look = { mouth: 0, speaking: false, hue: EMOTION_HUE.neutral, attention: 0 };
  let replyText = "";
  let bubbleUntil = 0;
  let listening = false;
  // Инициатива: сам говорит что-нибудь к месту (remarks.ts).
  let remarkAt = performance.now() + (40 + Math.random() * 50) * 1000;
  let lastRemark = "";
  let lastRemarkTime = 0;
  let topic: RemarkTopic = "other";
  let poking = false;
  /** Куда закрепится при отпускании перетаскиваемого персонажа. */
  let drop: Spot | null = null;
  let onDesktop = false;
  let icons: Target[] = [];
  let desktopAt = Infinity;
  /** Времена поглаживаний за последние 3 с. */
  let pets: number[] = [];
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
    // «Следовать» тоже иногда прогуливается сам (инициатива), «Сидеть здесь» — нет.
    brain.wander = settings.behavior !== "stay";
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
    void setShown(shouldShow(settings, mainShown, world?.fullscreen ?? false));
  }

  function onWorld(raw: World): void {
    monitor = raw.monitor;
    world = css(raw);
    brain.setWorld(world);
    refresh();
    // Показали раньше, чем пришла картина окон: выйти сейчас (иначе персонаж так и не появлялся).
    if (shown && brain.phase === "hidden") arrive();
    const key = JSON.stringify(raw.focus);
    if (key !== lastFocus) {
      lastFocus = key;
      scheduleFollow(world.focus);
      noticeTopic(world.focus);
      void enterDesktop(world.focus.kind === "desktop");
    }
  }

  function scheduleFollow(focus: Focus): void {
    clearTimeout(followTimer);
    // Быстрый Alt+Tab не дёргает спутника: переход — если окно осталось активным 0,25 с.
    followTimer = setTimeout(() => {
      if (world === null || settings.behavior !== "follow" || gesture !== "none") return;
      if (brain.phase !== "rest") return;
      const spot = followSpot(world, brain.surfaceList, focus);
      if (spot !== null && hostOf(spot) !== hostOf(brain.spot)) brain.goTo(spot);
    }, FOLLOW_DELAY_MS);
  }

  function onFeed(feed: Feed): void {
    if (isLang(feed.lang) && locale.lang !== feed.lang) locale.set(feed.lang);
    look.mouth = feed.mouth;
    look.speaking = feed.speaking;
    const hue = new Map<string, number>(Object.entries(EMOTION_HUE)).get(feed.emotion);
    look.hue = hue ?? EMOTION_HUE.neutral;
    if (feed.speaking) {
      brain.wake();
      listening = false;
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
    const hit = settings.hologram || box === null ? null : box;
    const key = JSON.stringify([
      hit && [Math.round(hit.x), Math.round(hit.y), Math.round(hit.w)],
      capture,
    ]);
    if (key === lastHit) return;
    lastHit = key;
    void invoke("companion_hit", { hit, capture });
  }

  function syncHost(): void {
    const host = hostOf(brain.spot);
    if (host === attachedHost) return;
    attachedHost = host;
    void invoke("companion_attach", { host });
  }

  /** Перешли в программу другого рода — иногда сразу прокомментировать, но не чаще раза в 45 с. */
  /** Рабочий стол: значки — опоры и цели; спутник садится на них и иногда перепрыгивает или тычет. */
  async function enterDesktop(desktop: boolean): Promise<void> {
    onDesktop = desktop;
    if (!desktop) {
      icons = [];
      brain.setIcons([]);
      return;
    }
    await refreshIcons();
    desktopAt = performance.now() + 1200;
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

  /** Перепрыгнуть на значок (с репликой) или ткнуть в него. */
  async function desktopAct(now: number): Promise<void> {
    desktopAt = now + (25 + Math.random() * 35) * 1000;
    await refreshIcons();
    const chosen = icons[Math.floor(Math.random() * icons.length)];
    if (chosen === undefined || brain.phase !== "rest" || gesture !== "none") return;
    if (Math.random() < 0.4) {
      void poke(now);
      return;
    }
    const spot = snap(brain.surfaceList, chosen.rect.x + chosen.rect.w / 2, chosen.rect.y + 6, 30);
    if (spot === null) return;
    brain.goTo(spot);
    const lines = locale.t.companion.perch;
    const line = lines[Math.floor(Math.random() * lines.length)];
    if (line !== undefined)
      setTimeout(() => {
        say(line(chosen.name), performance.now());
      }, 900);
  }

  function noticeTopic(focus: Focus): void {
    const app = focus.kind === "desktop" ? "" : focus.app;
    const next = topicOf(app, focus.kind === "desktop");
    if (next === topic) return;
    topic = next;
    const now = performance.now();
    if (now - lastRemarkTime > 45_000 && Math.random() < 0.35) remarkAt = now + 1500;
  }

  function say(text: string, now: number): void {
    listening = false;
    replyText = text;
    bubbleUntil = now + 6000;
    lastRemark = text;
    lastRemarkTime = now;
  }

  function maybeRemark(now: number): void {
    const busy = look.speaking || listening || now < bubbleUntil || gesture !== "none";
    if (!shown || brain.phase !== "rest" || busy || poking || now < remarkAt) return;
    remarkAt = now + nextPause(Math.random) * 1000;
    // Примерно каждая третья выходка — «потыкать» в кнопку или значок (ADR-0048).
    if (Math.random() < 0.35) {
      void poke(now);
      return;
    }
    const hour = new Date().getHours();
    say(remark(locale.t, { topic, hour, idleS: brain.idleSeconds }, Math.random, lastRemark), now);
  }

  /** Подлететь к элементу экрана, ткнуть, сказать его название и вернуться. Нечего тыкать — фраза. */
  async function poke(now: number): Promise<void> {
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
      say(
        remark(
          locale.t,
          { topic, hour: new Date().getHours(), idleS: brain.idleSeconds },
          Math.random,
          lastRemark,
        ),
        now,
      );
      return;
    }
    const back = brain.spot;
    brain.visit(near.x, near.y, "poke", near.facing);
    const lines = locale.t.companion.poke;
    const line = lines[Math.floor(Math.random() * lines.length)];
    setTimeout(() => {
      if (line !== undefined) say(line(near.name), performance.now());
    }, 700);
    setTimeout(() => {
      poking = false;
      if (brain.phase !== "rest" || gesture !== "none") return;
      const home =
        back ?? (world === null ? null : followSpot(world, brain.surfaceList, { kind: "desktop" }));
      if (home !== null) brain.goTo(home);
    }, 5200);
  }

  function updateBubble(now: number): void {
    const box = stage?.bounds;
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
    maybeRemark(now);
    const free = shown && brain.phase === "rest" && gesture === "none" && !poking && !look.speaking;
    if (onDesktop && free && settings.behavior !== "stay" && now >= desktopAt) void desktopAct(now);
    // Своя инициатива — фраза в облачке или «тыканье»: на мышь в это время не смотрит.
    brain.busy = poking || (!listening && now < bubbleUntil && replyText === lastRemark);
    if (press !== null && gesture === "none" && now - press.t >= HOLD_MS) {
      gesture = "aim";
      aim = { x: press.x, y: press.y, ghost: null };
    }
    brain.tick(dt);
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
      const done = release(brain.surfaceList, point, velocityOf(trail));
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
    pets = [...pets.filter((t) => now - t < 3000), now];
    brain.pet();
    look.attention = Math.max(look.attention, 0.5);
    const lines = locale.t.companion.pet;
    const list = pets.length >= 6 ? lines.lots : pets.length >= 3 ? lines.more : lines.first;
    const line = list[Math.floor(Math.random() * list.length)];
    if (line !== undefined && (pets.length === 1 || pets.length === 3 || pets.length === 6)) {
      say(line, now);
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
        if (world !== null)
          brain.hostMoved(id, rect === null ? null : rectToCss(rect, world.monitor, scale));
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
