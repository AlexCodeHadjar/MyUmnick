<script lang="ts">
  import { locale } from "../../core";
  // Сцена с персонажем: вид показа на всю панель, статус загрузки или ошибки поверх. Логика —
  // в session.ts, reactions.ts и mood.ts; рендер вида — отдельный чанк, чат его не ждёт.
  import { onMount } from "svelte";

  import type { AppStore } from "../../core";
  import type { AvatarView } from "./view";
  import type { AvatarReaction } from "./AvatarRenderer";
  import { isWaiting, THINKING_AFTER_MS } from "./reactions";
  import {
    AvatarSession,
    type AmbientSource,
    type AvatarStatus,
    type MouthSource,
    type RendererFactory,
  } from "./session";

  // Каждый вид — свой лёгкий чанк (ADR-0038): чат не ждёт загрузки рендера.
  const RENDERERS: Record<AvatarView, RendererFactory> = {
    orb: async (element, size) => {
      const { OrbRenderer } = await import("./orb/OrbRenderer");
      return OrbRenderer.create(element, size);
    },
  };

  const {
    view,
    store,
    mouth = () => 0,
    mouthForm = () => 0,
    ambient = () => ({ bass: 0, mid: 0, high: 0 }),
    onhittest,
  }: {
    view: AvatarView;
    store: AppStore;
    mouth?: MouthSource;
    /** Форма рта, -1…1 (ADR-0023). */
    mouthForm?: () => number;
    /** Звук компьютера (Этап 22): басы, середина, верха 0…1. */
    ambient?: AmbientSource;
    /** Получить проверку «над моделью ли точка сцены»: окну поверх стола (S-15.2). */
    onhittest?: (contains: (x: number, y: number) => boolean) => void;
  } = $props();

  let host: HTMLDivElement | undefined = $state();
  let status = $state<AvatarStatus>({ state: "loading" });
  // Не реактивна: эффекты ниже перезапускаются по статусу «ready», а не по самой сессии.
  let session: AvatarSession | null = null;

  const speaking = $derived(store.voice.speech?.speaking ?? false);
  const waiting = $derived(
    isWaiting({
      phase: store.phase,
      connection: store.connection,
      lastRole: store.messages.at(-1)?.role ?? null,
      hasError: store.error !== null,
      voiceExpected: store.backends.tts === "ready",
      voiceStarted: store.turn !== null && store.voice.speech?.turn === store.turn,
    }),
  );
  // «Думаю» — только если ответ медленнее порога: таймер с начала ожидания.
  let waitedLong = $state(false);
  const reaction = $derived<AvatarReaction>(waiting && waitedLong ? "thinking" : "idle");
  // Не реактивен: кивок один раз на ход, даже если эффект перезапустится по статусу сцены.
  let noddedTurn: string | null = null;
  // Не реактивен: тот же жест не играется второй раз, если эффект перезапустится по статусу.
  let playedGesture = 0;

  $effect(() => {
    if (!waiting) {
      waitedLong = false;
      return;
    }
    const timer = setTimeout(() => {
      waitedLong = true;
    }, THINKING_AFTER_MS);
    return () => {
      clearTimeout(timer);
    };
  });

  // Эффекты срабатывают в том же кадре, что и изменение store (T-17): кивок — в кадре
  // `turn.started`, эмоция — в кадре, где пришёл `avatar.emotion`.
  $effect(() => {
    if (status.state === "ready") {
      session?.renderer?.react(reaction);
    }
  });

  // Обращение по имени («Умник…»): внимание сразу, ещё до того, как фраза договорена.
  let seenCalls = 0;
  $effect(() => {
    const calls = store.called;
    if (status.state === "ready" && calls !== seenCalls) {
      seenCalls = calls;
      session?.renderer?.attend?.();
    }
  });

  $effect(() => {
    const turn = store.turn;
    if (status.state === "ready" && turn !== null && turn !== noddedTurn) {
      noddedTurn = turn;
      session?.renderer?.nod();
    }
  });

  $effect(() => {
    const gesture = store.gesture;
    if (status.state === "ready" && gesture !== null && gesture.seq !== playedGesture) {
      playedGesture = gesture.seq;
      session?.renderer?.gesture(gesture.name);
    }
  });

  $effect(() => {
    // Эмоция читается до `session?.`: иначе при пустой сессии чтение не случится и эффект не
    // подпишется на смену эмоции.
    const emotion = store.emotion;
    session?.mood.set(emotion);
  });

  $effect(() => {
    if (status.state === "ready") {
      session?.renderer?.setSpeaking(speaking);
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
    onhittest?.((x, y) => current.renderer?.contains(x, y) ?? false);
    // Источник рта читается при каждом кадре через замыкание: смена пропса подхватывается.
    current.mouth = (deltaMs) => mouth(deltaMs);
    current.mouthForm = () => mouthForm();
    current.ambient = () => ambient();
    // Разговор идёт, пока идёт ход или звучит голос: эмоция угасает только после речи.
    current.activity = () => store.phase !== "idle" || (store.voice.speech?.speaking ?? false);
    void current.start(RENDERERS[view]);
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
    <p class="note">{locale.t.avatar.loading}</p>
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
