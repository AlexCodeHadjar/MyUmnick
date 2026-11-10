<script lang="ts">
  // Значок издания в строке статуса (STAGE_20, 3.5): клик — подтверждение и перезапуск на экран выбора.
  import { locale, type AppStore } from "../../core";
  import { launcher, PICK_PARAM } from "./launcher";

  const { store }: { store: AppStore } = $props();

  let confirming = $state(false);
  const id = $derived(store.expectedEdition ?? store.edition?.id ?? null);
  const label = $derived(id === null ? null : id === "en" ? "EN 18+" : id.toUpperCase());

  async function restart(): Promise<void> {
    // Ядро останавливается до перезагрузки: новое издание займёт ту же видеопамять и порт.
    await launcher().stopCore();
    location.search = `?${PICK_PARAM}=1`;
  }
</script>

{#if label !== null}
  <span class="edition">
    <button
      type="button"
      class="badge"
      title={locale.t.edition.badgeHint}
      onclick={() => (confirming = true)}>{label}</button
    >
    {#if confirming}
      <span>{locale.t.edition.switchConfirm}</span>
      <button type="button" onclick={() => void restart()}>{locale.t.edition.switchYes}</button>
      <button type="button" onclick={() => (confirming = false)}>{locale.t.edition.cancel}</button>
    {/if}
    {#if store.editionMismatch}
      <span class="warn"
        >{locale.t.edition.mismatch(store.editionMismatch.core, store.editionMismatch.chosen)}</span
      >
    {/if}
  </span>
{/if}

<style>
  .edition {
    display: inline-flex;
    gap: 6px;
    align-items: center;
  }
  .badge {
    padding: 0 6px;
    border: 1px solid #66c0f4;
    border-radius: 3px;
    background: transparent;
    color: #66c0f4;
    font-weight: 700;
    cursor: pointer;
  }
  .warn {
    color: #ffc27a;
  }
</style>
