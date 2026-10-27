<script lang="ts">
  // Панель чата: история, индикатор «печатает», ошибка ядра, поле ввода. Состояние — только из
  // store, действия — через CoreClient (R-63); своей логики диалога здесь нет.
  import type { CoreClient } from "../../core";
  import Composer from "./Composer.svelte";
  import MessageList from "./MessageList.svelte";

  const { client }: { client: CoreClient } = $props();
  const store = $derived(client.store);
</script>

<section class="chat" aria-label="Чат">
  <MessageList messages={store.messages} />
  <div class="status" aria-live="polite">
    {#if store.phase === "thinking"}
      <span class="typing">печатает<span class="dots" aria-hidden="true">…</span></span>
    {:else if store.error !== null}
      <span class="error" role="alert">{store.error.message}</span>
    {/if}
  </div>
  <Composer
    busy={store.phase !== "idle"}
    onsend={(text: string) => {
      client.say(text);
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
    min-height: 1.4em;
    padding: 0 16px;
    font-size: 0.9em;
    opacity: 0.8;
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
