<script lang="ts">
  import { locale } from "../../../core";
  // Окошко персонажа (Этап 23, ADR-0044): файл перетаскивают в окошко — картинка меняется; правая
  // кнопка — меню: сменить картинку, вписать или заполнить, вернуть стандартную, сфера или персонаж.
  import type { AvatarView } from "../view";
  import {
    clearPicture,
    loadFit,
    pictureProblem,
    saveFit,
    savePicture,
    windowStorage,
    type PictureFit,
  } from "./picture";

  const {
    host,
    view,
    onview,
  }: {
    host: HTMLElement | undefined;
    view: AvatarView;
    onview: (view: AvatarView) => void;
  } = $props();

  let dragging = $state(false);
  let problem = $state<string | null>(null);
  let menu = $state<{ x: number; y: number } | null>(null);
  let fit = $state<PictureFit>(loadFit(windowStorage()));
  let picker: HTMLInputElement | undefined = $state();
  // Счётчик входов: dragleave приходит и при переходе между дочерними элементами окошка.
  let depth = 0;
  let problemTimer: ReturnType<typeof setTimeout> | undefined;

  function hasFiles(event: DragEvent): boolean {
    return event.dataTransfer?.types.includes("Files") ?? false;
  }

  function report(text: string | null): void {
    problem = text;
    clearTimeout(problemTimer);
    if (text !== null) {
      problemTimer = setTimeout(() => {
        problem = null;
      }, 4000);
    }
  }

  async function take(file: File | undefined): Promise<void> {
    if (file === undefined) return;
    const why = pictureProblem(file, locale.t);
    if (why !== null) {
      report(why);
      return;
    }
    try {
      await savePicture(file);
      report(null);
      if (view !== "portrait") onview("portrait");
    } catch {
      report(locale.t.character.saveFailed);
    }
  }

  $effect(() => {
    if (host === undefined) return;
    const target = host;
    const enter = (event: DragEvent): void => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      depth += 1;
      dragging = true;
    };
    const over = (event: DragEvent): void => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      if (event.dataTransfer !== null) event.dataTransfer.dropEffect = "copy";
    };
    const leave = (): void => {
      depth = Math.max(0, depth - 1);
      if (depth === 0) dragging = false;
    };
    const drop = (event: DragEvent): void => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      depth = 0;
      dragging = false;
      void take(event.dataTransfer?.files[0]);
    };
    const context = (event: MouseEvent): void => {
      event.preventDefault();
      const box = target.getBoundingClientRect();
      menu = { x: event.clientX - box.left, y: event.clientY - box.top };
    };
    target.addEventListener("dragenter", enter);
    target.addEventListener("dragover", over);
    target.addEventListener("dragleave", leave);
    target.addEventListener("drop", drop);
    target.addEventListener("contextmenu", context);
    return () => {
      target.removeEventListener("dragenter", enter);
      target.removeEventListener("dragover", over);
      target.removeEventListener("dragleave", leave);
      target.removeEventListener("drop", drop);
      target.removeEventListener("contextmenu", context);
    };
  });

  function closeOnEscape(event: KeyboardEvent): void {
    if (event.key === "Escape") menu = null;
  }

  function closeOutside(event: PointerEvent): void {
    const inside = event.target instanceof Element && event.target.closest(".menu") !== null;
    if (menu !== null && !inside) menu = null;
  }

  function choose(next: PictureFit): void {
    fit = next;
    saveFit(windowStorage(), next);
    menu = null;
  }
</script>

<svelte:window onkeydown={closeOnEscape} onpointerdown={closeOutside} />

<input
  bind:this={picker}
  type="file"
  accept="image/png,image/jpeg,image/webp,image/gif,image/apng"
  hidden
  onchange={(event) => {
    void take(event.currentTarget.files?.[0]);
    event.currentTarget.value = "";
  }}
/>

{#if dragging}
  <div class="drop" aria-hidden="true">
    <p>{locale.t.character.drop}</p>
  </div>
{/if}

{#if problem !== null}
  <p class="problem" role="alert">{problem}</p>
{/if}

{#if menu !== null}
  <div
    class="menu"
    role="menu"
    style:left={`${String(menu.x)}px`}
    style:top={`${String(menu.y)}px`}
  >
    <button
      type="button"
      role="menuitem"
      onclick={() => {
        menu = null;
        picker?.click();
      }}>{locale.t.character.change}</button
    >
    {#if view === "portrait"}
      <button
        type="button"
        role="menuitemradio"
        aria-checked={fit === "contain"}
        onclick={() => {
          choose("contain");
        }}>{fit === "contain" ? "● " : "○ "}{locale.t.character.fitContain}</button
      >
      <button
        type="button"
        role="menuitemradio"
        aria-checked={fit === "cover"}
        onclick={() => {
          choose("cover");
        }}>{fit === "cover" ? "● " : "○ "}{locale.t.character.fitCover}</button
      >
      <button
        type="button"
        role="menuitem"
        onclick={() => {
          menu = null;
          void clearPicture().catch(() => {
            report(locale.t.character.saveFailed);
          });
        }}>{locale.t.character.reset}</button
      >
    {/if}
    <hr />
    <button
      type="button"
      role="menuitem"
      onclick={() => {
        menu = null;
        onview(view === "portrait" ? "orb" : "portrait");
      }}
      >{view === "portrait" ? locale.t.character.showOrb : locale.t.character.showPortrait}</button
    >
  </div>
{/if}

<style>
  .drop {
    position: absolute;
    inset: 10px;
    z-index: 6;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px dashed var(--title);
    border-radius: 14px;
    background: rgb(124 108 255 / 16%);
    pointer-events: none;
  }

  .drop p {
    margin: 0;
    padding: 8px 14px;
    border-radius: 8px;
    background: var(--panel);
    font-size: 1.05em;
  }

  .problem {
    position: absolute;
    left: 50%;
    bottom: 16px;
    z-index: 6;
    margin: 0;
    padding: 6px 12px;
    border-radius: 8px;
    background: rgb(60 20 20 / 92%);
    color: var(--danger);
    transform: translateX(-50%);
  }

  .menu {
    position: absolute;
    z-index: 7;
    display: flex;
    flex-direction: column;
    min-width: 210px;
    padding: 4px;
    border: 1px solid var(--edge);
    border-radius: 8px;
    background: var(--panel);
    box-shadow: 0 6px 24px rgb(0 0 0 / 45%);
    font-size: 0.88em;
  }

  .menu button {
    padding: 6px 10px;
    border: none;
    border-radius: 5px;
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  .menu button:hover,
  .menu button:focus-visible {
    background: #2c2c3a;
  }

  hr {
    width: 100%;
    margin: 4px 0;
    border: none;
    border-top: 1px solid var(--edge);
  }
</style>
