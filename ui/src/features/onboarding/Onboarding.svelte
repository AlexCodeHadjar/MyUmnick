<script lang="ts">
  // Мастер первого запуска (S-13.2): что подходит этой машине, согласие на загрузку, ход загрузки,
  // выбор аватара. Без явного согласия ядру не уходит ни одной команды на скачивание.
  import { onMount, untrack } from "svelte";

  import type { CoreClient } from "../../core";
  import { chooseAvatar } from "./avatar";
  import {
    canInstall,
    downloadSize,
    formatSize,
    initialSelection,
    loadAvatars,
    percent,
    toggled,
  } from "./plan";
  import { restartApp } from "./restart";

  const {
    client,
    storage,
    fallbackAvatar,
    onclose,
  }: {
    client: CoreClient;
    storage: Storage | undefined;
    fallbackAvatar: string;
    onclose: () => void;
  } = $props();

  const store = $derived(client.store);
  const setup = $derived(store.setup);

  let selection = $state(new Set<string>());
  let voice = $state("");
  let agreed = $state(false);
  let installing = $state(false);
  let avatars = $state<string[]>([]);
  let avatar = $state("");
  let restartByHand = $state(false);

  const result = $derived(store.setupResult);
  const size = $derived(setup === null ? 0 : downloadSize(setup.items, selection));
  const finished = $derived(result !== null && result.problem === null);

  $effect(() => {
    if (setup !== null) {
      const data = setup;
      untrack(() => {
        selection = initialSelection(data);
        voice = data.voice;
      });
    }
  });

  $effect(() => {
    if (result !== null) {
      untrack(() => {
        installing = false;
      });
    }
  });

  onMount(() => {
    avatar = fallbackAvatar;
    avatars = [fallbackAvatar];
    void loadAvatars(fallbackAvatar).then((names) => {
      avatars = names;
      avatar = names[0] ?? fallbackAvatar;
    });
  });

  function install(): void {
    installing = true;
    client.installSetup([...selection], voice);
  }

  async function finish(): Promise<void> {
    chooseAvatar(storage, avatar);
    restartByHand = !(await restartApp());
  }
</script>

{#if setup !== null}
  <div class="backdrop">
    <section class="wizard" aria-label="Первый запуск">
      <h2>Первый запуск</h2>
      <p>
        {#if setup.gpu_total_mb === null}
          Видеокарта NVIDIA не найдена.
        {:else}
          Видеопамять: {setup.gpu_total_mb} МБ.
        {/if}
        Приложению нужны модели: они работают на этом компьютере.
      </p>
      {#each setup.warnings as warning (warning)}
        <p class="warn">{warning}</p>
      {/each}

      {#if finished}
        <label>
          Аватар
          <select bind:value={avatar}>
            {#each avatars as name (name)}
              <option value={name}>{name}</option>
            {/each}
          </select>
        </label>
        <p>Всё установлено. Приложение перезапустится и загрузит модели.</p>
        <button type="button" class="primary" onclick={() => void finish()}>Завершить</button>
        {#if restartByHand}
          <p class="warn">Перезапустите приложение вручную.</p>
        {/if}
      {:else}
        <ul>
          {#each setup.items as item (item.id)}
            <li>
              <label>
                <input
                  type="checkbox"
                  checked={selection.has(item.id)}
                  disabled={item.required || installing}
                  onchange={() => {
                    selection = toggled(selection, item);
                  }}
                />
                {item.title}
              </label>
              <span class="meta">
                {item.installed ? "уже установлено" : formatSize(item.size)} · {item.license}
              </span>
            </li>
          {/each}
        </ul>
        <label>
          Голос
          <select bind:value={voice} disabled={installing}>
            {#each setup.voices as name (name)}
              <option value={name}>{name}</option>
            {/each}
          </select>
        </label>
        <label class="consent">
          <input type="checkbox" bind:checked={agreed} disabled={installing} />
          Согласен скачать {formatSize(size)} из интернета и принимаю лицензии выше
        </label>

        {#if result?.problem}
          <p class="warn">{result.problem}</p>
        {/if}
        {#if installing && store.setupProgress !== null}
          <progress max="100" value={percent(store.setupProgress.done, store.setupProgress.total)}
          ></progress>
          <p class="meta">
            {formatSize(store.setupProgress.done)} из {formatSize(store.setupProgress.total)}
          </p>
        {/if}

        <div class="actions">
          {#if installing}
            <button
              type="button"
              onclick={() => {
                client.cancelSetup();
                installing = false;
              }}>Прервать</button
            >
          {:else}
            <button type="button" onclick={onclose}>Позже</button>
            <button
              type="button"
              class="primary"
              disabled={!canInstall(setup, selection, agreed)}
              onclick={install}>Скачать и установить</button
            >
          {/if}
        </div>
      {/if}
    </section>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgb(0 0 0 / 60%);
  }

  .wizard {
    width: min(560px, calc(100% - 32px));
    max-height: calc(100% - 32px);
    overflow: auto;
    padding: 16px 20px;
    border: 1px solid #2c2c38;
    border-radius: 10px;
    background: #15151c;
  }

  h2 {
    margin: 0 0 8px;
  }

  ul {
    margin: 8px 0;
    padding: 0;
    list-style: none;
  }

  li {
    padding: 6px 0;
  }

  .meta {
    display: block;
    margin-left: 24px;
    font-size: 0.85em;
    opacity: 0.65;
  }

  .warn {
    color: #ffc27a;
  }

  .consent {
    display: block;
    margin: 12px 0;
  }

  progress {
    width: 100%;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  button {
    padding: 6px 12px;
    border: 1px solid #3a3a48;
    border-radius: 6px;
    background: #22222c;
    color: inherit;
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.45;
    cursor: default;
  }

  .primary {
    background: #2f5fb5;
  }
</style>
