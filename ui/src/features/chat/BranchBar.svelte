<script lang="ts">
  import { locale } from "../../core";
  // Ветки диалога (S-16.1): показывается, когда есть что выбирать или куда вернуться.
  import type { CoreClient } from "../../core";

  const { client }: { client: CoreClient } = $props();

  const store = $derived(client.store);
  let name = $state("");
</script>

{#if store.branches.branches.length > 0}
  <div class="branches" aria-label={locale.t.branches.region}>
    {#if store.branches.branches.length > 1}
      <label>
        {locale.t.branches.branch}
        <select
          value={store.branches.branches.find((branch) => branch.active)?.leaf}
          onchange={(event) => {
            client.goToTurn(event.currentTarget.value);
          }}
        >
          {#each store.branches.branches as branch (branch.leaf)}
            <option value={branch.leaf}>{branch.title.slice(0, 40)} ({branch.length})</option>
          {/each}
        </select>
      </label>
    {/if}
    {#if store.branches.checkpoints.length > 0}
      <label>
        {locale.t.branches.checkpoint}
        <select
          value=""
          onchange={(event) => {
            client.goToTurn(event.currentTarget.value);
          }}
        >
          <option value="" disabled>{locale.t.branches.choose}</option>
          {#each store.branches.checkpoints as point (point.name)}
            <option value={point.turn}>{point.name}</option>
          {/each}
        </select>
      </label>
    {/if}
    <form
      onsubmit={(event) => {
        event.preventDefault();
        client.saveCheckpoint(name);
        name = "";
      }}
    >
      <input
        bind:value={name}
        placeholder={locale.t.branches.checkpointName}
        aria-label={locale.t.branches.checkpointNameLabel}
      />
      <button type="submit" disabled={name.trim() === ""}>{locale.t.branches.saveCheckpoint}</button
      >
    </form>
    {#if store.branches.problem !== null}
      <span class="warn" role="status">{store.branches.problem}</span>
    {/if}
  </div>
{/if}

<style>
  .branches {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    padding: 4px 16px;
    border-bottom: 1px solid #2c2c38;
    font-size: 0.8em;
  }

  form {
    display: inline-flex;
    gap: 4px;
  }

  select,
  input,
  button {
    max-width: 180px;
    border: 1px solid #3a3a48;
    border-radius: 6px;
    background: #22222c;
    color: inherit;
    font: inherit;
  }

  .warn {
    color: #ffc27a;
  }
</style>
