<script lang="ts">
  import DeskKeepsakes from "./DeskKeepsakes.svelte";
  import { createView } from "./controller/view.svelte";
  import RadioCard from "./look/RadioCard.svelte";
  import CompanionMenu from "./look/CompanionMenu.svelte";
  import Checklist from "./look/Checklist.svelte";
  const view = createView();
</script>

<svelte:window onkeydown={view.cancelAim} />

<canvas
  bind:this={view.canvas}
  class="layer"
  onpointerdown={view.down}
  onpointermove={view.move}
  onpointerup={view.up}
  ondblclick={view.dblclick}
  oncontextmenu={(event) => {
    event.preventDefault();
    view.menu = { x: event.clientX, y: event.clientY };
  }}
></canvas>

<DeskKeepsakes controller={view.controller} bind:this={view.keepsakes} />

{#if view.bubble !== null}
  <p
    class="bubble"
    bind:this={view.bubbleEl}
    style:left={`${String(view.bubble.x)}px`}
    style:top={`${String(view.bubble.y)}px`}
  >
    {view.bubble.text}
  </p>
{/if}
<RadioCard {view} /><CompanionMenu {view} /><Checklist
  checks={view.checks}
  onclose={view.toggleChecklist}
  bind:panel={view.checklistEl}
/>

<style>
  :global(html.companion-layer),
  :global(html.companion-layer body) {
    margin: 0;
    overflow: hidden;
    background: transparent;
    /* Текст спутника не выделяется ни кликом, ни протяжкой: это персонаж, а не страница. */
    user-select: none;
    -webkit-user-select: none;
  }

  .layer {
    /* Над персонажем — рука: его можно погладить (над пустым местом клики идут сквозь слой). */
    cursor: pointer;
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
  }

  .bubble {
    position: fixed;
    max-width: 280px;
    margin: 0;
    padding: 8px 12px;
    border-radius: 10px 10px 10px 2px;
    background: var(--panel);
    box-shadow: inset 0 0 0 1px var(--rule);
    color: var(--text);
    font-family: var(--font);
    font-size: 15px;
    line-height: 1.3;
    pointer-events: none;
    user-select: none;
    -webkit-user-select: none;
    overflow-wrap: anywhere;
  }
</style>
