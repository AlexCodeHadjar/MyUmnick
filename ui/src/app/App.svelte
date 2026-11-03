<script lang="ts">
  // Окно: чат слева, сцена с аватаром справа (FR-01), статус-бар внизу, панель метрик по горячей
  // клавише (FR-15). Голос: плеер из фичи audio, его громкость — рот аватара (ADR-0003, R-63).
  import { onMount } from "svelte";

  import type { CoreClient } from "../core";
  import { connectVoice, type VoicePlayer } from "../features/audio";
  import { AvatarStage } from "../features/avatar";
  import { Chat } from "../features/chat";
  import { MicControl } from "../features/mic";
  import { isMetricsHotkey, METRICS_HOTKEY_LABEL, MetricsPanel } from "../features/metrics";
  import { isMemoryHotkey, MEMORY_HOTKEY_LABEL, MemoryPanel } from "../features/memory";
  import { chosenAvatar, Onboarding } from "../features/onboarding";
  import { PrivacyControl } from "../features/privacy";
  import { isResourcesHotkey, RESOURCES_HOTKEY_LABEL, ResourcesPanel } from "../features/resources";
  import SplitLayout from "./SplitLayout.svelte";
  import StatusBar from "./StatusBar.svelte";

  const { client }: { client: CoreClient } = $props();

  let showMetrics = $state(false);
  let showResources = $state(false);
  let showMemory = $state(false);
  let setupClosed = $state(false);
  // Не реактивен: рот опрашивается каждый кадр из цикла аватара, а не через Svelte (R-66).
  let player: VoicePlayer | null = null;

  onMount(() => {
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
    } else if (isMemoryHotkey(event)) {
      event.preventDefault();
      showMemory = !showMemory;
    } else if (isResourcesHotkey(event)) {
      event.preventDefault();
      showResources = !showResources;
    } else if (event.key === "Escape" && !event.isComposing) {
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
  <SplitLayout storage={layoutStorage()}>
    {#snippet left()}
      <Chat {client} storage={layoutStorage()} />
    {/snippet}
    {#snippet right()}
      <section class="stage" aria-label="Сцена">
        <AvatarStage
          name={chosenAvatar(layoutStorage()) ?? import.meta.env.VITE_AVATAR}
          store={client.store}
          mouth={(deltaMs: number) => player?.mouth(deltaMs) ?? 0}
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
  <StatusBar
    store={client.store}
    hint={`${METRICS_HOTKEY_LABEL}, ${RESOURCES_HOTKEY_LABEL}, ${MEMORY_HOTKEY_LABEL}`}
  >
    <MicControl {client} storage={layoutStorage()} />
    <PrivacyControl {client} />
  </StatusBar>
  {#if client.store.setup?.needed && !setupClosed}
    <Onboarding
      {client}
      storage={layoutStorage()}
      fallbackAvatar={import.meta.env.VITE_AVATAR}
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
    font-family: system-ui, sans-serif;
    /* Полосы прокрутки и поля ввода — в тёмной гамме WebView. */
    color-scheme: dark;
    background: #15151c;
    color: #e8e8f0;
  }

  .app {
    display: grid;
    grid-template-rows: minmax(0, 1fr) auto;
    height: 100vh;
  }

  .stage {
    position: relative;
    display: grid;
    place-content: center;
    height: 100%;
    text-align: center;
  }
</style>
