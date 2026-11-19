<script lang="ts">
  // Кнопка чек-листа у персонажа в главном окне (просьба пользователя 2026-11-18): строки присылает слой
  // спутника — там датчики и «Разум»; спутник может быть спрятан, чек-лист всё равно считается.
  import { onDestroy } from "svelte";
  import { locale } from "../../core";
  import Checklist from "./look/Checklist.svelte";
  import type { Checklist as Rows } from "./look/checklist";
  import { watchChecklist } from "./look/checklistLink";

  let open = $state(false);
  let rows = $state<Rows | null>(null);
  let stop: (() => void) | null = null;

  function toggle(): void {
    open = !open;
    stop?.();
    stop = null;
    rows = null;
    if (open)
      stop = watchChecklist((next) => {
        rows = next;
      });
  }
  onDestroy(() => stop?.());
</script>

<button
  type="button"
  class="checklist-button"
  title={locale.t.companion.checklist.open}
  aria-pressed={open}
  onclick={toggle}>☑</button
>
{#if open}
  {#if rows === null}
    <p class="waiting u-frame">{locale.t.companion.checklist.waiting}</p>
  {/if}
  <Checklist checks={rows} onclose={toggle} />
{/if}

<style>
  .checklist-button {
    border: none;
    background: none;
    color: var(--text);
    font-size: 16px;
    cursor: pointer;
  }
  .waiting {
    position: fixed;
    z-index: 3;
    top: 16px;
    left: 16px;
    padding: 8px 12px;
    font: 13px var(--font);
  }
</style>
