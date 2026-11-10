<script lang="ts">
  import { locale } from "../../core";
  // Панель метрик для разработчика (FR-15): задержки стадий хода — от ядра (`metrics.span`) и
  // замер самого UI. Поверх сцены, не отнимает место у чата; открывается горячей клавишей.
  import { SPAN_HISTORY, type AppStore } from "../../core";
  import { overBudget, summarizeAll } from "./stats";

  const { store, onclose }: { store: AppStore; onclose: () => void } = $props();

  const rows = $derived(summarizeAll(store.spans));

  const ms = (value: number): string => (Number.isNaN(value) ? "—" : value.toFixed(1));
</script>

<aside class="metrics" aria-label={locale.t.metrics.region}>
  <header>
    <h2>{locale.t.metrics.title}</h2>
    <button type="button" onclick={onclose} aria-label={locale.t.metrics.close}>×</button>
  </header>
  {#if rows.length === 0}
    <p class="empty">{locale.t.metrics.empty}</p>
  {:else}
    <table>
      <thead>
        <tr>
          <th>{locale.t.metrics.stage}</th><th>{locale.t.metrics.last}</th><th>p50</th><th>p95</th
          ><th>{locale.t.metrics.norm}</th><th>n</th>
        </tr>
      </thead>
      <tbody>
        {#each rows as row (row.name)}
          <tr class:over={overBudget(row)}>
            <td class="name">{row.name}</td>
            <td>{ms(row.last)}</td>
            <td>{ms(row.p50)}</td>
            <td>{ms(row.p95)}</td>
            <td>{row.budget === null ? "—" : `≤ ${String(row.budget)}`}</td>
            <td>{row.count}</td>
          </tr>
        {/each}
      </tbody>
    </table>
    <p class="note">{locale.t.metrics.note(SPAN_HISTORY)}</p>
  {/if}
</aside>

<style>
  .metrics {
    position: absolute;
    top: 12px;
    right: 12px;
    min-width: 360px;
    padding: 10px 14px;
    border: 1px solid #2c2c38;
    border-radius: 10px;
    background: rgb(17 17 23 / 92%);
    font-size: 0.85em;
    font-variant-numeric: tabular-nums;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  h2 {
    margin: 0;
    font-size: 1em;
  }

  header button {
    border: none;
    background: none;
    color: inherit;
    font-size: 1.3em;
    cursor: pointer;
  }

  table {
    width: 100%;
    margin-top: 8px;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 3px 6px;
    text-align: right;
  }

  th:first-child,
  .name {
    text-align: left;
  }

  th {
    font-weight: normal;
    opacity: 0.6;
  }

  .over td {
    color: #ff8a8a;
  }

  .empty,
  .note {
    margin: 8px 0 0;
    opacity: 0.6;
  }
</style>
