<script lang="ts">
  import { locale } from "../core";
  // Значки в окошке персонажа (просьба пользователя 2026-11-18): справа столбиком — состояние ядра и
  // бэкендов цветом, подсказка при наведении; снизу — субтитры и то, что передали снаружи (вернуть спутника).
  import type { Snippet } from "svelte";

  import type { AppStore } from "../core";
  import { backendIndicator, blockedDetails, connectionIndicator } from "./status";

  const {
    store,
    subtitles,
    onsubtitles,
    children,
  }: {
    store: AppStore;
    subtitles: boolean;
    onsubtitles: () => void;
    children?: Snippet;
  } = $props();

  // Связь хоть раз была: потерю показываем как «нет связи», а не как первое «подключение…».
  let everOpen = $state(false);
  $effect(() => {
    if (store.connection === "open") everOpen = true;
  });

  const online = $derived(store.connection === "open");
  const s = $derived(locale.t.status);
  const items = $derived([
    {
      id: "core",
      icon: "⚡",
      name: `${s.core} — ${s.coreHint}`,
      ...connectionIndicator(store.connection, everOpen, locale.t),
    },
    {
      id: "LLM",
      icon: "🧠",
      name: `LLM — ${s.llmHint}`,
      ...backendIndicator(store.backends.llm, online, locale.t),
    },
    {
      id: "TTS",
      icon: "🔊",
      name: `TTS — ${s.ttsHint}`,
      ...backendIndicator(store.backends.tts, online, locale.t),
    },
    // Микрофон загружает модель по первому кадру: до этого показывать нечего.
    ...(store.backends.stt === "unknown"
      ? []
      : [
          {
            id: "STT",
            icon: "🎙",
            name: `STT — ${s.sttHint}`,
            ...backendIndicator(store.backends.stt, online, locale.t),
          },
        ]),
  ]);
</script>

<div class="status" aria-label={locale.t.app.state}>
  {#each items as item (item.id)}
    <span
      class="icon {item.tone}"
      data-testid="status-{item.id}"
      title={`${item.name}: ${item.label}`}
      aria-label={`${item.name}: ${item.label}`}
      role="img">{item.icon}</span
    >
  {/each}
  {#if store.blockedViewers.length > 0}
    <span
      class="icon bad"
      data-testid="status-blocked"
      role="img"
      aria-label={`${s.viewerAttacks}: ${String(store.blockedViewers.length)}`}
      title={`${s.viewerAttacks}: ${String(store.blockedViewers.length)}\n${blockedDetails(store.blockedViewers)}`}
      >⚠</span
    >
  {/if}
</div>

<div class="tools">
  <button
    type="button"
    class="badge cc"
    aria-pressed={subtitles}
    title={`${locale.t.chat.subtitles}: ${locale.t.chat.subtitlesHint}`}
    aria-label={locale.t.chat.subtitles}
    onclick={onsubtitles}>CC</button
  >
  {@render children?.()}
</div>

<style>
  .status {
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 2;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .icon {
    display: grid;
    place-items: center;
    width: 26px;
    height: 26px;
    border: 2px solid currentColor;
    border-radius: 50%;
    background: color-mix(in srgb, var(--panel) 85%, transparent);
    font-size: 13px;
    cursor: help;
  }

  .ok {
    color: #5fd38d;
  }

  .wait {
    color: #e8c35a;
  }

  .bad {
    color: var(--danger);
    box-shadow: 0 0 8px var(--danger);
  }

  .off {
    color: #55556a;
  }

  .tools {
    position: absolute;
    bottom: 10px;
    left: 10px;
    z-index: 2;
    display: flex;
    gap: 6px;
  }

  .tools :global(.badge) {
    display: grid;
    place-items: center;
    min-width: 30px;
    height: 26px;
    padding: 0 6px;
    border: 1px solid var(--edge);
    border-radius: 8px;
    background: color-mix(in srgb, var(--panel) 85%, transparent);
    color: var(--text);
    font: inherit;
    font-size: 12px;
    font-weight: 700;
    opacity: 0.7;
    cursor: pointer;
  }

  .tools :global(.badge:hover) {
    opacity: 1;
  }

  .cc[aria-pressed="true"] {
    border-color: #a77bc4;
    background: #3a2a44;
    opacity: 1;
  }
</style>
