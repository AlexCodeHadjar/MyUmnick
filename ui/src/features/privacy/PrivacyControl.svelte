<script lang="ts">
  import { locale } from "../../core";
  // Приватный режим и очистка памяти (S-17.2). Режим хранит ядро, поэтому индикатор честен и после
  // перезапуска окна. Очистка — в два шага: необратимое действие не должно срабатывать от одного клика.
  import type { CoreClient } from "../../core";

  const { client }: { client: CoreClient } = $props();

  const store = $derived(client.store);
  let confirming = $state(false);
</script>

<span class="privacy">
  <button
    type="button"
    class:active={store.privacy.enabled}
    aria-pressed={store.privacy.enabled}
    title={locale.t.privacy.hint}
    onclick={() => {
      client.setPrivate(!store.privacy.enabled);
    }}
  >
    {store.privacy.enabled ? locale.t.privacy.on : locale.t.privacy.off}
  </button>
  {#if store.privacy.erasable}
    {#if confirming}
      <span class="warn">{locale.t.privacy.confirmErase}</span>
      <button
        type="button"
        class="danger"
        onclick={() => {
          confirming = false;
          client.eraseMemory();
        }}>{locale.t.privacy.erase}</button
      >
      <button
        type="button"
        onclick={() => {
          confirming = false;
        }}>{locale.t.privacy.cancel}</button
      >
    {:else}
      <button
        type="button"
        onclick={() => {
          confirming = true;
        }}>{locale.t.privacy.clear}</button
      >
    {/if}
  {/if}
  {#if store.privacy.result !== null}
    <span class="warn" role="status">{store.privacy.result}</span>
  {/if}
</span>

<style>
  .privacy {
    display: inline-flex;
    gap: 6px;
    align-items: center;
  }

  button {
    padding: 1px 8px;
    border: 1px solid #3a3a48;
    border-radius: 6px;
    background: #22222c;
    color: inherit;
    font: inherit;
    cursor: pointer;
  }

  .active {
    border-color: #ff8a8a;
    background: #5a1f1f;
    color: #fff;
    font-weight: 600;
  }

  .danger {
    background: #7a2222;
  }

  .warn {
    color: #ffc27a;
  }
</style>
