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
    return () => {
      disposed = true;
      void player?.dispose();
      player = null;
    };
  });

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
        <section class="stage" aria-label={locale.t.app.stage} bind:this={stageHost}>
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
          />
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
        </section>
      {/snippet}
    </SplitLayout>
  </div>
  <!-- Скрыт, а не снят: микрофон продолжает слушать и поверх стола. -->
  <div class="status" class:hidden={overlay}>
    <StatusBar
      store={client.store}
      hint={`${locale.t.metrics.hotkey}, ${locale.t.resources.hotkey}, ${locale.t.memory.hotkey}, ${locale.t.skills.hotkey}${desktopPort === null ? "" : `, ${locale.t.desktop.hotkey}`}`}
    >
      <EditionBadge store={client.store} />
      <AmbientControl audio={systemAudio} storage={layoutStorage()} />
      <MicControl {client} storage={layoutStorage()} {background} />
      <PrivacyControl {client} />
      <button
        type="button"
        class="skills-button"
        class:active={showSkills}
        title={locale.t.skills.openHint}
        aria-pressed={showSkills}
        onclick={() => {
          showSkills = !showSkills;
        }}>🧩 {locale.t.skills.open}</button
      >
    </StatusBar>
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
    grid-template-rows: minmax(0, 1fr) auto;
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

  .stage {
    position: relative;
    display: grid;
    place-content: center;
    height: 100%;
    text-align: center;
  }

  .skills-button {
    padding: 2px 8px;
    border: 1px solid var(--edge);
    border-radius: 6px;
    background: var(--plate);
    color: inherit;
    font: inherit;
    font-size: 0.85em;
    cursor: pointer;
  }

  .skills-button.active {
    border-color: var(--accent);
  }
</style>
