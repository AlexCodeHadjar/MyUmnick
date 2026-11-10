<script lang="ts">
  // Поверх стола видно только персонажа: кнопок нет. Обратно — двойной щелчок по персонажу или
  // Ctrl+Shift+O (App). Здесь — перетаскивание за модель и клики сквозь пустое место окна.
  import { onMount } from "svelte";

  import { ClickThrough, POLL_MS } from "./clickThrough";
  import type { Point, WindowPort } from "./mode";

  const { port, overModel }: { port: WindowPort; overModel: (point: Point) => boolean } = $props();

  // Перетаскивание — за модель и только после сдвига: простой и двойной щелчок окно не таскают,
  // иначе система забирает мышь и двойной щелчок (смена режима) не доходит.
  const DRAG_PX = 4;
  let pressed: Point | null = null;

  function onpointerdown(event: PointerEvent): void {
    const point = { x: event.clientX, y: event.clientY };
    pressed = event.button === 0 && overModel(point) ? point : null;
  }

  function onpointermove(event: PointerEvent): void {
    if (pressed === null || (event.buttons & 1) === 0) {
      pressed = null;
      return;
    }
    if (Math.hypot(event.clientX - pressed.x, event.clientY - pressed.y) >= DRAG_PX) {
      pressed = null;
      void port.startDrag();
    }
  }

  onMount(() => {
    const through = new ClickThrough(port, overModel);
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

<svelte:window {onpointerdown} {onpointermove} onpointerup={() => (pressed = null)} />
