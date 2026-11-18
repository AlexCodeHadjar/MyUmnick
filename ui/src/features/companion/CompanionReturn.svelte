<script lang="ts">
  import { locale } from "../../core";
  // Спутника спрятали («Спрятать» в его меню) — в окошке персонажа значок, чтобы вернуть его одним
  // щелчком (просьба пользователя 2026-11-18). Настройку пишет слой спутника: следим за `storage`.
  import { onMount } from "svelte";

  import { COMPANION_KEY, loadSettings, saveSettings } from "./settings";

  let hidden = $state(loadSettings(window.localStorage).when === "off");

  onMount(() => {
    const onStorage = (event: StorageEvent): void => {
      if (event.key === COMPANION_KEY) hidden = loadSettings(window.localStorage).when === "off";
    };
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("storage", onStorage);
    };
  });

  /** «Всегда»: при «когда окно свёрнуто» он бы не вышел, пока главное окно открыто. */
  function bringBack(): void {
    saveSettings(window.localStorage, { ...loadSettings(window.localStorage), when: "always" });
    hidden = false;
  }
</script>

{#if hidden}
  <button
    type="button"
    class="badge"
    title={locale.t.companion.bringBack}
    aria-label={locale.t.companion.bringBack}
    onclick={bringBack}>👻</button
  >
{/if}
