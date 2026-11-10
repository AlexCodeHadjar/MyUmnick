// Публичный API экрана выбора издания (Этап 20, R-63).
export { default as EditionBadge } from "./EditionBadge.svelte";
export { default as EditionPicker } from "./EditionPicker.svelte";
export {
  editionById,
  EDITIONS,
  needsPicker,
  type Edition,
  type EditionId,
  type LauncherState,
} from "./editions";
export { launcher, PICK_PARAM, pickRequested, type LauncherPort } from "./launcher";
