<script lang="ts">
  // Сцена с аватаром: холст Live2D на всю панель, статус загрузки или ошибки поверх. Логика —
  // в session.ts; движок грузится динамически, поэтому чат не ждёт Pixi и Cubism Core.
  import { onMount } from "svelte";

  import { AvatarSession, type AvatarStatus } from "./session";

  const { name }: { name: string } = $props();

  let host: HTMLDivElement | undefined = $state();
  let status = $state<AvatarStatus>({ state: "loading" });

  onMount(() => {
    if (host === undefined) {
      return;
    }
    const session = new AvatarSession(host, (next) => {
      status = next;
    });
    void session.start(name, async (element, size) => {
      const { Live2DRenderer } = await import("./live2d/Live2DRenderer");
      return Live2DRenderer.create(element, size);
    });
    const onmove = (event: PointerEvent): void => {
      session.lookAtPointer(event.clientX, event.clientY);
    };
    const onleave = (): void => {
      session.lookAhead();
    };
    window.addEventListener("pointermove", onmove);
    document.documentElement.addEventListener("pointerleave", onleave);
    return () => {
      window.removeEventListener("pointermove", onmove);
      document.documentElement.removeEventListener("pointerleave", onleave);
      session.dispose();
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
