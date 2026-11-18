<script lang="ts">
  import { locale } from "../core";
  // Окно: чат слева, сцена с аватаром справа (FR-01), настройки под ней, панели — кнопками (FR-15). Голос: плеер из фичи audio, его громкость — рот аватара (ADR-0003, R-63).
  import { isTauri } from "@tauri-apps/api/core";
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
  import { Chat, readSubtitles, writeSubtitles } from "../features/chat";
  import { ChatSidebar } from "../features/chats";
  import { EditionBadge } from "../features/edition";
  import { MicControl } from "../features/mic";
  import { MetricsPanel } from "../features/metrics";
  import { MemoryPanel } from "../features/memory";
  import { SkillsPanel } from "../features/skills";
  import { ThemePanel } from "../features/theme";
  import { CompanionMenu, CompanionReturn, startFeed } from "../features/companion";
  import { Onboarding } from "../features/onboarding";
  import { listenRadioCommands, RadioControl, RadioPlayer } from "../features/radio";
  import { ResourcesPanel } from "../features/resources";
  import { restoreWindow } from "./restoreWindow";
  import SplitLayout from "./SplitLayout.svelte";
  import StageBadges from "./StageBadges.svelte";
  import StatusBar from "./StatusBar.svelte";

  const { client, background = false }: { client: CoreClient; background?: boolean } = $props();

  let showMetrics = $state(false);
  let showResources = $state(false);
  let showMemory = $state(false);
  let showSkills = $state(false);
  let showTheme = $state(false);
  let setupClosed = $state(false);
  // Звук компьютера для сферы: один на окно, читается циклом аватара каждый кадр (ADR-0039).
  const systemAudio = new SystemAudio();
  // Радио (ADR-0049): играет главное окно — оно живо и в трее; спутник показывает и шлёт команды.
  const radioPlayer = new RadioPlayer(layoutStorage());

  // Вид показа справа (Этап 23): картинка персонажа или сфера — выбор в меню по правой кнопке.
  let avatarView = $state(loadView(layoutStorage()));
  // Субтитры — значком в окошке персонажа, а действуют в чате (просьба пользователя 2026-11-18).
  let subtitles = $state(readSubtitles(layoutStorage()));
  let stageHost: HTMLElement | undefined = $state();
  // Спутник и его меню есть только в оболочке Tauri, в браузере их нет.
  const desktopApp = isTauri();
  // Не реактивен: рот опрашивается каждый кадр из цикла аватара, а не через Svelte (R-66).
  let player: VoicePlayer | null = null;

  onMount(() => {
    // Режим «поверх стола» удалён (просьба пользователя 2026-11-18): окно, оставшееся без рамки, — обычным.
    if (desktopApp) void restoreWindow(layoutStorage());
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
    const stopFeed = !desktopApp
      ? null
      : startFeed(
          client,
          (dt) => player?.mouth(dt) ?? 0,
          (time) => radioPlayer.feed(time),
        );
    const stopCommands = !desktopApp
      ? null
      : listenRadioCommands((command) => {
          radioPlayer.command(command);
        });
    return () => {
      disposed = true;
      stopFeed?.();
      void stopCommands?.then((stop) => {
        stop();
      });
      radioPlayer.dispose();
      void player?.dispose();
      player = null;
    };
  });

  /** Кнопки панелей в окне настроек. */
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
      hint: locale.t.memory.title,
      shown: showMemory,
      toggle: () => (showMemory = !showMemory),
    },
    {
      id: "metrics",
      label: `⏱ ${locale.t.metrics.region}`,
      hint: locale.t.metrics.region,
      shown: showMetrics,
      toggle: () => (showMetrics = !showMetrics),
    },
    {
      id: "resources",
      label: `📊 ${locale.t.resources.title}`,
      hint: locale.t.resources.title,
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
    if (event.key === "Escape" && !event.isComposing) {
      // Ход в ядре мог уже закончиться (кнопки «Стоп» нет), а голос ещё звучит — Esc его глушит.
      player?.cancel(null);
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

<svelte:window {onkeydown} onpointerdown={unlockAudio} />

<main class="app">
  <div class="workspace">
    <ChatSidebar {client} storage={layoutStorage() ?? null} />
    <SplitLayout storage={layoutStorage()}>
      {#snippet left()}
        <Chat {client} {subtitles} />
      {/snippet}
      {#snippet right()}
        <!-- Справа два окошка (просьба пользователя 2026-11-17): мордашка сверху, настройки под ней. -->
        <div class="side">
          <section class="stage card" aria-label={locale.t.app.stage} bind:this={stageHost}>
            <!-- Смена вида пересоздаёт сцену: у каждого вида свой рендер. -->
            {#key avatarView}
              <AvatarStage
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
                {#if desktopApp}
                  <CompanionMenu onclose={close} onnote={note} />
                {/if}
              {/snippet}
            </CharacterControls>
            <StageBadges
              store={client.store}
              {subtitles}
              onsubtitles={() => {
                subtitles = !subtitles;
                writeSubtitles(layoutStorage(), subtitles);
              }}
            >
              {#if desktopApp}
                <CompanionReturn />
              {/if}
            </StageBadges>
          </section>
          <div class="card settings">
            <StatusBar>
              <EditionBadge store={client.store} />
              <AmbientControl audio={systemAudio} storage={layoutStorage()} />
              <MicControl {client} storage={layoutStorage()} {background} />
              {#snippet radio()}
                <RadioControl player={radioPlayer} />
              {/snippet}
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

  .card {
    min-height: 0;
    border: 1px solid var(--rule-dim);
    border-radius: 12px;
    background: color-mix(in srgb, var(--panel) 70%, transparent);
    overflow: hidden;
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
