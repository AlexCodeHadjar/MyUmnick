<script lang="ts">
  // Панель чата: история, индикатор «печатает», ошибка ядра, поле ввода, режим субтитров.
  // Состояние — только из store, действия — через CoreClient (R-63); своей логики диалога нет.
  import type { ChatMessage, CoreClient } from "../../core";
  import Composer from "./Composer.svelte";
  import MessageList from "./MessageList.svelte";
  import { readSubtitles, Subtitles, writeSubtitles, type SettingStorage } from "./subtitles";
  import { TypingDebouncer } from "./typing";

  const { client, storage }: { client: CoreClient; storage?: SettingStorage | undefined } =
    $props();
  const store = $derived(client.store);
  const speaking = $derived(store.voice.speech?.speaking ?? false);

  // Черновик — ядру после паузы в наборе (T-05); отправка реплики снимает ожидающий.
  const typing = new TypingDebouncer((text) => {
    client.typing(text);
  });

  // Не реактивен: держит показанную длину субтитров между кадрами.
  const subtitler = new Subtitles();
  // Читается один раз при создании: дальше режим живёт в компоненте, хранилище только пишется.
  // svelte-ignore state_referenced_locally
  let subtitles = $state(readSubtitles(storage));
  const subtitleView = $derived({
    enabled: subtitles && store.backends.tts === "ready",
    speech: store.voice.speech,
  });

  function toggleSubtitles(): void {
    subtitles = !subtitles;
    writeSubtitles(storage, subtitles);
  }
</script>

<section class="chat" aria-label="Чат">
  <MessageList
    messages={store.messages}
    textOf={(message: ChatMessage) => subtitler.text(message, subtitleView)}
  />
  <div class="status">
    <span class="state" aria-live="polite">
      {#if store.hypothesis !== ""}
        <span class="hypothesis">слышу: {store.hypothesis}</span>
      {:else if store.phase === "thinking"}
        <span class="typing">печатает<span class="dots" aria-hidden="true">…</span></span>
      {:else if store.error !== null}
        <span class="error" role="alert">{store.error.message}</span>
      {:else if store.notice !== null}
        <span class="notice" role="status">{store.notice}</span>
      {/if}
    </span>
    <button
      type="button"
      class="toggle"
      aria-pressed={subtitles}
      title="Текст ответа появляется вместе с голосом"
      onclick={toggleSubtitles}>Субтитры</button
    >
  </div>
  <!-- «Стоп» нужен и после конца хода: голос звучит дольше, чем идёт ход (синтез быстрее речи). -->
  <Composer
    busy={store.phase !== "idle" || speaking}
    onsend={(text: string) => {
      typing.cancel();
      client.say(text);
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
    border: 1px solid #44445a;
    border-radius: 10px;
    background: transparent;
    color: inherit;
    font: inherit;
    font-size: 0.85em;
    opacity: 0.6;
    cursor: pointer;
  }

  .toggle[aria-pressed="true"] {
    border-color: #a77bc4;
    background: #3a2a44;
    opacity: 1;
  }

  .notice {
    color: #ffc27a;
  }

  .error {
    color: #ff8a8a;
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
