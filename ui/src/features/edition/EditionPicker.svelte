<script lang="ts">
  // Экран выбора издания в духе выбора аккаунта Steam (Этап 20, STAGE_20 раздел 3): плитки по центру,
  // картинка — на всю плитку, подпись снизу. Pixi и Live2D здесь не грузятся: экран — мгновенно.
  import { onMount, untrack } from "svelte";

  import { messagesFor } from "../../core";
  import {
    afterPick,
    editionAt,
    EDITIONS,
    keyAction,
    needsAgeGate,
    type Edition,
    type LauncherState,
  } from "./editions";

  const {
    initial,
    onpick,
  }: {
    initial: LauncherState;
    /** Выбор сделан и подтверждён; промис — запуск ядра (ошибка — текст под плиткой). */
    onpick: (edition: Edition, state: LauncherState) => Promise<void>;
  } = $props();

  // Язык ещё не выбран: заголовок — на обоих, остальное — на языке плитки в фокусе.
  const ru = messagesFor("ru");
  const en = messagesFor("en");

  let focused = $state(
    Math.max(
      0,
      EDITIONS.findIndex((edition) => edition.id === initial.last),
    ),
  );
  // Начальные значения из сохранённого выбора; дальше экран живёт своим состоянием.
  let remember = $state(untrack(() => initial.remember));
  let ageFor = $state<Edition | null>(null);
  let starting = $state<string | null>(null);
  let problem = $state<{ id: string; text: string } | null>(null);
  const broken = $state<Record<string, boolean>>({});
  const tiles: HTMLButtonElement[] = [];

  const t = $derived(messagesFor(editionAt(focused).lang));

  onMount(() => {
    tiles[focused]?.focus();
  });

  function choose(index: number): void {
    if (starting !== null) return;
    const edition = editionAt(index);
    focused = index;
    if (needsAgeGate(edition, initial)) {
      ageFor = edition;
      return;
    }
    void launch(edition);
  }

  async function launch(edition: Edition): Promise<void> {
    ageFor = null;
    starting = edition.id;
    problem = null;
    const today = new Date().toISOString().slice(0, 10);
    try {
      await onpick(edition, afterPick(initial, edition, remember, today));
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      problem = { id: edition.id, text: messagesFor(edition.lang).edition.failed(reason) };
      starting = null;
    }
  }

  function onkeydown(event: KeyboardEvent): void {
    if (ageFor !== null) {
      if (event.key === "Escape") ageFor = null;
      return;
    }
    const action = keyAction(event.key, focused, EDITIONS.length);
    if (action === null) return;
    event.preventDefault();
    if (action.kind === "focus") {
      focused = action.index;
      tiles[action.index]?.focus();
    } else {
      choose(action.index);
    }
  }
</script>

<svelte:window {onkeydown} />

<main class="picker">
  <h1>{ru.edition.title}<span class="sub">{en.edition.title}</span></h1>

  <div class="tiles">
    {#each EDITIONS as edition, index (edition.id)}
      <div class="slot" class:dim={starting !== null && starting !== edition.id}>
        <button
          type="button"
          class="tile {edition.id}"
          class:focused={index === focused}
          bind:this={tiles[index]}
          aria-label={messagesFor(edition.lang).edition.tile(edition.name, edition.caption)}
          onfocus={() => (focused = index)}
          onclick={() => {
            choose(index);
          }}
        >
          {#if !broken[edition.id]}
            <!-- Портрета нет — монограмма на градиенте издания: экран не ломается. -->
            <img
              src="editions/{edition.id}.webp"
              alt=""
              onerror={() => (broken[edition.id] = true)}
            />
          {/if}
          <span class="mono">{edition.id.toUpperCase()}</span>
          {#if edition.badge}<span class="badge">{edition.badge}</span>{/if}
          {#if starting === edition.id}
            <span class="busy">{messagesFor(edition.lang).edition.starting}</span>
          {/if}
        </button>
        <span class="name">{edition.name}</span>
        <span class="caption">{edition.caption}</span>
        {#if problem?.id === edition.id}<span class="error">{problem.text}</span>{/if}
      </div>
    {/each}
  </div>

  <footer>
    <label
      ><input type="checkbox" bind:checked={remember} />
      {ru.edition.remember} · {en.edition.remember}</label
    >
    <span class="keys">{t.edition.keys}</span>
  </footer>

  {#if ageFor !== null}
    <div class="gate" role="dialog" aria-modal="true" aria-labelledby="age-title">
      <div class="card">
        <h2 id="age-title">{messagesFor(ageFor.lang).edition.ageTitle}</h2>
        <p>{messagesFor(ageFor.lang).edition.ageText}</p>
        <div class="actions">
          <button
            type="button"
            class="primary"
            onclick={() => {
              if (ageFor !== null) void launch(ageFor);
            }}>{messagesFor(ageFor.lang).edition.ageConfirm}</button
          >
          <button type="button" onclick={() => (ageFor = null)}
            >{messagesFor(ageFor.lang).edition.back}</button
          >
        </div>
      </div>
    </div>
  {/if}
</main>

<style>
  .picker {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 40px;
    padding: 16px;
    box-sizing: border-box;
    background: #171a21;
    color: #c7d5e0;
    font-family: system-ui, sans-serif;
  }
  h1 {
    margin: 0;
    text-align: center;
    font-size: 26px;
    font-weight: 500;
    color: #fff;
  }
  .sub {
    display: block;
    margin-top: 6px;
    font-size: 15px;
    color: #8f98a0;
  }
  .tiles {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 48px;
  }
  .slot {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    width: 176px;
    transition: opacity 120ms;
  }
  .slot.dim {
    opacity: 0.35;
  }
  .tile {
    position: relative;
    width: 176px;
    height: 176px;
    padding: 0;
    border: 2px solid #2a475e;
    border-radius: 4px;
    overflow: hidden;
    cursor: pointer;
    transition:
      transform 120ms,
      border-color 120ms;
  }
  .tile.ru {
    background: linear-gradient(135deg, #3d6fb6, #1b2838);
  }
  .tile.en {
    background: linear-gradient(135deg, #b6475f, #1b2838);
  }
  .tile:hover,
  .tile.focused {
    border-color: #66c0f4;
    transform: translateY(-2px);
  }
  .tile:focus-visible {
    outline: 3px solid #66c0f4;
    outline-offset: 3px;
  }
  .tile img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .mono {
    position: absolute;
    left: 10px;
    bottom: 8px;
    font-size: 15px;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 1px 3px #000;
  }
  .badge {
    position: absolute;
    top: 8px;
    right: 8px;
    padding: 2px 6px;
    border-radius: 3px;
    background: #c0392b;
    color: #fff;
    font-size: 12px;
    font-weight: 700;
  }
  .busy {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background: #000a;
    color: #fff;
  }
  .name {
    color: #fff;
    font-size: 17px;
  }
  .caption {
    font-size: 13px;
    color: #8f98a0;
  }
  .error {
    font-size: 12px;
    color: #ff8a80;
    text-align: center;
  }
  footer {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
    justify-content: center;
    font-size: 13px;
    color: #8f98a0;
  }
  .gate {
    position: fixed;
    inset: 0;
    display: grid;
    place-items: center;
    padding: 16px;
    background: #000c;
  }
  .card {
    max-width: 440px;
    padding: 24px;
    border-radius: 6px;
    background: #1b2838;
  }
  .card h2 {
    margin-top: 0;
    color: #fff;
  }
  .actions {
    display: flex;
    gap: 12px;
  }
  .actions button {
    padding: 8px 16px;
    border: 0;
    border-radius: 3px;
    background: #2a475e;
    color: #fff;
    cursor: pointer;
  }
  .actions .primary {
    background: #5c7e10;
  }
  @media (prefers-reduced-motion: reduce) {
    .tile,
    .slot {
      transition: none;
    }
    .tile:hover,
    .tile.focused {
      transform: none;
    }
  }
</style>
