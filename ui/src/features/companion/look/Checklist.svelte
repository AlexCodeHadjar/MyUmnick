<script lang="ts">
  import { APP_VERSION, locale } from "../../../core";
  import type { CheckRow, Checklist } from "./checklist";
  // Панель только показывает строки: их считает слой спутника (look/checklist.ts).
  let {
    checks,
    onclose,
    panel = $bindable(null),
  }: { checks: Checklist | null; onclose: () => void; panel?: HTMLDivElement | null } = $props();
  const t = $derived(locale.t.companion.checklist);
</script>

{#snippet rows(list: CheckRow[])}
  {#each list as row (row.id)}
    <li class:ok={row.ok === true} class:no={row.ok === false}>
      <span class="name">{row.name}</span>
      <span class="value">{row.value}</span>
      {#if row.score !== undefined}<span class="bar" style:width={`${String(row.score * 100)}%`}
        ></span>{/if}
      {#if row.when}<span class="when">{row.when}</span>{/if}
    </li>
  {/each}
{/snippet}

{#if checks !== null}
  <div class="checklist u-frame" bind:this={panel}>
    <header>
      <strong>{t.title}</strong>
      <span class="version">{APP_VERSION}</span>
      <button type="button" aria-label={t.close} onclick={onclose}>×</button>
    </header>
    <h4>{t.sensors}</h4>
    <ul>{@render rows(checks.sensors)}</ul>
    <h4>{t.actions}</h4>
    <ul>{@render rows(checks.actions)}</ul>
    <h4>{t.reactions}</h4>
    <p class="when">{t.reactionsWhen}</p>
    <ul>{@render rows(checks.reactions)}</ul>
    <h4>{t.others}</h4>
    <ul>{@render rows(checks.others)}</ul>
  </div>
{/if}

<style>
  .checklist {
    position: fixed;
    z-index: 3;
    top: 16px;
    left: 16px;
    width: 400px;
    max-height: calc(100vh - 32px);
    overflow-y: auto;
    padding: 8px 12px;
    font: 13px var(--font);
    color: var(--text);
  }
  header {
    display: flex;
    gap: 8px;
    align-items: baseline;
  }
  header strong {
    flex: 1;
  }
  .version {
    color: var(--title);
    font-size: 11px;
  }
  header button {
    border: none;
    background: none;
    color: var(--text);
    font-size: 18px;
    cursor: pointer;
  }
  h4 {
    margin: 10px 0 4px;
    color: var(--title);
    font-size: 11px;
    text-transform: uppercase;
  }
  ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  li {
    position: relative;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 0 8px;
    padding: 3px 0 3px 10px;
    border-left: 3px solid var(--rule-dim);
  }
  li.ok {
    border-left-color: #4fd18b;
  }
  li.no {
    border-left-color: #c9576a;
  }
  .value {
    color: var(--value);
    font-size: 12px;
  }
  .bar {
    grid-column: 1 / -1;
    height: 3px;
    background: var(--value);
    border-radius: 2px;
  }
  .when {
    grid-column: 1 / -1;
    margin: 1px 0 0;
    color: var(--title);
    font-size: 11px;
  }
</style>
