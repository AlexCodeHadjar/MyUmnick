<script lang="ts">
  // Окно: чат слева, сцена с аватаром справа (FR-01), статус-бар внизу, панель метрик по горячей
  // клавише (FR-15). Голос: плеер из фичи audio, его громкость — рот аватара (ADR-0003, R-63).
  import { onMount } from "svelte";

  import type { CoreClient } from "../core";
  import { connectVoice, type VoicePlayer } from "../features/audio";
  import { AvatarStage } from "../features/avatar";
  import { Chat } from "../features/chat";
  import { isMetricsHotkey, METRICS_HOTKEY_LABEL, MetricsPanel } from "../features/metrics";
  import SplitLayout from "./SplitLayout.svelte";
  import StatusBar from "./StatusBar.svelte";

  const { client }: { client: CoreClient } = $props();

  let showMetrics = $state(false);
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
          name={import.meta.env.VITE_AVATAR}
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
      </section>
    {/snippet}
  </SplitLayout>
  <StatusBar store={client.store} hint={METRICS_HOTKEY_LABEL} />
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
