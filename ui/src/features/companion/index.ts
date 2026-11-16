// Публичный API «Сопровождения» (Этап 23, ADR-0045; R-63).
export { default as Companion } from "./Companion.svelte";
export { default as CompanionMenu } from "./CompanionMenu.svelte";
export { startFeed } from "./feed";
export {
  loadSettings as loadCompanion,
  saveSettings as saveCompanion,
  type CompanionSettings,
  type CompanionWhen,
} from "./settings";
export { clearPoses, savePoses } from "./pack";
