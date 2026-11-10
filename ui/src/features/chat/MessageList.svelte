<script lang="ts">
  import { locale } from "../../core";
  // Виртуализированная история: в DOM только окно вокруг экрана (layout.ts), строки
  // позиционируются по замеренным высотам (measure.ts). Внизу список «прилипает» к новым.
  import { SvelteMap } from "svelte/reactivity";

  import type { ChatMessage } from "../../core";
  import { computeWindow, ESTIMATED_HEIGHT, isAtBottom } from "./layout";
  import { measureHeight } from "./measure";

  const {
    messages,
    textOf = (message) => message.text,
    onrewind,
  }: {
    messages: ChatMessage[];
    /** Вернуться к этой реплике витюбера и продолжить от неё (S-16.1). */
    onrewind?: (turn: string) => void;
    /** Что показать в пузыре: в режиме субтитров — часть текста, уже прозвучавшая. */
    textOf?: (message: ChatMessage) => string;
  } = $props();

  const heights = new SvelteMap<number, number>();
  let viewport: HTMLDivElement | undefined = $state();
  let scrollTop = $state(0);
  let viewportHeight = $state(0);
  // Не реактивно: меняется только прокруткой пользователя и не должно перезапускать эффекты.
  let stick = true;

  const view = $derived(
    computeWindow(messages, (m) => heights.get(m.id) ?? ESTIMATED_HEIGHT, {
      scrollTop,
      height: viewportHeight,
    }),
  );

  $effect(() => {
    if (stick && viewport !== undefined && viewport.scrollTop + viewportHeight < view.totalHeight) {
      viewport.scrollTop = view.totalHeight;
    }
  });

  function onscroll(): void {
    if (viewport === undefined) {
      return;
    }
    scrollTop = viewport.scrollTop;
    stick = isAtBottom({ scrollTop, height: viewportHeight }, view.totalHeight);
  }
</script>

<div
  class="viewport"
  bind:this={viewport}
  bind:clientHeight={viewportHeight}
  {onscroll}
  aria-label={locale.t.chat.history}
>
  <div class="canvas" style:height="{view.totalHeight}px">
    {#each view.placed as { item, top } (item.id)}
      <div
        class="row {item.role}"
        style:transform="translateY({top}px)"
        use:measureHeight={{ id: item.id, heights }}
      >
        <p class="bubble" class:cancelled={item.status === "cancelled"}>
          {#if item.image !== undefined}
            <img class="shown" src={item.image} alt={locale.t.chat.shownImage} />
          {/if}
          {textOf(item)}{#if item.status === "streaming"}<span class="caret" aria-hidden="true"
            ></span>{/if}{#if item.status === "cancelled"}<span class="mark"
              >{locale.t.chat.interrupted}</span
            >{/if}
        </p>
        {#if onrewind && item.turn !== null && item.status !== "streaming"}
          {@const turn = item.turn}
          <button
            type="button"
            class="rewind"
            title={locale.t.chat.continueHereHint}
            aria-label={locale.t.chat.continueHere}
            onclick={() => {
              onrewind(turn);
            }}>↩</button
          >
        {/if}
      </div>
    {/each}
  </div>
</div>

<style>
  .viewport {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  .canvas {
    position: relative;
  }

  .row {
    position: absolute;
    inset: 0 0 auto;
    display: flex;
    padding: 6px 16px;
    box-sizing: border-box;
  }

  .row.user {
    justify-content: flex-end;
  }

  .rewind {
    align-self: flex-end;
    margin-left: 4px;
    padding: 0 4px;
    border: none;
    background: none;
    color: inherit;
    opacity: 0;
    cursor: pointer;
  }

  .row:hover .rewind,
  .rewind:focus-visible {
    opacity: 0.7;
  }

  .shown {
    display: block;
    max-width: 100%;
    max-height: 160px;
    margin-bottom: 4px;
    border-radius: 4px;
  }

  .bubble {
    margin: 0;
    max-width: 85%;
    padding: 8px 12px;
    border-radius: 12px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    line-height: 1.4;
    background: #23232e;
  }

  .user .bubble {
    background: #3a2a44;
  }

  .bubble.cancelled {
    opacity: 0.75;
  }

  .mark {
    /* Отступ — CSS: Svelte срезает ведущий пробел в тексте элемента. */
    margin-left: 0.3em;
    font-size: 0.85em;
    opacity: 0.7;
  }

  .caret {
    display: inline-block;
    width: 0.5em;
    height: 1em;
    margin-left: 2px;
    vertical-align: text-bottom;
    background: currentColor;
    animation: blink 1s steps(1) infinite;
  }

  @keyframes blink {
    50% {
      opacity: 0;
    }
  }
</style>
