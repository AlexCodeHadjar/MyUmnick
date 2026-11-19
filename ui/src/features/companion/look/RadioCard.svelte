<script lang="ts">
  import type { CompanionView } from "../controller/view.svelte";
  import { locale } from "../../../core";
  import { sendRadioCommand } from "../../radio";

  const commands = ["prev", "off", "next"] as const;
  let { view }: { view: CompanionView } = $props();
</script>

{#if view.radio !== null && view.radioAt !== null}
  <div
    class="radio-card"
    bind:this={view.radioEl}
    style:left={`${String(view.radioAt.x)}px`}
    style:top={`${String(view.radioAt.y)}px`}
    style:width={`${String(view.radioAt.w)}px`}
    style:height={`${String(view.radioAt.h)}px`}
  >
    {#each commands as command (command)}
      <button
        type="button"
        aria-label={locale.t.radio[command]}
        title={locale.t.radio[command]}
        onclick={() => {
          sendRadioCommand(command);
        }}
      ></button>
    {/each}
  </div>
{/if}

<style>
  .radio-card {
    position: fixed;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    background: url("./radio-controls.webp") center / 100% 100% no-repeat;
  }
  button {
    border: 0;
    padding: 0;
    background: transparent;
    cursor: pointer;
  }
  button:hover,
  button:focus-visible {
    background: #60e8ff26;
  }
  button:active {
    background: #06162a66;
  }
</style>
