// Публичный API фичи персонажа: сцена, контракт рендера и выбор вида (Этап 23).
export type { AvatarReaction, AvatarRenderer, StageSize } from "./AvatarRenderer";
export { default as AvatarStage } from "./AvatarStage.svelte";
export type { MouthSource } from "./session";
export { AVATAR_VIEWS, loadView, saveView, type AvatarView } from "./view";
export { default as CharacterControls } from "./portrait/CharacterControls.svelte";
