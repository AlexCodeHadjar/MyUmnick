<script lang="ts">
  import { locale } from "../../core";
  // Пункты «Сопровождения» в меню окошка персонажа (Этап 23): когда спутник на экране и его позы.
  import { clearPoses, savePoses } from "./pack";
  import { loadSettings, saveSettings, type CompanionWhen } from "./settings";

  const { onclose, onnote }: { onclose: () => void; onnote: (text: string) => void } = $props();

  let when = $state<CompanionWhen>(loadSettings(window.localStorage).when);
  let folder: HTMLInputElement | undefined = $state();

  function choose(next: CompanionWhen): void {
    when = next;
    saveSettings(window.localStorage, { ...loadSettings(window.localStorage), when: next });
    onclose();
  }

  async function take(files: FileList | null): Promise<void> {
    const saved = await savePoses(files === null ? [] : [...files]);
    onnote(locale.t.companion.posesSaved(saved));
  }
</script>

<input
  bind:this={folder}
  type="file"
  accept="image/png,image/webp"
  multiple
  webkitdirectory
  hidden
  onchange={(event) => {
    void take(event.currentTarget.files);
    event.currentTarget.value = "";
  }}
/>
<p class="label">{locale.t.companion.title}</p>
{#each [["off", locale.t.companion.off], ["minimized", locale.t.companion.minimized], ["always", locale.t.companion.always]] as const as [value, label] (value)}
  <button
    type="button"
    role="menuitemradio"
    aria-checked={when === value}
    onclick={() => {
      choose(value);
    }}>{when === value ? "● " : "○ "}{label}</button
  >
{/each}
<button
  type="button"
  role="menuitem"
  onclick={() => {
    onclose();
    folder?.click();
  }}>{locale.t.companion.poses}</button
>
<button
  type="button"
  role="menuitem"
  onclick={() => {
    onclose();
    void clearPoses();
  }}>{locale.t.companion.clearPoses}</button
>

<style>
  .label {
    margin: 2px 10px;
    color: var(--title);
    font-size: 0.8em;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
</style>
