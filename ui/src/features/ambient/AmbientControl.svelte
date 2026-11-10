<script lang="ts">
  // Включатель «сфера слышит звук компьютера» в строке статуса (Этап 22, ADR-0039).
  import { onMount, untrack } from "svelte";

  import { locale } from "../../core";
  import { readAmbientEnabled, SystemAudio, writeAmbientEnabled } from "./systemAudio";

  const { audio, storage }: { audio: SystemAudio; storage: Storage | undefined } = $props();

  let enabled = $state(untrack(() => readAmbientEnabled(storage)));
  let problem = $state<string | null>(null);

  async function apply(next: boolean): Promise<void> {
    problem = null;
    try {
      if (next) await audio.start();
      else await audio.stop();
      enabled = next;
      writeAmbientEnabled(storage, next);
    } catch (error) {
      enabled = false;
      problem = error instanceof Error ? error.message : String(error);
    }
  }

  onMount(() => {
    if (enabled) void apply(true);
    return () => {
      void audio.stop();
    };
  });
</script>

{#if SystemAudio.supported}
  <button
    type="button"
    class="ambient"
    class:on={enabled}
    title={problem ?? locale.t.ambient.hint}
    aria-pressed={enabled}
    onclick={() => void apply(!enabled)}
    >{enabled ? locale.t.ambient.on : locale.t.ambient.off}</button
  >
{/if}

<style>
  .ambient {
    padding: 0 6px;
    border: 1px solid #3a3f4b;
    border-radius: 3px;
    background: transparent;
    color: #9aa3b2;
    cursor: pointer;
  }
  .ambient.on {
    border-color: #66c0f4;
    color: #66c0f4;
  }
</style>
