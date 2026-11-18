<script lang="ts">
  // Подсказки команд над полем ввода: что можно написать после «/». Щелчок или Enter — выполнить.
  import type { Command } from "./commands";

  const {
    hints,
    active,
    onpick,
  }: { hints: readonly Command[]; active: number; onpick: (command: Command) => void } = $props();
</script>

<ul class="hints" role="listbox">
  {#each hints as hint, index (hint.id)}
    <li role="option" aria-selected={index === active}>
      <button
        type="button"
        class:active={index === active}
        onmousedown={(event) => {
          // Не забирать фокус у поля ввода.
          event.preventDefault();
        }}
        onclick={() => {
          onpick(hint);
        }}
      >
        <span class="name">/{hint.name}</span>
        <span class="hint">{hint.hint}</span>
      </button>
    </li>
  {/each}
</ul>

<style>
  .hints {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin: 0 16px;
    padding: 4px;
    list-style: none;
    border: 1px solid var(--rule-dim);
    border-radius: 8px;
    background: var(--panel);
  }

  button {
    display: flex;
    gap: 10px;
    align-items: baseline;
    width: 100%;
    padding: 5px 8px;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  button:hover,
  button.active {
    background: var(--plate);
  }

  .name {
    font-weight: 600;
    color: var(--title);
  }

  .hint {
    font-size: 0.85em;
    opacity: 0.7;
  }
</style>
