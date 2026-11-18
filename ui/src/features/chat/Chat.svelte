<script lang="ts">
  import { locale } from "../../core";
  // Панель чата: история, индикатор «печатает», ошибка ядра, поле ввода, команды после «/».
  // Субтитры включаются иконкой в окошке персонажа (просьба пользователя 2026-11-18): здесь только флаг.
  // Состояние — только из store, действия — через CoreClient (R-63); своей логики диалога нет.
  import type { ChatMessage, CoreClient } from "../../core";
  import BranchBar from "./BranchBar.svelte";
  import Composer from "./Composer.svelte";
  import type { Command } from "./commands";
  import type { Attachment } from "./image";
  import MessageList from "./MessageList.svelte";
  import { Subtitles } from "./subtitles";
  import { TypingDebouncer } from "./typing";

  const { client, subtitles }: { client: CoreClient; subtitles: boolean } = $props();
  const store = $derived(client.store);
  const speaking = $derived(store.voice.speech?.speaking ?? false);

  // Черновик — ядру после паузы в наборе (T-05); отправка реплики снимает ожидающий.
  const typing = new TypingDebouncer((text) => {
    client.typing(text);
  });

  // Не реактивен: держит показанную длину субтитров между кадрами.
  const subtitler = new Subtitles();
  const subtitleView = $derived({
    enabled: subtitles && store.backends.tts === "ready",
    speech: store.voice.speech,
  });

  // Приватный режим и очистка памяти — команды (S-17.2): очистка в два шага, она необратима.
  const commands = $derived<Command[]>([
    { id: "private", name: "private", hint: locale.t.privacy.hint },
    { id: "clear", name: "clear", hint: locale.t.privacy.clearHint },
  ]);
  let confirming = $state(false);
  let said = $state<string | null>(null);

  function oncommand(command: Command): void {
    said = null;
    if (command.id === "private") {
      const next = !store.privacy.enabled;
      client.setPrivate(next);
      said = next ? locale.t.privacy.enabled : locale.t.privacy.disabled;
    } else if (store.privacy.erasable) {
      confirming = true;
    } else {
      said = locale.t.privacy.nothing;
    }
  }
</script>

<section class="chat" aria-label={locale.t.chat.region}>
  <BranchBar {client} />
  <MessageList
    messages={store.messages}
    onrewind={(turn: string) => {
      client.goToTurn(turn);
    }}
    textOf={(message: ChatMessage) => subtitler.text(message, subtitleView)}
  />
  {#if store.sources.length > 0}
    <p class="sources">
      {locale.t.chat.sources}
      {#each store.sources as source (source.url)}
        <a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url}</a>
      {/each}
    </p>
  {/if}
  <div class="status">
    <span class="state" aria-live="polite">
      {#if confirming}
        <span class="warn">{locale.t.privacy.confirmErase}</span>
        <button
          type="button"
          class="toggle danger"
          onclick={() => {
            confirming = false;
            client.eraseMemory();
          }}>{locale.t.privacy.erase}</button
        >
        <button
          type="button"
          class="toggle"
          onclick={() => {
            confirming = false;
          }}>{locale.t.privacy.cancel}</button
        >
      {:else if store.hypothesis !== ""}
        <span class="hypothesis">{locale.t.chat.hearing} {store.hypothesis}</span>
      {:else if store.phase === "thinking"}
        <span class="typing"
          >{locale.t.chat.typing}<span class="dots" aria-hidden="true">…</span></span
        >
      {:else if store.error !== null}
        <span class="error" role="alert">{store.error.message}</span>
      {:else if store.notice !== null}
        <span class="notice" role="status">{store.notice}</span>
      {:else if store.privacy.result !== null}
        <span class="notice" role="status">{store.privacy.result}</span>
      {:else if said !== null}
        <span class="notice" role="status">{said}</span>
      {/if}
    </span>
    {#if store.privacy.enabled}
      <span class="private" title={locale.t.privacy.hint}>🔒 {locale.t.privacy.on}</span>
    {/if}
  </div>
  <!-- «Стоп» нужен и после конца хода: голос звучит дольше, чем идёт ход (синтез быстрее речи). -->
  <Composer
    {commands}
    {oncommand}
    busy={store.phase !== "idle" || speaking}
    onsend={(text: string, attached: Attachment | null) => {
      typing.cancel();
      client.say(text, attached ?? undefined);
    }}
    ontyping={(text: string) => {
      typing.input(text);
    }}
    onstop={() => {
      client.stop();
    }}
  />
</section>

<style>
  .chat {
    display: flex;
    flex-direction: column;
    min-height: 0;
    height: 100%;
  }

  .status {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 1.4em;
    padding: 0 16px;
    font-size: 0.9em;
  }

  .state {
    flex: 1;
    opacity: 0.8;
  }

  .toggle {
    padding: 1px 8px;
    border: 1px solid var(--edge);
    border-radius: 10px;
    background: transparent;
    color: inherit;
    font: inherit;
    font-size: 0.85em;
    opacity: 0.6;
    cursor: pointer;
  }

  .danger {
    border-color: var(--danger);
    background: #7a2222;
    opacity: 1;
  }

  .warn {
    color: var(--hot);
  }

  .private {
    font-size: 0.85em;
    font-weight: 600;
    color: var(--danger);
  }

  .sources {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 0;
    padding: 4px 16px;
    font-size: 0.8em;
    opacity: 0.8;
  }

  .sources a {
    color: var(--title);
  }

  .notice {
    color: var(--hot);
  }

  .error {
    color: var(--danger);
  }

  .dots {
    display: inline-block;
    animation: pulse 1.2s ease-in-out infinite;
  }

  @keyframes pulse {
    50% {
      opacity: 0.3;
    }
  }
</style>
