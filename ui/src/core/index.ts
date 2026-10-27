// Публичный API core: фичи импортируют отсюда, а не из модулей пакета (R-63).
export { CoreClient, type AudioSink, type CoreClientOptions } from "./client";
export { type AudioFrame } from "./frames";
export {
  AppStore,
  type ChatMessage,
  type MessageStatus,
  type Role,
  type TurnPhase,
} from "./store.svelte";
export { type ConnectionState } from "./transport";
