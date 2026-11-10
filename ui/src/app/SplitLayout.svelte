<script lang="ts">
  import { locale } from "../core";
  // Две панели с перетаскиваемым разделителем (FR-01). Доля — в split.ts: ограничение минимумами
  // панелей и запоминание между запусками. Разделитель двигается и стрелками (role="separator").
  import type { Snippet } from "svelte";

  import {
    clampRatio,
    KEYBOARD_STEP,
    loadRatio,
    ratioAt,
    saveRatio,
    type RatioStorage,
  } from "./split";

  const {
    left,
    right,
    storage,
    onlyRight = false,
  }: {
    left: Snippet;
    right: Snippet;
    storage: RatioStorage | undefined;
    onlyRight?: boolean;
  } = $props();

  const ARROW_STEPS: Partial<Record<string, number>> = {
    ArrowLeft: -KEYBOARD_STEP,
    ArrowRight: KEYBOARD_STEP,
  };

  let container: HTMLDivElement | undefined = $state();
  let width = $state(0);
  // Читается один раз при создании: дальше доля живёт в компоненте, хранилище только пишется.
  // svelte-ignore state_referenced_locally
  let ratio = $state(loadRatio(storage));
  let dragging = $state(false);
  const effective = $derived(clampRatio(ratio, width));

  function commit(next: number): void {
    ratio = clampRatio(next, width);
    saveRatio(storage, ratio);
  }

  function onpointerdown(event: PointerEvent): void {
    if (event.currentTarget instanceof Element) {
      event.currentTarget.setPointerCapture(event.pointerId);
    }
    dragging = true;
  }

  function onpointermove(event: PointerEvent): void {
    if (!dragging || container === undefined) {
      return;
    }
    const rect = container.getBoundingClientRect();
    ratio = clampRatio(ratioAt(event.clientX, rect.left, rect.width), rect.width);
  }

  function onpointerup(): void {
    if (dragging) {
      dragging = false;
      commit(ratio);
    }
  }

  function onkeydown(event: KeyboardEvent): void {
    const step = ARROW_STEPS[event.key];
    if (step !== undefined) {
      event.preventDefault();
      commit(effective + step);
    }
  }
</script>

<div
  class="split"
  class:dragging
  bind:this={container}
  bind:clientWidth={width}
  class:only-right={onlyRight}
  style:grid-template-columns={onlyRight
    ? "0 0 1fr"
    : `${String(effective)}fr 6px ${String(1 - effective)}fr`}
>
  <div class="pane">{@render left()}</div>
  <!-- Фокусируемый separator — интерактивный виджет по WAI-ARIA (шаблон window splitter), а
       проверка Svelte считает separator неинтерактивным всегда. -->
  <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
  <div
    class="divider"
    role="separator"
    aria-orientation="vertical"
    aria-label={locale.t.app.chatWidth}
    aria-valuemin={0}
    aria-valuemax={100}
    aria-valuenow={Math.round(effective * 100)}
    tabindex="0"
    {onpointerdown}
    {onpointermove}
    {onpointerup}
    onpointercancel={onpointerup}
    {onkeydown}
  ></div>
  <div class="pane">{@render right()}</div>
</div>

<style>
  .split {
    display: grid;
    min-height: 0;
    height: 100%;
  }

  .split.dragging {
    cursor: col-resize;
    user-select: none;
  }

  .pane {
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }

  .divider {
    cursor: col-resize;
    background: #2c2c38;
    touch-action: none;
  }

  .only-right .divider {
    display: none;
  }

  .divider:hover,
  .divider:focus-visible,
  .dragging .divider {
    background: #ec70a0;
    outline: none;
  }
</style>
