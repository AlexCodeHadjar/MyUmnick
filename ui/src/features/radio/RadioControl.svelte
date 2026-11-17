<script lang="ts">
  // Радио в окне настроек (ADR-0049): включить, ⏮ ⏯ ⏭, станция, громкость, своя станция.
  import { onMount, untrack } from "svelte";

  import { locale } from "../../core";
  import type { RadioPlayer } from "./player";

  const { player }: { player: RadioPlayer } = $props();

  let mode = $state(untrack(() => player.mode));
  let index = $state(untrack(() => player.index));
  let volume = $state(untrack(() => player.volume));
  let stations = $state(untrack(() => player.stations));
  let adding = $state(false);
  let name = $state("");
  let url = $state("");
  let wrong = $state(false);

  onMount(() =>
    player.subscribe(() => {
      mode = player.mode;
      index = player.index;
      volume = player.volume;
      stations = player.stations;
    }),
  );

  const on = $derived(mode !== "off");
  const playing = $derived(mode === "playing" || mode === "loading");
  const status = $derived(
    mode === "loading" ? locale.t.radio.loading : mode === "failed" ? locale.t.radio.failed : "",
  );

  function add(event: SubmitEvent): void {
    event.preventDefault();
    wrong = !player.add(name, url);
    if (wrong) return;
    adding = false;
    name = "";
    url = "";
  }
</script>

<div class="radio" title={locale.t.radio.hint}>
  <div class="row">
    <button
      type="button"
      class="power"
      class:on
      aria-pressed={on}
      onclick={() => {
        if (on) player.off();
        else void player.play();
      }}>📻 {on ? locale.t.radio.off : locale.t.radio.on}</button
    >
    <button
      type="button"
      title={locale.t.radio.prev}
      onclick={() => {
        player.command("prev");
      }}>⏮</button
    >
    <button
      type="button"
      title={playing ? locale.t.radio.pause : locale.t.radio.play}
      onclick={() => {
        player.toggle();
      }}>{playing ? "⏸" : "▶"}</button
    >
    <button
      type="button"
      title={locale.t.radio.next}
      onclick={() => {
        player.command("next");
      }}>⏭</button
    >
  </div>
  <div class="row">
    <select
      aria-label={locale.t.radio.station}
      value={index}
      onchange={(event) => {
        player.select(Number(event.currentTarget.value));
      }}
    >
      {#each stations as one, i (one.url)}
        <option value={i}>{one.name}</option>
      {/each}
    </select>
    <input
      type="range"
      min="0"
      max="1"
      step="0.05"
      aria-label={locale.t.radio.volume}
      value={volume}
      oninput={(event) => {
        player.setVolume(Number(event.currentTarget.value));
      }}
    />
    <button
      type="button"
      title={locale.t.radio.add}
      onclick={() => {
        adding = !adding;
      }}>＋</button
    >
  </div>
  {#if status !== ""}
    <span class="status">{status}</span>
  {/if}
  {#if adding}
    <form class="row" onsubmit={add}>
      <input placeholder={locale.t.radio.namePrompt} bind:value={name} />
      <input placeholder={locale.t.radio.addPrompt} bind:value={url} class:wrong />
      <button type="submit">{locale.t.radio.add}</button>
    </form>
  {/if}
</div>

<style>
  .radio {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }

  button,
  select,
  input {
    padding: 2px 8px;
    border: 1px solid var(--edge);
    border-radius: 6px;
    background: var(--plate);
    color: inherit;
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  .power.on {
    border-color: var(--accent);
  }

  select {
    max-width: 220px;
  }

  input[type="range"] {
    width: 110px;
    padding: 0;
  }

  .wrong {
    border-color: var(--danger);
  }

  .status {
    opacity: 0.7;
  }
</style>
