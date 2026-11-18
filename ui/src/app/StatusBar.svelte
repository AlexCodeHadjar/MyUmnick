<script lang="ts">
  import { locale } from "../core";
  // Окно настроек под персонажем (просьба пользователя 2026-11-17): голос, радио, открытие панелей.
  // Состояние ядра — значками в окошке персонажа (StageBadges), горячих клавиш нет (2026-11-18).
  import type { Snippet } from "svelte";

  const {
    children,
    panels,
    radio,
  }: {
    children?: Snippet;
    panels?: Snippet;
    radio?: Snippet;
  } = $props();
</script>

<aside class="settings" aria-label={locale.t.app.settings}>
  <h2>{locale.t.app.settings}</h2>
  <section>
    <h3>{locale.t.app.controls}</h3>
    <div class="row">{@render children?.()}</div>
  </section>
  {#if radio !== undefined}
    <section>
      <h3>{locale.t.radio.title}</h3>
      {@render radio()}
    </section>
  {/if}
  {#if panels !== undefined}
    <section>
      <h3>{locale.t.app.panels}</h3>
      <div class="row">{@render panels()}</div>
    </section>
  {/if}
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

  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }
</style>
