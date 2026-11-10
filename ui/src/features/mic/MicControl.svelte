<script lang="ts">
  import { locale } from "../../core";
  // Голосовой ввод: режим «выключен / всегда слушать / по клавише F9» (FR-голос, Этап 11). Захват
  // живёт, пока режим не «выключен»; кадры идут ядру через CoreClient (R-63). Отказ в доступе к
  // микрофону не мешает чату: режим откатывается, причина — в подсказке.
  import { onMount } from "svelte";

  import type { CoreClient } from "../../core";
  import { MIC_SAMPLE_RATE } from "./framer";
  import { MicCapture } from "./MicCapture";
  import { isPushToTalk, micModes, parseMode, TRAILING_SILENCE_MS, type MicMode } from "./mode";

  const MODE_KEY = "vtuber.mic.mode";

  const { client, storage }: { client: CoreClient; storage?: Storage | undefined } = $props();

  let mode = $state<MicMode>("off");
  let problem = $state<string | null>(null);
  // Не реактивны: смена не должна перезапускать эффекты; переключения идут по очереди (`apply`).
  let capture: MicCapture | null = null;
  let applying: Promise<void> = Promise.resolve();

  function remembered(): MicMode {
    try {
      return parseMode(storage?.getItem(MODE_KEY) ?? null);
    } catch {
      return "off";
    }
  }

  function remember(next: MicMode): void {
    try {
      storage?.setItem(MODE_KEY, next);
    } catch {
      // Не запомнится — режим работает до перезапуска.
    }
  }

  async function apply(next: MicMode): Promise<void> {
    problem = null;
    if (next === "off") {
      await capture?.stop();
      capture = null;
      return;
    }
    try {
      capture ??= await MicCapture.start((pcm) => {
        client.micFrame(pcm, MIC_SAMPLE_RATE);
      });
      capture.setOpen(next === "always", TRAILING_SILENCE_MS);
    } catch (error) {
      problem = error instanceof Error ? error.message : String(error);
      mode = "off";
      remember("off");
    }
  }

  function choose(next: MicMode): void {
    mode = next;
    remember(next);
    // По очереди: быстрые переключения не откроют микрофон дважды.
    applying = applying.then(() => apply(next));
  }

  function onkeydown(event: KeyboardEvent): void {
    if (mode === "push" && isPushToTalk(event) && !event.repeat) {
      event.preventDefault();
      capture?.setOpen(true, TRAILING_SILENCE_MS);
    }
  }

  function onkeyup(event: KeyboardEvent): void {
    if (mode === "push" && isPushToTalk(event)) {
      capture?.setOpen(false, TRAILING_SILENCE_MS);
    }
  }

  onMount(() => {
    const saved = remembered();
    if (saved !== "off") {
      choose(saved);
    }
    return () => {
      void capture?.stop();
      capture = null;
    };
  });
</script>

<svelte:window {onkeydown} {onkeyup} />

<label class="mic" title={problem ?? locale.t.mic.title}>
  <span class:error={problem !== null}>🎤</span>
  <select
    aria-label={locale.t.mic.mode}
    value={mode}
    onchange={(event) => {
      choose(parseMode(event.currentTarget.value));
    }}
  >
    {#each micModes(locale.t) as option (option.value)}
      <option value={option.value}>{option.label}</option>
    {/each}
  </select>
</label>

<style>
  .mic {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.85em;
  }

  .error {
    filter: grayscale(1);
  }

  select {
    border: 1px solid #44445a;
    border-radius: 6px;
    background: #23232e;
    color: inherit;
    font: inherit;
  }
</style>
