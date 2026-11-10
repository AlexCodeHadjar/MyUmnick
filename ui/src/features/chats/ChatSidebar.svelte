<script lang="ts">
  // Чаты слева, как в Claude (Этап 21, ADR-0037): у каждого чата своя память и свой контекст,
  // категории создаёт пользователь. Стрелка справа прячет панель сдвигом к краю окна.
  import { untrack } from "svelte";

  import { locale, type ChatItemData, type CoreClient } from "../../core";
  import {
    chatLabel,
    groupChats,
    readCollapsed,
    writeCollapsed,
    type SettingStorage,
  } from "./groups";

  const { client, storage }: { client: CoreClient; storage: SettingStorage | null } = $props();

  const store = $derived(client.store);
  const chats = $derived(store.chats);
  const groups = $derived(chats === null ? [] : groupChats(chats.chats, chats.categories));

  let collapsed = $state(untrack(() => readCollapsed(storage)));
  let menuFor = $state<string | null>(null);
  let renaming = $state<string | null>(null);
  let deleting = $state<string | null>(null);
  let draft = $state("");
  let addingCategory = $state(false);
  let categoryDraft = $state("");

  /**
   * Фокус в поле, которое только что появилось: атрибут `autofocus` срабатывает лишь при загрузке
   * страницы, и без этого набранное название уходило мимо поля (ошибка S-21.2).
   */
  function focusNow(input: HTMLInputElement): void {
    queueMicrotask(() => {
      input.focus();
      input.select();
    });
  }

  function toggle(): void {
    collapsed = !collapsed;
    writeCollapsed(storage, collapsed);
  }

  function open(chat: ChatItemData): void {
    if (chats?.switching) return;
    menuFor = null;
    client.chatAction({ action: "open", id: chat.id });
  }

  function startRename(chat: ChatItemData): void {
    menuFor = null;
    renaming = chat.id;
    draft = chatLabel(chat, locale.t.chats.untitled);
  }

  function saveRename(id: string): void {
    if (renaming !== id) return; // Enter уже сохранил, следом пришёл blur
    if (draft.trim() !== "") client.chatAction({ action: "rename", id, name: draft });
    renaming = null;
  }

  function addCategory(): void {
    if (categoryDraft.trim() !== "") {
      client.chatAction({ action: "category_create", name: categoryDraft });
    }
    addingCategory = false;
    categoryDraft = "";
  }
</script>

<div class="dock" class:collapsed>
  <aside
    class="sidebar"
    aria-label={locale.t.chats.region}
    aria-hidden={collapsed}
    inert={collapsed}
  >
    <div class="top">
      <button
        type="button"
        class="new"
        disabled={chats === null || chats.switching}
        onclick={() => {
          client.chatAction({ action: "create" });
        }}>＋ {locale.t.chats.newChat}</button
      >
      <button
        type="button"
        class="ghost"
        title={locale.t.chats.newCategory}
        aria-label={locale.t.chats.newCategory}
        onclick={() => (addingCategory = true)}>🗀＋</button
      >
    </div>
    {#if addingCategory}
      <form
        class="inline"
        onsubmit={(event) => {
          event.preventDefault();
          addCategory();
        }}
      >
        <input bind:value={categoryDraft} placeholder={locale.t.chats.categoryName} use:focusNow />
        <button type="submit">{locale.t.chats.save}</button>
        <button type="button" onclick={() => (addingCategory = false)}
          >{locale.t.chats.cancel}</button
        >
      </form>
    {/if}
    {#if chats === null}<p class="warn">{locale.t.chats.offline}</p>{/if}
    {#if chats?.switching}<p class="note">{locale.t.chats.switching}</p>{/if}
    {#if chats?.problem}<p class="warn" role="status">{chats.problem}</p>{/if}

    <nav class="list">
      {#each groups as group (group.category?.id ?? "")}
        {#if group.category !== null}
          {@const category = group.category}
          <div class="category">
            <span>{category.name}</span>
            <button
              type="button"
              class="ghost small"
              title={locale.t.chats.deleteCategory}
              aria-label={locale.t.chats.deleteCategory}
              onclick={() => {
                client.chatAction({ action: "category_delete", id: category.id });
              }}>×</button
            >
          </div>
        {/if}
        {#each group.chats as chat (chat.id)}
          <div class="row" class:active={chat.id === chats?.active}>
            {#if renaming === chat.id}
              <form
                class="inline"
                onsubmit={(event) => {
                  event.preventDefault();
                  saveRename(chat.id);
                }}
              >
                <input
                  bind:value={draft}
                  aria-label={locale.t.chats.rename}
                  use:focusNow
                  onblur={() => {
                    saveRename(chat.id);
                  }}
                />
              </form>
            {:else}
              <button
                type="button"
                class="chat"
                onclick={() => {
                  open(chat);
                }}>{chatLabel(chat, locale.t.chats.untitled)}</button
              >
              <button
                type="button"
                class="ghost small"
                aria-label={locale.t.chats.actions}
                onclick={() => (menuFor = menuFor === chat.id ? null : chat.id)}>⋯</button
              >
            {/if}
          </div>
          {#if menuFor === chat.id}
            <div class="menu">
              <button
                type="button"
                onclick={() => {
                  startRename(chat);
                }}>{locale.t.chats.rename}</button
              >
              <label>
                {locale.t.chats.moveTo}
                <select
                  value={chat.category ?? ""}
                  onchange={(event) => {
                    const value = event.currentTarget.value;
                    client.chatAction({
                      action: "move",
                      id: chat.id,
                      category: value === "" ? null : value,
                    });
                    menuFor = null;
                  }}
                >
                  <option value="">{locale.t.chats.noCategory}</option>
                  {#each chats?.categories ?? [] as option (option.id)}
                    <option value={option.id}>{option.name}</option>
                  {/each}
                </select>
              </label>
              {#if deleting === chat.id}
                <span class="warn">{locale.t.chats.confirmDelete}</span>
                <button
                  type="button"
                  class="danger"
                  onclick={() => {
                    client.chatAction({ action: "delete", id: chat.id });
                    deleting = null;
                    menuFor = null;
                  }}>{locale.t.chats.delete}</button
                >
                <button type="button" onclick={() => (deleting = null)}
                  >{locale.t.chats.cancel}</button
                >
              {:else}
                <button
                  type="button"
                  class="danger"
                  disabled={chat.id === chats?.active}
                  onclick={() => (deleting = chat.id)}>{locale.t.chats.delete}</button
                >
              {/if}
            </div>
          {/if}
        {/each}
      {/each}
    </nav>
  </aside>
  <button
    type="button"
    class="toggle"
    aria-label={collapsed ? locale.t.chats.expand : locale.t.chats.collapse}
    title={collapsed ? locale.t.chats.expand : locale.t.chats.collapse}
    aria-expanded={!collapsed}
    onclick={toggle}><span class="arrow">‹</span></button
  >
</div>

<style>
  .dock {
    --width: 240px;
    position: relative;
    display: flex;
    height: 100%;
    width: calc(var(--width) + 14px);
    transition: width 220ms ease;
    overflow: hidden;
  }
  .dock.collapsed {
    width: 14px;
  }
  .sidebar {
    flex: 0 0 var(--width);
    width: var(--width);
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px 8px;
    box-sizing: border-box;
    background: #15171c;
    border-right: 1px solid #2a2d35;
    color: #d6d9e0;
    transform: translateX(0);
    transition: transform 220ms ease;
  }
  .collapsed .sidebar {
    transform: translateX(-100%);
  }
  .toggle {
    flex: 0 0 14px;
    width: 14px;
    padding: 0;
    border: 0;
    background: #1c1f26;
    color: #9aa3b2;
    cursor: pointer;
  }
  .toggle:hover {
    background: #262a33;
    color: #fff;
  }
  .arrow {
    display: inline-block;
    transition: transform 220ms ease;
  }
  .collapsed .arrow {
    transform: rotate(180deg);
  }
  .top {
    display: flex;
    gap: 6px;
  }
  .new {
    flex: 1;
    padding: 6px 8px;
    border: 1px solid #3a3f4b;
    border-radius: 6px;
    background: #20242c;
    color: inherit;
    text-align: left;
    cursor: pointer;
  }
  .ghost {
    border: 0;
    background: transparent;
    color: #9aa3b2;
    cursor: pointer;
  }
  .small {
    padding: 0 6px;
  }
  .list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .category {
    display: flex;
    justify-content: space-between;
    margin-top: 10px;
    padding: 0 6px;
    font-size: 12px;
    color: #8a93a3;
    text-transform: uppercase;
  }
  .row {
    display: flex;
    align-items: center;
    border-radius: 6px;
  }
  .row:hover,
  .row.active {
    background: #262a33;
  }
  .chat {
    flex: 1;
    min-width: 0;
    padding: 6px 8px;
    border: 0;
    background: transparent;
    color: inherit;
    text-align: left;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
  }
  .menu {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin: 0 0 6px 8px;
    padding: 6px;
    border-radius: 6px;
    background: #1c1f26;
    font-size: 13px;
  }
  .menu button {
    text-align: left;
  }
  .inline {
    display: flex;
    gap: 4px;
  }
  .inline input {
    flex: 1;
    min-width: 0;
  }
  .note {
    margin: 0;
    font-size: 12px;
    color: #8a93a3;
  }
  .warn {
    margin: 0;
    font-size: 12px;
    color: #ffc27a;
  }
  .danger {
    color: #ff8a80;
  }
  @media (prefers-reduced-motion: reduce) {
    .dock,
    .sidebar,
    .arrow {
      transition: none;
    }
  }
</style>
