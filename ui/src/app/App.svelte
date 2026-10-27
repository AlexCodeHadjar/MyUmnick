<script lang="ts">
  // Окно: чат слева, сцена справа. Раскладка с разделителем и статус-бар — S-5.4,
  // аватар — Этап 6.
  import type { ConnectionState, CoreClient } from "../core";
  import { Chat } from "../features/chat";

  const { client }: { client: CoreClient } = $props();

  const CONNECTION_TEXT: Record<ConnectionState, string> = {
    connecting: "подключение…",
    open: "на связи",
    closed: "нет связи — переподключаюсь",
    replaced: "открыто другое окно",
  };
</script>

<main class="layout">
  <div class="chat-pane">
    <Chat {client} />
  </div>
  <section class="stage" aria-label="Сцена">
    <p class="placeholder">Здесь будет модель (Этап 6)</p>
    <p class="placeholder" data-testid="connection">
      Ядро: {CONNECTION_TEXT[client.store.connection]}
    </p>
  </section>
</main>

<style>
  :global(html),
  :global(body) {
    margin: 0;
    height: 100%;
    font-family: system-ui, sans-serif;
    background: #15151c;
    color: #e8e8f0;
  }

  .layout {
    display: grid;
    grid-template-columns: minmax(320px, 2fr) 3fr;
    height: 100vh;
  }

  .chat-pane {
    min-height: 0;
    border-right: 1px solid #2c2c38;
  }

  .stage {
    display: grid;
    place-content: center;
    text-align: center;
  }

  .placeholder {
    opacity: 0.6;
  }
</style>
