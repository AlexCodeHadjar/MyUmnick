<script lang="ts">
  // Каркас окна (S-5.1): чат слева, сцена справа. Раскладка с разделителем — S-5.4,
  // чат — S-5.3, транспорт к ядру — S-5.2, аватар — Этап 6.
  // Блок <script> нужен и пустым: без него svelte-check 4.7 не выдаёт типы модуля (TS7016).
</script>

<main class="layout">
  <section class="chat" aria-label="Чат">
    <p class="placeholder">Чат появится в S-5.3</p>
  </section>
  <section class="stage" aria-label="Сцена">
    <p class="placeholder">Здесь будет модель (Этап 6)</p>
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

  .chat {
    border-right: 1px solid #2c2c38;
  }

  .chat,
  .stage {
    display: grid;
    place-items: center;
  }

  .placeholder {
    opacity: 0.6;
  }
</style>
