<script lang="ts">
  import { locale } from "../../core";
  // Кнопки режима поверх стола и работа с окном. Кнопки видны всегда, а не только над моделью:
  // модель могла не загрузиться, а окно не должно остаться без выхода.
  import { onMount } from "svelte";

  import { ClickThrough, POLL_MS } from "./clickThrough";
  import type { Point, WindowPort } from "./mode";

  const {
    port,
    pinned,
    overModel,
    onpin,
    onleave,
  }: {
    port: WindowPort;
    pinned: boolean;
    overModel: (point: Point) => boolean;
    onpin: () => void;
    onleave: () => void;
  } = $props();

  let controls: HTMLDivElement | undefined = $state();

  function overControls(point: Point): boolean {
    const box = controls?.getBoundingClientRect();
    return (
      box !== undefined &&
      point.x >= box.left &&
      point.x <= box.right &&
      point.y >= box.top &&
      point.y <= box.bottom
    );
  }

  function onpointerdown(event: PointerEvent): void {
    // Перетаскивание — за модель; за кнопки окно не таскается.
    if (event.button === 0 && !overControls({ x: event.clientX, y: event.clientY })) {
      void port.startDrag();
    }
  }

  onMount(() => {
    const through = new ClickThrough(port, (point) => overControls(point) || overModel(point));
    const timer = setInterval(() => {
      through.tick().catch((error: unknown) => {
        console.warn("[desktop] окно не ответило", error);
      });
    }, POLL_MS);
    return () => {
      clearInterval(timer);
      void through.stop();
    };
  });
</script>

<svelte:window {onpointerdown} />

<div class="controls" bind:this={controls}>
  <button type="button" aria-pressed={pinned} onclick={onpin}>
    {pinned ? locale.t.desktop.pinnedOn : locale.t.desktop.pinnedOff}
  </button>
  <button type="button" onclick={onleave}>{locale.t.desktop.leave}</button>
</div>

<style>
  .controls {
    position: fixed;
    top: 8px;
    right: 8px;
    z-index: 10;
    display: flex;
    gap: 4px;
    opacity: 0.55;
  }

  .controls:hover,
  .controls:focus-within {
    opacity: 1;
  }

  button {
    padding: 2px 8px;
    font: inherit;
    font-size: 0.75em;
    color: #e8e8f0;
    background: #15151ccc;
    border: 1px solid #2c2c38;
    border-radius: 4px;
    cursor: pointer;
  }
</style>
