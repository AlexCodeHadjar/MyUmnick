<script lang="ts">
  import { locale } from "../../core";
  // Панель «Навыки» (Этап 23, ADR-0043): инструменты помощника, поиск и включатели. Список
  // запрашивается при открытии — ядро заодно находит установленные, но не запущенные плагины.
  import { onMount } from "svelte";
  import { fly } from "svelte/transition";

  import type { CoreClient, SkillData } from "../../core";
  import { grouped, needsConfirm, statsLine } from "./skills";

  const { client, onclose }: { client: CoreClient; onclose: () => void } = $props();

  const store = $derived(client.store);
  let query = $state("");
  let confirming = $state<string | null>(null);
  // Плагин запускается на ходу секунды — пусть будет видно, что включение идёт.
  let starting = $state<string | null>(null);
  const parts = $derived(store.skills === null ? [] : grouped(store.skills.skills, query));

  onMount(() => {
    client.listSkills();
  });

  $effect(() => {
    // Новый список от ядра — запуск закончился (удачно или с причиной в `problem`).
    if (store.skills !== null) {
      starting = null;
    }
  });

  function toggle(skill: SkillData): void {
    const enabling = !skill.enabled;
    if (needsConfirm(skill, enabling)) {
      confirming = skill.id;
      return;
    }
    if (!skill.loaded) starting = skill.id;
    client.setSkill(skill.id, enabling);
  }
</script>

<aside
  class="skills u-frame"
  aria-label={locale.t.skills.title}
  transition:fly={{ x: 360, duration: 180 }}
>
  <header>
    <h2 class="u-section">{locale.t.skills.title}</h2>
    <button type="button" class="close" onclick={onclose} aria-label={locale.t.skills.close}
      >×</button
    >
  </header>
  <input
    type="search"
    placeholder={locale.t.skills.search}
    aria-label={locale.t.skills.search}
    bind:value={query}
  />
  <p class="note">{locale.t.skills.appliesNext}</p>
  {#if store.skills?.problem}
    <p class="warn" role="status">{store.skills.problem}</p>
  {/if}
  {#if store.skills === null}
    <p class="note">{locale.t.skills.loading}</p>
  {:else if parts.length === 0}
    <p class="note">{locale.t.skills.nothing}</p>
  {/if}
  {#each parts as part (part.group)}
    <h3>{locale.t.skills.groups[part.group]}</h3>
    <ul>
      {#each part.skills as skill (skill.id)}
        <li class:off={!skill.enabled}>
          <div class="head">
            <strong>{skill.title}</strong>
            <label class="switch" title={locale.t.skills.toggle(skill.title)}>
              <input
                type="checkbox"
                checked={skill.enabled}
                aria-label={locale.t.skills.toggle(skill.title)}
                onchange={(event) => {
                  // Состояние рисует ядро: до ответа галочка не должна врать.
                  event.currentTarget.checked = skill.enabled;
                  toggle(skill);
                }}
              />
              <span aria-hidden="true"></span>
            </label>
          </div>
          {#if skill.summary}
            <p>{skill.summary}</p>
          {/if}
          {#if skill.examples.length > 0}
            <p class="examples">«{skill.examples.join("», «")}»</p>
          {/if}
          <p class="badges">
            {#if skill.plugin === "core"}<span>{locale.t.skills.core}</span>{/if}
            {#if skill.network}<span title={locale.t.skills.networkHint}
                >🌐 {locale.t.skills.network}</span
              >{/if}
            {#if skill.gpu}<span title={locale.t.skills.gpuHint}>⚡ {locale.t.skills.gpu}</span
              >{/if}
            {#if starting === skill.id}<span>{locale.t.skills.starting}</span>
            {:else if !skill.loaded}<span title={locale.t.skills.idleHint}>⏸</span>{/if}
            <span class="stats">{statsLine(skill, locale.t)}</span>
          </p>
          {#if confirming === skill.id}
            <p class="warn">{locale.t.skills.confirmNetwork}</p>
            <button
              type="button"
              onclick={() => {
                client.setSkill(skill.id, true);
                confirming = null;
              }}>{locale.t.skills.enable}</button
            >
            <button
              type="button"
              onclick={() => {
                confirming = null;
              }}>{locale.t.skills.cancel}</button
            >
          {/if}
        </li>
      {/each}
    </ul>
  {/each}
</aside>

<style>
  .skills {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 5;
    width: min(360px, 100%);
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

  h2 {
    margin: 0;
    font-size: 1.05em;
  }

  h3 {
    margin: 14px 0 4px;
    color: var(--title);
    font-size: 0.8em;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    opacity: 0.6;
  }

  input[type="search"] {
    width: 100%;
    box-sizing: border-box;
    margin-top: 10px;
    padding: 6px 8px;
    border: 1px solid var(--edge);
    border-radius: 6px;
    background: var(--well);
    color: inherit;
    font: inherit;
  }

  ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  li {
    padding: 8px 0;
    border-top: 1px solid var(--rule-dim);
    transition: opacity 0.15s;
  }

  li.off {
    opacity: 0.6;
  }

  li p {
    margin: 4px 0 0;
  }

  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }

  .examples {
    font-style: italic;
    opacity: 0.75;
  }

  .badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    font-size: 0.9em;
    opacity: 0.7;
  }

  .badges span:not(.stats) {
    padding: 0 6px;
    border: 1px solid var(--edge);
    border-radius: 999px;
  }

  .switch {
    position: relative;
    flex: none;
    width: 34px;
    height: 18px;
    cursor: pointer;
  }

  .switch input {
    position: absolute;
    opacity: 0;
    inset: 0;
    margin: 0;
    cursor: pointer;
  }

  .switch span {
    position: absolute;
    inset: 0;
    border-radius: 999px;
    background: var(--edge);
    transition: background 0.15s;
  }

  .switch span::after {
    content: "";
    position: absolute;
    top: 2px;
    left: 2px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--text);
    transition: transform 0.15s;
  }

  .switch input:checked + span {
    background: var(--value);
  }

  .switch input:checked + span::after {
    transform: translateX(16px);
  }

  .switch input:focus-visible + span {
    outline: 2px solid var(--title);
    outline-offset: 2px;
  }

  button {
    margin-top: 4px;
    margin-right: 6px;
    border: 1px solid var(--edge);
    border-radius: 6px;
    background: var(--plate);
    color: inherit;
    cursor: pointer;
  }

  .close {
    margin: 0;
    border: none;
    background: none;
    font-size: 1.3em;
  }

  .note {
    margin: 6px 0 0;
    opacity: 0.6;
  }

  .warn {
    color: var(--hot);
  }
</style>
