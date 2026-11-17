<script lang="ts">
  import { locale } from "../core";
  // Окно: чат слева, сцена с аватаром справа (FR-01), статус-бар внизу, панель метрик по горячей
  // клавише (FR-15). Голос: плеер из фичи audio, его громкость — рот аватара (ADR-0003, R-63).
  import { onMount } from "svelte";

  import type { CoreClient } from "../core";
  import { connectVoice, type VoicePlayer } from "../features/audio";
  import { AmbientControl, SystemAudio } from "../features/ambient";
  import {
    AvatarStage,
    CharacterControls,
    loadView,
    saveView,
    type AvatarView,
  } from "../features/avatar";
  import { Chat } from "../features/chat";
  import { ChatSidebar } from "../features/chats";
  import {
    DesktopOverlay,
    isDesktopHotkey,
    loadDesktop,
    saveDesktop,
    tauriWindow,
    type Point,
  } from "../features/desktop";
  import { EditionBadge } from "../features/edition";
  import { MicControl } from "../features/mic";
  import { isMetricsHotkey, MetricsPanel } from "../features/metrics";
  import { isMemoryHotkey, MemoryPanel } from "../features/memory";
  import { isSkillsHotkey, SkillsPanel } from "../features/skills";
  import { isThemeHotkey, ThemePanel } from "../features/theme";
  import { CompanionMenu, startFeed } from "../features/companion";
  import { Onboarding } from "../features/onboarding";
  import { PrivacyControl } from "../features/privacy";
  import { isResourcesHotkey, ResourcesPanel } from "../features/resources";
  import SplitLayout from "./SplitLayout.svelte";
  import StatusBar from "./StatusBar.svelte";

  type HitTest = (x: number, y: number) => boolean;

  const { client, background = false }: { client: CoreClient; background?: boolean } = $props();

  let showMetrics = $state(false);
  let showResources = $state(false);
  let showMemory = $state(false);
  let showSkills = $state(false);
  let showTheme = $state(false);
  let setupClosed = $state(false);
  // Звук компьютера для сферы: один на окно, читается циклом аватара каждый кадр (ADR-0039).
  const systemAudio = new SystemAudio();

  // Вид показа справа (Этап 23): картинка персонажа или сфера — выбор в меню по правой кнопке.
  let avatarView = $state(loadView(layoutStorage()));
  let stageHost: HTMLElement | undefined = $state();
  // Вне Tauri такого окна нет: режим и кнопка просто отсутствуют.
  const desktopPort = tauriWindow();
  let desktop = $state(loadDesktop(layoutStorage()));
  const overlay = $derived(desktopPort !== null && desktop.overlay);
  // Не реактивна: опрашивается таймером, сцена даёт её один раз при создании.
  let overModel: HitTest = () => false;
  // Не реактивен: рот опрашивается каждый кадр из цикла аватара, а не через Svelte (R-66).
  let player: VoicePlayer | null = null;

  // Чат и сцена остаются смонтированными: возврат мгновенный, модель не загружается заново.
  $effect(() => {
    document.documentElement.classList.toggle("desktop-overlay", overlay);
  });

  function changeDesktop(next: typeof desktop): void {
    const entering = next.overlay && !desktop.overlay;
    const leaving = !next.overlay && desktop.overlay;
    desktop = next;
    saveDesktop(layoutStorage(), next);
    if (entering) void desktopPort?.enterOverlay(next.pinned);
    else if (leaving) void desktopPort?.leaveOverlay();
    else void desktopPort?.setPinned(next.overlay && next.pinned);
  }

  onMount(() => {
    // Прошлый запуск закончился поверх стола: окно создаётся обычным.
    if (overlay) void desktopPort?.enterOverlay(desktop.pinned);
    let disposed = false;
    connectVoice(client)
      .then((created) => {
        if (disposed) {
          void created.dispose();
        } else {
          player = created;
        }
      })
      .catch((error: unknown) => {
        // Без звука чат и аватар работают — голос не обязателен.
        console.warn("[audio] плеер не создан", error);
      });
    // Спутнику — речь и эмоция (Этап 23): к ядру он не подключается.
    const stopFeed =
      desktopPort === null ? null : startFeed(client, (dt) => player?.mouth(dt) ?? 0);
    return () => {
      disposed = true;
      stopFeed?.();
      void player?.dispose();
      player = null;
    };
  });

  const hints = $derived([
    locale.t.metrics.hotkey,
    locale.t.resources.hotkey,
    locale.t.memory.hotkey,
    locale.t.skills.hotkey,
    locale.t.theme.hotkey,
    ...(desktopPort === null ? [] : [locale.t.desktop.hotkey]),
  ]);

  /** Кнопки панелей в окне настроек: те же панели, что по горячим клавишам. */
  const panelButtons = $derived([
    {
      id: "skills",
      label: `🧩 ${locale.t.skills.open}`,
      hint: locale.t.skills.openHint,
      shown: showSkills,
      toggle: () => (showSkills = !showSkills),
    },
    {
      id: "theme",
      label: `🎨 ${locale.t.theme.open}`,
      hint: locale.t.theme.openHint,
      shown: showTheme,
      toggle: () => (showTheme = !showTheme),
    },
    {
      id: "memory",
      label: `🧠 ${locale.t.memory.title}`,
      hint: locale.t.memory.hotkey,
      shown: showMemory,
      toggle: () => (showMemory = !showMemory),
    },
    {
      id: "metrics",
      label: `⏱ ${locale.t.metrics.region}`,
      hint: locale.t.metrics.hotkey,
      shown: showMetrics,
      toggle: () => (showMetrics = !showMetrics),
    },
    {
      id: "resources",
      label: `📊 ${locale.t.resources.title}`,
      hint: locale.t.resources.hotkey,
      shown: showResources,
      toggle: () => (showResources = !showResources),
    },
  ]);

  /** Браузер запускает звук только после жеста пользователя — первое нажатие его и даёт. */
  function unlockAudio(): void {
    void player?.resume();
  }

  function onkeydown(event: KeyboardEvent): void {
    unlockAudio();
    if (isMetricsHotkey(event)) {
      event.preventDefault();
      showMetrics = !showMetrics;
    } else if (desktopPort !== null && isDesktopHotkey(event)) {
      event.preventDefault();
      changeDesktop({ ...desktop, overlay: !desktop.overlay });
    } else if (isMemoryHotkey(event)) {
      event.preventDefault();
      showMemory = !showMemory;
    } else if (isSkillsHotkey(event)) {
      event.preventDefault();
      showSkills = !showSkills;
    } else if (isThemeHotkey(event)) {
      event.preventDefault();
      showTheme = !showTheme;
    } else if (isResourcesHotkey(event)) {
      event.preventDefault();
      showResources = !showResources;
    } else if (event.key === "Escape" && !event.isComposing) {
      // Ход в ядре мог уже закончиться (кнопки «Стоп» нет), а голос ещё звучит — Esc его глушит.
      player?.cancel(null);
    }
  }

  /** Двойной щелчок по персонажу — поверх стола и обратно (то же, что Ctrl+Shift+O). */
  function ondblclick(event: MouseEvent): void {
    if (desktopPort !== null && overModel(event.clientX, event.clientY)) {
      changeDesktop({ ...desktop, overlay: !desktop.overlay });
    }
  }

  /** localStorage недоступен (политика WebView, приватный режим) — ширина просто не запомнится. */
  function layoutStorage(): Storage | undefined {
    try {
      return window.localStorage;
    } catch {
      return undefined;
    }
  }
</script>

<svelte:window {onkeydown} {ondblclick} onpointerdown={unlockAudio} />

<main class="app">
  {#if overlay && desktopPort !== null}
    <DesktopOverlay port={desktopPort} overModel={(point: Point) => overModel(point.x, point.y)} />
  {/if}
  <div class="workspace">
    {#if !overlay}
      <ChatSidebar {client} storage={layoutStorage() ?? null} />
    {/if}
    <SplitLayout storage={layoutStorage()} onlyRight={overlay}>
      {#snippet left()}
        <Chat {client} storage={layoutStorage()} />
      {/snippet}
      {#snippet right()}
        <!-- Справа два окошка (просьба пользователя 2026-11-17): мордашка сверху, настройки под ней. -->
        <div class="side" class:overlay>
          <section class="stage card" aria-label={locale.t.app.stage} bind:this={stageHost}>
            <!-- Смена вида пересоздаёт сцену: у каждого вида свой рендер. -->
            {#key avatarView}
              <AvatarStage
                onhittest={(contains: HitTest) => {
                  overModel = contains;
                }}
                view={avatarView}
                store={client.store}
                mouth={(deltaMs: number) => player?.mouth(deltaMs) ?? 0}
                mouthForm={() => player?.mouthForm() ?? 0}
                ambient={() => systemAudio.bands}
              />
            {/key}
            <CharacterControls
              host={stageHost}
              view={avatarView}
              onview={(next: AvatarView) => {
                avatarView = next;
                saveView(layoutStorage(), next);
              }}
            >
              {#snippet extra(close: () => void, note: (text: string) => void)}
                {#if desktopPort !== null}
                  <CompanionMenu onclose={close} onnote={note} />
                {/if}
              {/snippet}
            </CharacterControls>
          </section>
          <!-- Скрыто, а не снято: микрофон продолжает слушать и поверх стола. -->
          <div class="card settings" class:hidden={overlay}>
            <StatusBar store={client.store} {hints}>
              <EditionBadge store={client.store} />
              <AmbientControl audio={systemAudio} storage={layoutStorage()} />
              <MicControl {client} storage={layoutStorage()} {background} />
              <PrivacyControl {client} />
              {#snippet panels()}
                {#each panelButtons as panel (panel.id)}
                  <button
                    type="button"
                    class="panel-button"
                    class:active={panel.shown}
                    title={panel.hint}
                    aria-pressed={panel.shown}
                    onclick={panel.toggle}>{panel.label}</button
                  >
                {/each}
              {/snippet}
            </StatusBar>
          </div>
          {#if showMetrics}
            <MetricsPanel
              store={client.store}
              onclose={() => {
                showMetrics = false;
              }}
            />
          {/if}
          {#if showMemory}
            <MemoryPanel
              {client}
              onclose={() => {
                showMemory = false;
              }}
            />
          {/if}
          {#if showTheme}
            <ThemePanel
              storage={layoutStorage()}
              onclose={() => {
                showTheme = false;
              }}
            />
          {/if}
          {#if showSkills}
            <SkillsPanel
              {client}
              onclose={() => {
                showSkills = false;
              }}
            />
          {/if}
          {#if showResources}
            <ResourcesPanel
              {client}
              onclose={() => {
                showResources = false;
              }}
            />
          {/if}
        </div>
      {/snippet}
    </SplitLayout>
  </div>
  {#if client.store.setup?.needed && !setupClosed}
    <Onboarding
      {client}
      onclose={() => {
        setupClosed = true;
      }}
    />
  {/if}
</main>

<style>
  :global(html),
  :global(body) {
    margin: 0;
    height: 100%;
    font-family: var(--font);
    /* Полосы прокрутки и поля ввода — в тёмной гамме WebView. */
    color-scheme: dark;
    background:
      radial-gradient(ellipse 120% 45% at 50% 0, var(--glow), transparent 70%) fixed,
      var(--ground);
    color: var(--text);
  }

  /* Прозрачно только поверх стола: у обычного окна фон свой, хоть само окно и прозрачное. */
  :global(html.desktop-overlay),
  :global(html.desktop-overlay body) {
    background: transparent;
  }

  .hidden {
    display: none;
  }

  .app {
    display: grid;
    grid-template-rows: minmax(0, 1fr);
    height: 100vh;
  }

  /* Чаты слева, затем чат и сцена: панель чатов сворачивается сама, раскладка не прыгает. */
  .workspace {
    display: flex;
    min-height: 0;
  }
  .workspace > :global(:last-child) {
    flex: 1;
    min-width: 0;
  }

  /* Правая колонка: окошко персонажа сверху, окошко настроек под ним; панели — поверх обоих. */
  .side {
    position: relative;
    display: grid;
    grid-template-rows: minmax(200px, 42%) minmax(0, 1fr);
    gap: 10px;
    height: 100%;
    padding: 10px;
    box-sizing: border-box;
  }

  .side.overlay {
    grid-template-rows: minmax(0, 1fr);
    padding: 0;
  }

  .card {
    min-height: 0;
    border: 1px solid var(--rule-dim);
    border-radius: 12px;
    background: color-mix(in srgb, var(--panel) 70%, transparent);
    overflow: hidden;
  }

  .side.overlay .card {
    border: none;
    background: transparent;
  }

  .settings {
    display: flex;
    flex-direction: column;
  }

  .stage {
    position: relative;
    display: grid;
    place-content: center;
    height: 100%;
    text-align: center;
  }

  .panel-button {
    padding: 2px 8px;
    border: 1px solid var(--edge);
    border-radius: 6px;
    background: var(--plate);
    color: inherit;
    font: inherit;
    font-size: 0.85em;
    cursor: pointer;
  }

  .panel-button.active {
    border-color: var(--accent);
  }
</style>
