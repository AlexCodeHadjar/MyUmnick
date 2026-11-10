<script lang="ts">
  import { locale } from "../../core";
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
    <section class="wizard" aria-label={locale.t.onboarding.title}>
      <h2>{locale.t.onboarding.title}</h2>
      <p>
        {#if setup.gpu_total_mb === null}
          {locale.t.onboarding.noGpu}
        {:else}
          {locale.t.onboarding.vram(setup.gpu_total_mb)}
        {/if}
        {locale.t.onboarding.intro}
      </p>
      {#each setup.warnings as warning (warning)}
        <p class="warn">{warning}</p>
      {/each}

      {#if finished}
        <label>
          {locale.t.onboarding.avatar}
          <select bind:value={avatar}>
            {#each avatars as name (name)}
              <option value={name}>{name}</option>
            {/each}
          </select>
        </label>
        <p>{locale.t.onboarding.done}</p>
        <button type="button" class="primary" onclick={() => void finish()}
          >{locale.t.onboarding.finish}</button
        >
        {#if restartByHand}
          <p class="warn">{locale.t.onboarding.restartManually}</p>
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
                {item.installed ? locale.t.onboarding.installed : formatSize(item.size, locale.t)} · {item.license}
              </span>
            </li>
          {/each}
        </ul>
        <label>
          {locale.t.onboarding.voice}
          <select bind:value={voice} disabled={installing}>
            {#each setup.voices as name (name)}
              <option value={name}>{name}</option>
            {/each}
          </select>
        </label>
        <label class="consent">
          <input type="checkbox" bind:checked={agreed} disabled={installing} />
          {locale.t.onboarding.consent(formatSize(size, locale.t))}
        </label>

        {#if result?.problem}
          <p class="warn">{result.problem}</p>
        {/if}
        {#if installing && store.setupProgress !== null}
          <progress max="100" value={percent(store.setupProgress.done, store.setupProgress.total)}
          ></progress>
          <p class="meta">
            {locale.t.onboarding.progress(
              formatSize(store.setupProgress.done, locale.t),
              formatSize(store.setupProgress.total, locale.t),
            )}
          </p>
        {/if}

        <div class="actions">
          {#if installing}
            <button
              type="button"
              onclick={() => {
                client.cancelSetup();
                installing = false;
              }}>{locale.t.onboarding.abort}</button
            >
          {:else}
            <button type="button" onclick={onclose}>{locale.t.onboarding.later}</button>
            <button
              type="button"
              class="primary"
              disabled={!canInstall(setup, selection, agreed)}
              onclick={install}>{locale.t.onboarding.install}</button
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
