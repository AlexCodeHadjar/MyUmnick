<script lang="ts">
  // Поле ввода: Enter — отправить, Shift+Enter — перенос, Esc или «Стоп» — прервать ответ.
  // Отправка во время ответа разрешена: новая реплика сама прерывает текущий ход (ADR-0002).
  import { isSendKey, isStopKey } from "./keys";

  const {
    busy,
    onsend,
    onstop,
  }: { busy: boolean; onsend: (text: string) => void; onstop: () => void } = $props();

  let text = $state("");
  const empty = $derived(text.trim() === "");

  function submit(): void {
    if (empty) {
      return;
    }
    onsend(text);
    text = "";
  }

  function onkeydown(event: KeyboardEvent): void {
    if (isSendKey(event)) {
      event.preventDefault();
      submit();
    } else if (isStopKey(event) && busy) {
      event.preventDefault();
      onstop();
    }
  }
</script>

<form
  class="composer"
  onsubmit={(event) => {
    event.preventDefault();
    submit();
  }}
>
  <textarea
    bind:value={text}
    {onkeydown}
    rows="2"
    placeholder="Сообщение… (Enter — отправить, Shift+Enter — новая строка)"
    aria-label="Сообщение"></textarea>
  <div class="actions">
    {#if busy}
      <button type="button" class="stop" onclick={onstop} title="Esc">Стоп</button>
    {/if}
    <button type="submit" disabled={empty}>Отправить</button>
  </div>
</form>

<style>
  .composer {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid #2c2c38;
  }

  textarea {
    flex: 1;
    resize: none;
    padding: 8px 10px;
    border: 1px solid #2c2c38;
    border-radius: 8px;
    background: #1b1b24;
    color: inherit;
    font: inherit;
  }

  textarea:focus {
    outline: 1px solid #ec70a0;
  }

  .actions {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  button {
    padding: 6px 14px;
    border: none;
    border-radius: 8px;
    background: #ec70a0;
    color: #15151c;
    font: inherit;
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .stop {
    background: #3a3a48;
    color: inherit;
  }
</style>
