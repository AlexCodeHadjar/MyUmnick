<script lang="ts">
  // Окно: чат слева, сцена с аватаром справа (FR-01), статус-бар внизу, панель метрик по горячей
  // клавише (FR-15).
  import type { CoreClient } from "../core";
  import { AvatarStage } from "../features/avatar";
  import { Chat } from "../features/chat";
  import { isMetricsHotkey, METRICS_HOTKEY_LABEL, MetricsPanel } from "../features/metrics";
  import SplitLayout from "./SplitLayout.svelte";
  import StatusBar from "./StatusBar.svelte";

  const { client }: { client: CoreClient } = $props();

  let showMetrics = $state(false);

  function onkeydown(event: KeyboardEvent): void {
    if (isMetricsHotkey(event)) {
      event.preventDefault();
      showMetrics = !showMetrics;
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

<svelte:window {onkeydown} />

<main class="app">
  <SplitLayout storage={layoutStorage()}>
    {#snippet left()}
      <Chat {client} />
    {/snippet}
    {#snippet right()}
      <section class="stage" aria-label="Сцена">
        <AvatarStage name={import.meta.env.VITE_AVATAR} />
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
