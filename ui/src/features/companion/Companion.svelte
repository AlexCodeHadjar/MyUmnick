<script lang="ts">
  import { locale } from "../../core";
  // Слой «Сопровождения» (Этап 23, ADR-0045) — только вид: холст, облачко, табличка радио, меню. Всё
  // поведение — в `controller/` (тело, «Разум», органы чувств, присутствие, жесты), события оболочки и
  // главного окна передаются туда.
  import { listen, type UnlistenFn } from "@tauri-apps/api/event";
  import { onMount } from "svelte";

  import { characterChannel } from "../avatar/portrait/picture";
  import { sendRadioCommand } from "../radio";
  import { CompanionController, tauriPorts, type Feed, type MainState } from "./controller";
  import { CompanionStage } from "./look";
  import {
    COMPANION_KEY,
    HEIGHTS,
    loadSettings,
    saveSettings,
    type CompanionBehavior,
    type CompanionSettings,
  } from "./settings";
  import { placeBubble, type Rect, type World } from "./space";

  const controller = new CompanionController(
    tauriPorts,
    window.localStorage,
    loadSettings(window.localStorage),
  );

  let canvas: HTMLCanvasElement | undefined = $state();
  let settings = $state<CompanionSettings>(controller.settings);
  let bubble = $state<{ text: string; x: number; y: number } | null>(null);
  /** Облачко на экране: его размер прошлого кадра держит текст в пределах экрана. */
  let bubbleEl = $state<HTMLParagraphElement | null>(null);
  let menu = $state<{ x: number; y: number } | null>(null);
  // Радио (ADR-0049): табличка над головой — станция и ⏮ ⏯ ⏭; кнопки шлют команды главному окну.
  let radio = $state(controller.radio);
  let radioAt = $state<{ x: number; y: number } | null>(null);
  let radioEl = $state<HTMLDivElement | null>(null);

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

  /** Табличка радио над головой, облачко — над табличкой; всё в пределах экрана. */
  function place(now: number): void {
    radio = controller.radio;
    let box = controller.stage?.bounds ?? null;
    const view = { w: innerWidth, h: innerHeight };
    radioAt = null;
    if (box !== null && radio !== null) {
      const card =
        radioEl === null ? { w: 230, h: 58 } : { w: radioEl.offsetWidth, h: radioEl.offsetHeight };
      radioAt = placeBubble(box, card, view);
      box = { ...box, y: radioAt.y - 6 - box.h * 0.08 };
    }
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
    controller.frame(dt, now, { menuOpen: menu !== null, card: cardRect() });
    place(now);
  }

  function down(event: PointerEvent): void {
    if (event.button !== 0 || canvas === undefined) return;
    menu = null;
    controller.gestures.down(event.clientX, event.clientY, performance.now());
    try {
      canvas.setPointerCapture(event.pointerId);
    } catch {
      // Указатель уже отпущен (короткий клик) — захват не нужен.
    }
  }

  function move(event: PointerEvent): void {
    controller.gestures.move(event.clientX, event.clientY, performance.now());
  }

  function up(event: PointerEvent): void {
    const point = {
      x: event.clientX,
      y: event.clientY,
      shift: event.shiftKey,
      ctrl: event.ctrlKey,
    };
    controller.gestures.up(point, performance.now());
  }

  function cancelAim(event: KeyboardEvent): void {
    if (event.key !== "Escape") return;
    menu = null;
    if (controller.gestures.gesture === "aim") controller.gestures.cancel();
  }

  function subscribe(): Promise<UnlistenFn>[] {
    return [
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
      listen<[number, number]>("companion-cursor", (event) => {
        controller.onCursor(...event.payload);
      }),
      listen<Feed>("companion-feed", (event) => {
        controller.onFeed(event.payload);
      }),
    ];
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
    const unlisten = subscribe();
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
    const onPack = (): void => {
      void stage.load(settings.height);
    };
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
  ondblclick={openMain}
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
    <button type="button" role="menuitem" onclick={openMain}>{locale.t.companion.openWindow}</button
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
