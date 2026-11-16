<script lang="ts">
  import { locale } from "../../core";
  // Оформление (ADR-0047): цветовой круг с тремя маркерами — основной цвет, «значения», «акценты».
  // Окно перекрашивается на лету, пока тянете маркер; тема запоминается, палитры можно сохранить.
  import { untrack } from "svelte";
  import { fly } from "svelte/transition";

  import {
    applyTheme,
    DEFAULT_THEME,
    deletePreset,
    fromHex,
    loadPresets,
    loadTheme,
    pointOf,
    savePreset,
    saveTheme,
    swatchAt,
    toHex,
    type Preset,
    type Swatch,
    type Theme,
  } from "./palette";

  type Role = "main" | "value" | "hot";

  const { storage, onclose }: { storage: Storage | undefined; onclose: () => void } = $props();

  const RADIUS = 110;
  const ROLES: readonly Role[] = ["main", "value", "hot"];

  // Хранилище окна не меняется за жизнь панели: читаем один раз при открытии.
  const initial = untrack(() => loadTheme(storage));
  let theme = $state<Theme>(initial);
  let presets = $state<Preset[]>(untrack(() => loadPresets(storage)));
  let role = $state<Role>("main");
  let name = $state("");
  let hex = $state(toHex(initial.main));
  let wheel: HTMLDivElement | undefined = $state();
  let dragging = false;

  function show(next: Theme, keep = false): void {
    theme = next;
    applyTheme(next);
    hex = toHex(next[role]);
    // Пока тянут маркер — только перекраска; запоминаем при отпускании (спутник узнает по `storage`).
    if (!keep) saveTheme(storage, next);
  }

  function withRole(base: Theme, which: Role, swatch: Swatch): Theme {
    if (which === "main") return { ...base, main: swatch };
    if (which === "value") return { ...base, value: swatch };
    return { ...base, hot: swatch };
  }

  function setRole(next: Role): void {
    role = next;
    hex = toHex(theme[next]);
  }

  function pick(event: PointerEvent, keep: boolean): void {
    if (wheel === undefined) return;
    const box = wheel.getBoundingClientRect();
    const swatch = swatchAt(
      event.clientX - (box.left + box.width / 2),
      event.clientY - (box.top + box.height / 2),
      RADIUS,
    );
    show(withRole(theme, role, swatch), keep);
  }

  /** Нажатие рядом с чужим маркером выбирает его роль, иначе двигает выбранный. */
  function nearest(event: PointerEvent): void {
    if (wheel === undefined) return;
    const box = wheel.getBoundingClientRect();
    const dx = event.clientX - (box.left + box.width / 2);
    const dy = event.clientY - (box.top + box.height / 2);
    for (const one of ROLES) {
      const point = pointOf(theme[one], RADIUS);
      if (Math.hypot(point.x - dx, point.y - dy) < 14) {
        setRole(one);
        return;
      }
    }
  }

  function chip(swatch: Swatch): string {
    return toHex(swatch);
  }

  function presetName(preset: Preset): string {
    if (!preset.builtIn) return preset.name;
    return (
      new Map<string, string>(Object.entries(locale.t.theme.presets)).get(preset.name) ??
      preset.name
    );
  }
</script>

<aside
  class="theme u-frame"
  aria-label={locale.t.theme.title}
  transition:fly={{ x: 360, duration: 180 }}
>
  <header>
    <h2 class="u-section">{locale.t.theme.title}</h2>
    <button type="button" class="close" onclick={onclose} aria-label={locale.t.theme.close}
      >×</button
    >
  </header>

  <div class="roles" role="radiogroup" aria-label={locale.t.theme.role}>
    {#each ROLES as one (one)}
      <button
        type="button"
        role="radio"
        aria-checked={role === one}
        class:on={role === one}
        onclick={() => {
          setRole(one);
        }}
      >
        <span class="dot" style:background={chip(theme[one])}></span>{locale.t.theme.roles[one]}
      </button>
    {/each}
  </div>

  <div
    class="wheel"
    bind:this={wheel}
    role="slider"
    tabindex="0"
    aria-label={locale.t.theme.wheel}
    aria-valuemin={0}
    aria-valuemax={360}
    aria-valuenow={Math.round(theme[role].h)}
    onpointerdown={(event) => {
      nearest(event);
      dragging = true;
      event.currentTarget.setPointerCapture(event.pointerId);
      pick(event, true);
    }}
    onpointermove={(event) => {
      if (dragging) pick(event, true);
    }}
    onpointerup={(event) => {
      dragging = false;
      pick(event, false);
    }}
    onkeydown={(event) => {
      const step = event.shiftKey ? 10 : 2;
      const current = theme[role];
      if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
        event.preventDefault();
        const h = (current.h + (event.key === "ArrowRight" ? step : -step) + 360) % 360;
        show(withRole(theme, role, { ...current, h }));
      } else if (event.key === "ArrowUp" || event.key === "ArrowDown") {
        event.preventDefault();
        const s = Math.min(1, Math.max(0, current.s + (event.key === "ArrowUp" ? 0.05 : -0.05)));
        show(withRole(theme, role, { ...current, s }));
      }
    }}
  >
    {#each ROLES as one (one)}
      {@const point = pointOf(theme[one], RADIUS)}
      <span
        class="handle"
        class:active={role === one}
        style:left={`${String(RADIUS + point.x)}px`}
        style:top={`${String(RADIUS + point.y)}px`}
        style:background={chip(theme[one])}
      ></span>
    {/each}
  </div>

  <label class="row">
    <span>{locale.t.theme.hex}</span>
    <input
      type="text"
      value={hex}
      maxlength="7"
      spellcheck="false"
      onchange={(event) => {
        const swatch = fromHex(event.currentTarget.value);
        if (swatch === null) event.currentTarget.value = hex;
        else show(withRole(theme, role, swatch));
      }}
    />
    <span class="preview" style:background={hex}></span>
  </label>

  <label class="row">
    <span>{locale.t.theme.depth}</span>
    <input
      type="range"
      min="0"
      max="1"
      step="0.01"
      value={theme.depth}
      oninput={(event) => {
        show({ ...theme, depth: Number(event.currentTarget.value) }, true);
      }}
      onchange={(event) => {
        show({ ...theme, depth: Number(event.currentTarget.value) });
      }}
    />
  </label>

  <h3>{locale.t.theme.saved}</h3>
  <ul class="presets">
    {#each presets as preset (`${String(preset.builtIn)}:${preset.name}`)}
      <li>
        <button
          type="button"
          class="preset"
          onclick={() => {
            show(preset.theme);
          }}
        >
          <span class="dots">
            {#each ROLES as one (one)}<span class="dot" style:background={chip(preset.theme[one])}
              ></span>{/each}
          </span>
          {presetName(preset)}
        </button>
        {#if !preset.builtIn}
          <button
            type="button"
            class="remove"
            aria-label={locale.t.theme.remove(preset.name)}
            onclick={() => {
              presets = deletePreset(storage, preset.name);
            }}>×</button
          >
        {/if}
      </li>
    {/each}
  </ul>

  <form
    class="row save"
    onsubmit={(event) => {
      event.preventDefault();
      presets = savePreset(storage, name, theme);
      name = "";
    }}
  >
    <input type="text" placeholder={locale.t.theme.name} maxlength="40" bind:value={name} />
    <button type="submit" disabled={name.trim() === ""}>{locale.t.theme.save}</button>
  </form>
  <button
    type="button"
    class="reset"
    onclick={() => {
      show(DEFAULT_THEME);
    }}>{locale.t.theme.reset}</button
  >
</aside>

<style>
  .theme {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 5;
    width: min(320px, 100%);
    overflow: auto;
    box-sizing: border-box;
    padding: 12px 14px;
    font-size: 0.85em;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .close {
    border: none;
    background: none;
    color: inherit;
    font-size: 1.3em;
    cursor: pointer;
  }

  .roles {
    display: flex;
    gap: 4px;
    margin: 10px 0;
  }

  .roles button {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    padding: 5px 4px;
    border: none;
    background: var(--plate);
    color: var(--text);
    font: inherit;
    cursor: pointer;
  }

  .roles button.on {
    box-shadow: inset 0 0 0 1px var(--value);
  }

  .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    box-shadow: 0 0 0 1px rgb(255 255 255 / 30%);
  }

  .wheel {
    position: relative;
    width: 220px;
    height: 220px;
    margin: 4px auto 12px;
    border-radius: 50%;
    background:
      radial-gradient(circle closest-side, hsl(0 0% 60%), transparent),
      conic-gradient(
        hsl(0 100% 60%),
        hsl(60 100% 60%),
        hsl(120 100% 60%),
        hsl(180 100% 60%),
        hsl(240 100% 60%),
        hsl(300 100% 60%),
        hsl(360 100% 60%)
      );
    box-shadow:
      0 0 0 2px var(--edge),
      0 0 24px var(--glow);
    cursor: crosshair;
    touch-action: none;
  }

  .wheel:focus-visible {
    outline: 2px solid var(--value);
    outline-offset: 4px;
  }

  .handle {
    position: absolute;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    box-shadow:
      0 0 0 2px #fff,
      0 0 0 3px rgb(0 0 0 / 50%);
    transform: translate(-50%, -50%);
    pointer-events: none;
  }

  .handle.active {
    width: 20px;
    height: 20px;
    box-shadow:
      0 0 0 3px #fff,
      0 0 0 4px rgb(0 0 0 / 60%),
      0 0 12px #fff;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 6px 0;
  }

  .row > span:first-child {
    flex: none;
    width: 92px;
    color: var(--title);
  }

  .row input[type="text"] {
    flex: 1;
    min-width: 0;
    padding: 4px 6px;
    border: 1px solid var(--edge);
    background: var(--well);
    color: var(--text);
    font: inherit;
  }

  .row input[type="range"] {
    flex: 1;
    accent-color: var(--value);
  }

  .preview {
    flex: none;
    width: 22px;
    height: 22px;
    box-shadow: inset 0 0 0 1px rgb(255 255 255 / 30%);
  }

  h3 {
    margin: 14px 0 6px;
    color: var(--title);
    font-size: 0.8em;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .presets {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .presets li {
    display: flex;
    gap: 4px;
    margin-bottom: 4px;
  }

  .preset {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 8px;
    border: none;
    background: var(--plate);
    color: var(--text);
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  .dots {
    display: inline-flex;
    gap: 3px;
  }

  .remove,
  .save button,
  .reset {
    border: none;
    background: var(--plate);
    color: var(--text);
    font: inherit;
    cursor: pointer;
  }

  .remove {
    padding: 0 8px;
  }

  .save button {
    padding: 4px 10px;
  }

  .reset {
    margin-top: 8px;
    padding: 4px 10px;
    color: var(--faint);
  }
</style>
