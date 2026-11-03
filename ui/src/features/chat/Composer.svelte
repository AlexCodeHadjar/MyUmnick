<script lang="ts">
  // Поле ввода: Enter — отправить, Shift+Enter — перенос, Esc или «Стоп» — прервать ответ.
  // Отправка во время ответа разрешена: новая реплика сама прерывает текущий ход (ADR-0002).
  import { attachmentFromFile, type Attachment } from "./image";
  import { isSendKey, isStopKey } from "./keys";
  import { captureScreen, wantsCapture } from "./screen";

  const {
    busy,
    onsend,
    onstop,
    ontyping = () => undefined,
  }: {
    busy: boolean;
    onsend: (text: string, attached: Attachment | null) => void;
    onstop: () => void;
    /** Текст поля после каждого изменения (черновик для прогрева LLM, T-05). */
    ontyping?: (text: string) => void;
  } = $props();

  let text = $state("");
  let attached = $state<Attachment | null>(null);
  let attachProblem = $state<string | null>(null);
  // Снимок показывается с предупреждением: на нём может быть то, что показывать не хотели.
  let fromScreen = $state(false);
  const empty = $derived(text.trim() === "" && attached === null);

  function submit(): void {
    if (empty) {
      return;
    }
    if (wantsCapture(text, attached !== null)) {
      void shoot();
      return;
    }
    onsend(text, attached);
    text = "";
    attached = null;
    fromScreen = false;
  }

  /** Реплика остаётся в поле: снимок уйдёт, только когда пользователь его увидит и отправит. */
  async function shoot(): Promise<void> {
    attachProblem = null;
    try {
      const shot = await captureScreen();
      if (shot !== null) {
        attached = shot;
        fromScreen = true;
      }
    } catch {
      attachProblem = "Не получилось снять экран";
    }
  }

  async function attach(file: Blob): Promise<void> {
    attachProblem = null;
    try {
      attached = await attachmentFromFile(file);
      fromScreen = false;
    } catch {
      attachProblem = "Не получилось открыть эту картинку";
    }
  }

  function onfile(event: Event & { currentTarget: HTMLInputElement }): void {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (file !== undefined) {
      void attach(file);
    }
  }

  function onpaste(event: ClipboardEvent): void {
    const file = [...(event.clipboardData?.files ?? [])].find((f) => f.type.startsWith("image/"));
    if (file !== undefined) {
      event.preventDefault();
      void attach(file);
    }
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

{#if attached !== null || attachProblem !== null}
  <div class="attached">
    {#if attached !== null}
      <img src={attached.preview} alt="Прикреплённая картинка" />
      <button
        type="button"
        class="stop"
        onclick={() => {
          attached = null;
          fromScreen = false;
        }}>Убрать</button
      >
      {#if fromScreen}
        <span class="warning" role="status">
          Снимок экрана: проверьте, нет ли на нём личного. На стриме его могут увидеть. Уйдёт только
          по кнопке «Отправить».
        </span>
      {/if}
    {/if}
    {#if attachProblem !== null}
      <span role="alert">{attachProblem}</span>
    {/if}
  </div>
{/if}
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
    {onpaste}
    oninput={() => {
      ontyping(text);
    }}
    rows="2"
    placeholder="Сообщение… (Enter — отправить, Shift+Enter — новая строка)"
    aria-label="Сообщение"></textarea>
  <div class="actions">
    {#if busy}
      <button type="button" class="stop" onclick={onstop} title="Esc">Стоп</button>
    {/if}
    <button type="submit" disabled={empty}>Отправить</button>
    <label class="attach" title="Прикрепить картинку; можно и вставить из буфера">
      Картинка
      <input type="file" accept="image/*" onchange={onfile} />
    </label>
    <button
      type="button"
      class="stop"
      title="Выбрать окно и сделать один снимок"
      onclick={() => void shoot()}>Экран</button
    >
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

  .attached {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px 0;
  }

  .attached img {
    max-height: 64px;
    border-radius: 4px;
  }

  .warning {
    font-size: 0.8em;
    color: #ffc27a;
  }

  .attach {
    padding: 2px 8px;
    font-size: 0.8em;
    text-align: center;
    cursor: pointer;
    opacity: 0.8;
  }

  .attach input {
    display: none;
  }

  .stop {
    background: #3a3a48;
    color: inherit;
  }
</style>
