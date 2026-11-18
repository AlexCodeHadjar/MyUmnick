<script lang="ts">
  import { locale } from "../../core";
  // Поле ввода: Enter — отправить, Shift+Enter — перенос, Esc или «Стоп» — прервать ответ.
  // Отправка во время ответа разрешена: новая реплика сама прерывает текущий ход (ADR-0002).
  import CommandHints from "./CommandHints.svelte";
  import { commandOf, suggest, type Command } from "./commands";
  import { attachmentFromFile, type Attachment } from "./image";
  import { isSendKey, isStopKey } from "./keys";
  import { captureScreen, wantsCapture } from "./screen";

  const {
    busy,
    onsend,
    onstop,
    ontyping = () => undefined,
    commands = [],
    oncommand = () => undefined,
  }: {
    busy: boolean;
    onsend: (text: string, attached: Attachment | null) => void;
    onstop: () => void;
    /** Текст поля после каждого изменения (черновик для прогрева LLM, T-05). */
    ontyping?: (text: string) => void;
    /** Команды после «/» и что делать, когда команду выбрали. */
    commands?: readonly Command[];
    oncommand?: (command: Command) => void;
  } = $props();

  let text = $state("");
  let attached = $state<Attachment | null>(null);
  let attachProblem = $state<string | null>(null);
  // Снимок показывается с предупреждением: на нём может быть то, что показывать не хотели.
  let fromScreen = $state(false);
  const empty = $derived(text.trim() === "" && attached === null);
  const hints = $derived(suggest(text, commands));
  let active = $state(0);

  function run(command: Command): void {
    text = "";
    active = 0;
    oncommand(command);
  }

  function submit(): void {
    if (empty) {
      return;
    }
    const command = commandOf(text, commands);
    if (command !== null) {
      run(command);
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
      attachProblem = locale.t.composer.screenFailed;
    }
  }

  async function attach(file: Blob): Promise<void> {
    attachProblem = null;
    try {
      attached = await attachmentFromFile(file);
      fromScreen = false;
    } catch {
      attachProblem = locale.t.composer.imageFailed;
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

  /** Подсказки открыты: стрелки выбирают, Enter или Tab выполняют выбранную команду. */
  function onhintkey(event: KeyboardEvent): boolean {
    const hint = hints[Math.min(active, hints.length - 1)];
    if (hint === undefined) return false;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      const step = event.key === "ArrowDown" ? 1 : hints.length - 1;
      active = (active + step) % hints.length;
    } else if (event.key === "Tab" || isSendKey(event)) {
      run(hint);
    } else {
      return false;
    }
    event.preventDefault();
    return true;
  }

  function onkeydown(event: KeyboardEvent): void {
    if (onhintkey(event)) return;
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
      <img src={attached.preview} alt={locale.t.composer.attached} />
      <button
        type="button"
        class="stop"
        onclick={() => {
          attached = null;
          fromScreen = false;
        }}>{locale.t.composer.remove}</button
      >
      {#if fromScreen}
        <span class="warning" role="status">
          {locale.t.composer.screenWarning}
        </span>
      {/if}
    {/if}
    {#if attachProblem !== null}
      <span role="alert">{attachProblem}</span>
    {/if}
  </div>
{/if}
{#if hints.length > 0}
  <CommandHints {hints} active={Math.min(active, hints.length - 1)} onpick={run} />
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
      active = 0;
      if (!text.trimStart().startsWith("/")) ontyping(text);
    }}
    rows="2"
    placeholder={locale.t.composer.placeholder}
    aria-label={locale.t.composer.label}></textarea>
  <div class="actions">
    {#if busy}
      <button type="button" class="stop" onclick={onstop} title="Esc"
        >{locale.t.composer.stop}</button
      >
    {/if}
    <button type="submit" disabled={empty}>{locale.t.composer.send}</button>
    <label class="attach" title={locale.t.composer.imageHint}>
      {locale.t.composer.image}
      <input type="file" accept="image/*" onchange={onfile} />
    </label>
    <button
      type="button"
      class="stop"
      title={locale.t.composer.screenHint}
      onclick={() => void shoot()}>{locale.t.composer.screen}</button
    >
  </div>
</form>

<style>
  .composer {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid var(--rule-dim);
  }

  textarea {
    flex: 1;
    resize: none;
    padding: 8px 10px;
    border: 1px solid var(--rule-dim);
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
    color: var(--well);
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
    color: var(--hot);
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
    background: var(--edge);
    color: inherit;
  }
</style>
