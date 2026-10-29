<script lang="ts">
  // Сцена с аватаром: холст Live2D на всю панель, статус загрузки или ошибки поверх. Логика —
  // в session.ts и reactions.ts; движок грузится динамически, чат не ждёт Pixi и Cubism Core.
  import { onMount } from "svelte";

  import type { AppStore } from "../../core";
  import { reactionOf } from "./reactions";
  import { AvatarSession, type AvatarStatus, type MouthSource } from "./session";

  const {
    name,
    store,
    mouth = () => 0,
  }: { name: string; store: AppStore; mouth?: MouthSource } = $props();

  let host: HTMLDivElement | undefined = $state();
  let status = $state<AvatarStatus>({ state: "loading" });
  // Не реактивна: эффекты ниже перезапускаются по статусу «ready», а не по самой сессии.
  let session: AvatarSession | null = null;

  const reaction = $derived(
    reactionOf({
      phase: store.phase,
      connection: store.connection,
      lastRole: store.messages.at(-1)?.role ?? null,
      hasError: store.error !== null,
    }),
  );

  // Эффекты срабатывают в том же кадре, что и изменение store (T-17): «думаю» — сразу после
  // отправки, эмоция — в кадре, где пришёл `avatar.emotion`.
  $effect(() => {
    if (status.state === "ready") {
      session?.renderer?.react(reaction);
    }
  });

  $effect(() => {
    if (status.state === "ready") {
      session?.renderer?.setEmotion(store.emotion, 1);
    }
  });

  onMount(() => {
    if (host === undefined) {
      return;
    }
    const current = new AvatarSession(host, (next) => {
      status = next;
    });
    session = current;
    // Источник рта читается при каждом кадре через замыкание: смена пропса подхватывается.
    current.mouth = (deltaMs) => mouth(deltaMs);
    void current.start(name, async (element, size) => {
      const { Live2DRenderer } = await import("./live2d/Live2DRenderer");
      return Live2DRenderer.create(element, size);
    });
    const onmove = (event: PointerEvent): void => {
      current.lookAtPointer(event.clientX, event.clientY);
    };
    const onleave = (): void => {
      current.lookAhead();
    };
    window.addEventListener("pointermove", onmove);
    document.documentElement.addEventListener("pointerleave", onleave);
    return () => {
      window.removeEventListener("pointermove", onmove);
      document.documentElement.removeEventListener("pointerleave", onleave);
      current.dispose();
      session = null;
    };
  });
</script>

<div class="avatar" bind:this={host}>
  {#if status.state === "loading"}
    <p class="note">Загрузка модели…</p>
  {:else if status.state === "error"}
    <p class="note error" role="alert">{status.message}</p>
  {/if}
</div>

<style>
  .avatar {
    position: absolute;
    inset: 0;
    overflow: hidden;
  }

  .avatar :global(canvas) {
    display: block;
  }

  .note {
    position: absolute;
    inset: auto 16px 16px;
    margin: 0;
    text-align: center;
    opacity: 0.7;
  }

  .error {
    color: #ff8a8a;
    opacity: 1;
  }
</style>
