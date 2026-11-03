<script lang="ts">
  // Редактор памяти (S-16.2): что витюбер запомнил, откуда это и как исправить.
  // Список запрашивается при открытии: закрытая панель заметки не читает.
  import { onMount } from "svelte";

  import type { CoreClient } from "../../core";

  const { client, onclose }: { client: CoreClient; onclose: () => void } = $props();

  const store = $derived(client.store);
  let editing = $state<string | null>(null);
  let draft = $state("");
  let deleting = $state<string | null>(null);

  const SOURCES: Record<string, string> = {
    user: "сказано прямо",
    extracted: "из разговора",
    summary: "из резюме",
  };

  onMount(() => {
    client.listMemory();
  });
</script>

<aside class="memory" aria-label="Память">
  <header>
    <h2>Память</h2>
    <button type="button" onclick={onclose} aria-label="Закрыть память">×</button>
  </header>
  {#if store.memory.problem !== null}
    <p class="warn" role="status">{store.memory.problem}</p>
  {/if}
  {#if store.memory.facts.length === 0}
    <p class="note">Пока ничего не запомнено.</p>
  {/if}
  <ul>
    {#each store.memory.facts as fact (fact.note)}
      <li>
        {#if editing === fact.note}
          <textarea bind:value={draft} rows="2" aria-label="Текст факта"></textarea>
          <button
            type="button"
            disabled={draft.trim() === ""}
            onclick={() => {
              client.saveFact(fact.note, draft);
              editing = null;
            }}>Сохранить</button
          >
          <button
            type="button"
            onclick={() => {
              editing = null;
            }}>Отмена</button
          >
        {:else}
          <p>{fact.text}</p>
          <p class="note">{SOURCES[fact.source] ?? fact.source} · {fact.created.slice(0, 10)}</p>
          {#if deleting === fact.note}
            <span class="warn">Удалить этот факт?</span>
            <button
              type="button"
              onclick={() => {
                client.deleteFact(fact.note);
                deleting = null;
              }}>Удалить</button
            >
            <button
              type="button"
              onclick={() => {
                deleting = null;
              }}>Отмена</button
            >
          {:else}
            <button
              type="button"
              onclick={() => {
                editing = fact.note;
                draft = fact.text;
              }}>Исправить</button
            >
            <button
              type="button"
              onclick={() => {
                deleting = fact.note;
              }}>Удалить</button
            >
          {/if}
        {/if}
      </li>
    {/each}
  </ul>
</aside>

<style>
  .memory {
    position: absolute;
    top: 12px;
    left: 12px;
    width: min(420px, calc(100% - 24px));
    max-height: calc(100% - 24px);
    overflow: auto;
    padding: 10px 14px;
    border: 1px solid #2c2c38;
    border-radius: 10px;
    background: rgb(17 17 23 / 95%);
    font-size: 0.85em;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  h2 {
    margin: 0;
    font-size: 1em;
  }

  ul {
    margin: 8px 0 0;
    padding: 0;
    list-style: none;
  }

  li {
    padding: 6px 0;
    border-top: 1px solid #2c2c38;
  }

  li p {
    margin: 0 0 4px;
  }

  textarea {
    width: 100%;
    box-sizing: border-box;
    color: inherit;
    background: #15151c;
    border: 1px solid #3a3a48;
  }

  button {
    border: 1px solid #3a3a48;
    border-radius: 6px;
    background: #22222c;
    color: inherit;
    cursor: pointer;
  }

  header button {
    border: none;
    background: none;
    font-size: 1.3em;
  }

  .note {
    opacity: 0.6;
  }

  .warn {
    color: #ffc27a;
  }
</style>
