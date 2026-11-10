// Публичный API core: фичи импортируют отсюда, а не из модулей пакета (R-63).
export { CoreClient, type AudioSink, type CancelSink, type CoreClientOptions } from "./client";
export { type AudioFrame } from "./frames";
export { FIRST_AUDIO_SPAN, FIRST_CHAR_SPAN } from "./probe";
export { int16ToFloat, StreamResampler } from "./resample";
export type {
  BackendState,
  CategoryData,
  ChatActionData,
  ChatItemData,
  ChatsData,
  Component,
  Emotion,
  Gesture,
  ImageData,
  ResourcesData,
  SetupData,
} from "./protocol.gen";
export {
  AppStore,
  SPAN_HISTORY,
  type ChatMessage,
  type MessageStatus,
  type Role,
  type SpeechProgress,
  type TurnPhase,
  type VoiceState,
} from "./store.svelte";
export { type ConnectionState } from "./transport";
export { isLang, locale, messagesFor, type Lang, type Messages } from "./i18n";
