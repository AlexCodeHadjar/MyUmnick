<script lang="ts">
  import { locale } from "../../core";
  // Панель ресурсов (FR-29): что сейчас в видеопамяти, кто и почему ждёт, нагрузка во времени.
  // Снимки ядро шлёт только при открытой панели: закрытая ничего не считает и не занимает кадр.
  import { untrack } from "svelte";

  import type { CoreClient } from "../../core";
  import { addSnapshot, sparkline, stateLabel, type LoadHistory } from "./history";

  const { client, onclose }: { client: CoreClient; onclose: () => void } = $props();

  const GRAPH_SIZE: [number, number] = [160, 24];

  const history: LoadHistory = new Map();
  let frame = $state(0);

  const snapshot = $derived(client.store.resources);

  $effect(() => {
    untrack(() => {
      client.watchResources(true);
    });
    return () => {
      client.watchResources(false);
    };
  });

  $effect(() => {
    if (snapshot !== null) {
      addSnapshot(history, snapshot);
      // Без untrack эффект подписался бы на свой же счётчик и зациклился.
      frame = untrack(() => frame) + 1;
    }
  });
</script>

<aside class="resources" aria-label={locale.t.resources.title}>
  <header>
    <h2>{locale.t.resources.title}</h2>
    <button type="button" onclick={onclose} aria-label={locale.t.resources.close}>×</button>
  </header>
  {#if snapshot === null}
    <p class="note">{locale.t.resources.waiting}</p>
  {:else}
    <p class="limits">
      {locale.t.resources.free(snapshot.free_mb, snapshot.limit_mb)}
      {#if snapshot.limit_mb < snapshot.capacity_mb}
        <span class="warn">{locale.t.resources.lessOnCard(snapshot.capacity_mb)}</span>
      {/if}
    </p>
    <p class="note">
      {locale.t.resources.pinned}
      {snapshot.pinned
        .map((item) => `${item.name} ${String(item.vram_mb)} ${locale.t.resources.mb}`)
        .join(", ")}
    </p>
    {#if snapshot.models.length === 0}
      <p class="note">{locale.t.resources.none}</p>
    {:else}
      <table>
        <thead>
          <tr
            ><th>{locale.t.resources.model}</th><th>{locale.t.resources.mb}</th><th
              >{locale.t.resources.priority}</th
            ><th>{locale.t.resources.state}</th><th>{locale.t.resources.load}</th></tr
          >
        </thead>
        <tbody>
          {#each snapshot.models as model (model.name)}
            <tr>
              <td class="name">{model.name}</td>
              <td>{model.vram_mb}</td>
              <td>{model.priority}</td>
              <td class="state">
                {stateLabel(model.state, locale.t)}
                {#if model.waiting_reason !== null}<span class="warn">: {model.waiting_reason}</span
                  >{/if}
              </td>
              <td>
                {#key frame}
                  <svg width={GRAPH_SIZE[0]} height={GRAPH_SIZE[1]} aria-hidden="true">
                    <polyline
                      points={sparkline(
                        history.get(model.name) ?? [],
                        snapshot.capacity_mb,
                        GRAPH_SIZE,
                      )}
                    />
                  </svg>
                {/key}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  {/if}
</aside>

<style>
  .resources {
    position: absolute;
    bottom: 12px;
    right: 12px;
    min-width: 420px;
    max-width: calc(100% - 24px);
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

  .limits {
    margin: 8px 0 0;
  }

  .note {
    margin: 4px 0 0;
    opacity: 0.6;
  }

  .warn {
    color: #ffc27a;
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
    vertical-align: middle;
  }

  th:first-child,
  .name,
  .state {
    text-align: left;
  }

  th {
    font-weight: normal;
    opacity: 0.6;
  }

  polyline {
    fill: none;
    stroke: #8ab4ff;
    stroke-width: 1.5;
  }
</style>
