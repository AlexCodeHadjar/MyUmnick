<script lang="ts">
  import { locale } from "../core";
  // Статус-бар: связь с ядром и состояние бэкендов (LLM, TTS). Тексты и цвета — status.ts.
  import type { Snippet } from "svelte";

  import type { AppStore } from "../core";
  import { backendIndicator, blockedDetails, connectionIndicator } from "./status";

  const { store, hint, children }: { store: AppStore; hint: string; children?: Snippet } = $props();

  // Связь хоть раз была: потерю показываем как «нет связи», а не как первое «подключение…».
  let everOpen = $state(false);
  $effect(() => {
    if (store.connection === "open") {
      everOpen = true;
    }
  });

  const online = $derived(store.connection === "open");
  const items = $derived([
    { name: locale.t.status.core, ...connectionIndicator(store.connection, everOpen, locale.t) },
    { name: "LLM", ...backendIndicator(store.backends.llm, online, locale.t) },
    { name: "TTS", ...backendIndicator(store.backends.tts, online, locale.t) },
    // Микрофон загружает модель по первому кадру: до этого показывать нечего.
    ...(store.backends.stt === "unknown"
      ? []
      : [{ name: "STT", ...backendIndicator(store.backends.stt, online, locale.t) }]),
  ]);
</script>

<footer class="status-bar">
  {#each items as item (item.name)}
    <span class="item" data-testid="status-{item.name}">
      <span class="dot {item.tone}" aria-hidden="true"></span>
      {item.name}: {item.label}
    </span>
  {/each}
  {@render children?.()}
  {#if store.blockedViewers.length > 0}
    <span class="blocked" data-testid="status-blocked" title={blockedDetails(store.blockedViewers)}>
      {locale.t.status.viewerAttacks}: {store.blockedViewers.length}
    </span>
  {/if}
  <span class="hint">{hint}</span>
</footer>

<style>
  .blocked {
    color: #ffc27a;
  }

  .status-bar {
    display: flex;
    gap: 18px;
    align-items: center;
    padding: 4px 12px;
    border-top: 1px solid #2c2c38;
    background: #111117;
    font-size: 0.8em;
    color: #b8b8c8;
  }

  .item {
    display: inline-flex;
    gap: 6px;
    align-items: center;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .ok {
    background: #5fd38d;
  }

  .wait {
    background: #e8c35a;
  }

  .bad {
    background: #ff6b6b;
  }

  .off {
    background: #55556a;
  }

  .hint {
    margin-left: auto;
    opacity: 0.6;
  }
</style>
