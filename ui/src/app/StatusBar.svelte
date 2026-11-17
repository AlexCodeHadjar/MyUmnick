<script lang="ts">
  import { locale } from "../core";
  // Окно настроек под персонажем (просьба пользователя 2026-11-17): состояние ядра и бэкендов, кнопки
  // голоса и приватности, открытие панелей, горячие клавиши. Тексты и цвета состояния — status.ts.
  import type { Snippet } from "svelte";

  import type { AppStore } from "../core";
  import { backendIndicator, blockedDetails, connectionIndicator } from "./status";

  const {
    store,
    hints,
    children,
    panels,
  }: { store: AppStore; hints: readonly string[]; children?: Snippet; panels?: Snippet } = $props();

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

<aside class="settings" aria-label={locale.t.app.settings}>
  <h2>{locale.t.app.settings}</h2>
  <section>
    <h3>{locale.t.app.state}</h3>
    <div class="items">
      {#each items as item (item.name)}
        <span class="item" data-testid="status-{item.name}">
          <span class="dot {item.tone}" aria-hidden="true"></span>
          {item.name}: {item.label}
        </span>
      {/each}
      {#if store.blockedViewers.length > 0}
        <span
          class="blocked"
          data-testid="status-blocked"
          title={blockedDetails(store.blockedViewers)}
        >
          {locale.t.status.viewerAttacks}: {store.blockedViewers.length}
        </span>
      {/if}
    </div>
  </section>
  <section>
    <h3>{locale.t.app.controls}</h3>
    <div class="row">{@render children?.()}</div>
  </section>
  {#if panels !== undefined}
    <section>
      <h3>{locale.t.app.panels}</h3>
      <div class="row">{@render panels()}</div>
    </section>
  {/if}
  <section>
    <h3>{locale.t.app.hotkeys}</h3>
    <ul class="hints">
      {#each hints as hint (hint)}
        <li>{hint}</li>
      {/each}
    </ul>
  </section>
</aside>

<style>
  .settings {
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-height: 0;
    padding: 14px 16px;
    overflow-y: auto;
    font-size: 0.85em;
    color: var(--text);
  }

  h2 {
    margin: 0;
    font-size: 1.15em;
    font-weight: 600;
  }

  section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  h3 {
    margin: 0;
    font-size: 0.8em;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    opacity: 0.55;
  }

  .items,
  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    align-items: center;
  }

  .row {
    gap: 8px;
  }

  .blocked {
    color: var(--hot);
  }

  .item {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    color: #b8b8c8;
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
    background: var(--danger);
  }

  .off {
    background: #55556a;
  }

  .hints {
    margin: 0;
    padding: 0;
    list-style: none;
    line-height: 1.6;
    opacity: 0.6;
  }
</style>
