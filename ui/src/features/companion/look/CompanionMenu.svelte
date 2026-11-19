<script lang="ts">
  import type { CompanionView } from "../controller/view.svelte";
  let { view }: { view: CompanionView } = $props();
  import { locale } from "../../../core";
  import { HEIGHTS } from "../settings";
</script>

{#if view.menu !== null}
  <div
    class="menu u-frame"
    role="menu"
    bind:this={view.menuEl}
    style:left={`${String(view.menu.x)}px`}
    style:top={`${String(view.menu.y)}px`}
  >
    {#each [["follow", locale.t.companion.follow], ["stay", locale.t.companion.stay], ["wander", locale.t.companion.wander]] as const as [value, label] (value)}
      <button
        type="button"
        role="menuitemradio"
        aria-checked={view.settings.behavior === value}
        onclick={() => {
          view.behave(value);
        }}>{view.settings.behavior === value ? "● " : "○ "}{label}</button
      >
    {/each}
    <hr />
    <p class="label">{locale.t.companion.size}</p>
    <div class="sizes">
      {#each HEIGHTS as height (height)}
        <button
          type="button"
          class:on={view.settings.height === height}
          onclick={() => {
            view.change({ height });
          }}>{height}</button
        >
      {/each}
    </div>
    <button
      type="button"
      role="menuitemcheckbox"
      aria-checked={view.settings.hologram}
      onclick={() => {
        view.change({ hologram: !view.settings.hologram });
        view.menu = null;
      }}>{view.settings.hologram ? "☑ " : "☐ "}{locale.t.companion.hologram}</button
    >
    <button
      type="button"
      role="menuitemcheckbox"
      aria-checked={view.settings.calm}
      onclick={() => {
        view.change({ calm: !view.settings.calm });
        view.menu = null;
      }}>{view.settings.calm ? "☑ " : "☐ "}{locale.t.companion.calm}</button
    >
    <button
      type="button"
      role="menuitem"
      onclick={() => {
        view.keepsakes?.resetBuilding();
        view.menu = null;
      }}>{locale.t.companion.keepsakes.reset}</button
    >
    <button type="button" role="menuitem" onclick={view.toggleChecklist}
      >{locale.t.companion.checklist.open}</button
    >
    <hr />
    <button type="button" role="menuitem" onclick={view.openMain}
      >{locale.t.companion.openWindow}</button
    >
    <button
      type="button"
      role="menuitem"
      onclick={() => {
        view.menu = null;
        view.change({ when: "off" });
      }}>{locale.t.companion.hide}</button
    >
  </div>
{/if}

<style>
  .menu {
    position: fixed;
    z-index: 2;
    display: flex;
    flex-direction: column;
    min-width: 200px;
    max-height: calc(100vh - 16px);
    overflow-y: auto;
    padding: 6px;
    font-family: var(--font);
    font-size: 14px;
  }

  .menu button {
    padding: 5px 10px;
    border: none;
    background: none;
    color: var(--text);
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  .menu button:hover {
    background: var(--hover);
  }

  .label {
    margin: 2px 10px;
    color: var(--title);
    font-size: 12px;
    text-transform: uppercase;
  }

  .sizes {
    display: flex;
    gap: 4px;
    padding: 2px 8px 6px;
  }

  .sizes button {
    flex: 1;
    text-align: center;
    background: var(--plate);
  }

  .sizes button.on {
    box-shadow: inset 0 0 0 1px var(--value);
    color: var(--value);
  }

  hr {
    width: 100%;
    margin: 4px 0;
    border: none;
    border-top: 1px solid var(--rule-dim);
  }
</style>
