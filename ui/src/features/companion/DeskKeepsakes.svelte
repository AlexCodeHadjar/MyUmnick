<script lang="ts">
  import Inspection from "./look/Inspection.svelte";
  import { untrack } from "svelte";
  import type { CompanionController } from "./controller";
  import { createDesk } from "./keepsakeScene.svelte";
  import { KEEPSAKE_TIMING as timing } from "./settings";
  let { controller }: { controller: CompanionController } = $props();
  const desk = untrack(() => createDesk(controller));
  let noteDown = 0;
  export const { tick, interactiveRect, resetBuilding } = desk;
</script>

{#if desk.visible}
  <div class="actor" bind:this={desk.actor}>
    {#if desk.item}<Inspection item={desk.item} ending={desk.ending} />{/if}
  </div>
  {#if desk.note}<button
      class="note"
      bind:this={desk.noteEl}
      style:left={String(desk.note.x) + "px"}
      style:top={String(desk.note.y) + "px"}
      onpointerdown={(e) => {
        noteDown = e.clientX;
        e.currentTarget.setPointerCapture(e.pointerId);
      }}
      onpointerup={(e) => {
        if (Math.abs(e.clientX - noteDown) > 16) desk.takeNote();
      }}
      onclick={desk.takeNote}>{desk.note.text}</button
    >{/if}
  {#if desk.buildingVisible && (desk.day?.seconds ?? 0) >= timing.stepSecs}<div
      class="house"
      bind:this={desk.house}
      aria-hidden="true"
    >
      {#each Array.from({ length: Math.min(12, Math.floor((desk.day?.seconds ?? 0) / timing.stepSecs)) }, (_, i) => i) as i (i)}<i
        ></i>{/each}
    </div>{/if}
{/if}

<style>
  .actor,
  .house,
  .note {
    position: fixed;
    top: 0;
    left: 0;
  }
  .actor,
  .house {
    pointer-events: none;
  }
  .note {
    background: #fff0c5;
    color: #203047;
    padding: 6px;
    border-radius: 5px;
    font: 12px system-ui;
    box-shadow: 0 2px 5px #13243b55;
  }
  .note {
    pointer-events: auto;
    max-width: 145px;
    touch-action: none;
    border: 0;
    border-top: 5px solid #ffcf74;
  }
  .house {
    width: 66px;
    height: 48px;
    display: flex;
    flex-flow: row-reverse wrap-reverse;
    align-content: flex-start;
    gap: 1px;
  }
  .house i {
    width: 18px;
    height: 12px;
    background: linear-gradient(155deg, #ffebba 25%, #d6bb8c 26%, #ffedc6 36%);
    border: 1px solid #374e67;
    border-radius: 1px 4px 1px 1px;
  }
</style>
