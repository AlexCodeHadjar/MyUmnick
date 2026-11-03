// Автогенерация: `uv run python tools/gen_protocol.py`. Не редактировать.

export const PROTOCOL_VERSION = 1 as const;

/** Ядро → UI: сменить выражение аватара. */
export interface AvatarEmotion {
  v: Version;
  type: "avatar.emotion";
  turn: string;
  data: EmotionData;
}

/** Ядро → UI: компонент упал, поднимается или снова работает (S-17.1). */
export interface BackendNoticeMessage {
  v: Version;
  type: "backend.notice";
  data: NoticeData;
}

/** Состояние бэкенда для статус-бара UI. */
export type BackendState = "loading" | "ready" | "failed";

/** Кто и что написал. */
export interface BlockedData {
  author: string;
  text: string;
}

/** UI → Ядро: запомнить текущее место под именем. */
export interface BranchCheckpoint {
  v: Version;
  type: "branch.checkpoint";
  data: BranchCheckpointData;
}

/** Имя контрольной точки. */
export interface BranchCheckpointData {
  name: string;
}

/** Ветка: её последняя реплика и длина; `active` — текущий путь идёт через неё. */
export interface BranchData {
  leaf: string;
  title: string;
  length: number;
  active: boolean;
}

/** UI → Ядро: вернуться к реплике; следующая реплика начнёт новую ветку. */
export interface BranchGo {
  v: Version;
  type: "branch.go";
  data: BranchGoData;
}

/** К какой реплике вернуться. */
export interface BranchGoData {
  turn: string;
}

/** Реплика активной ветки; у реплик пользователя `turn` — None. */
export interface BranchMessageData {
  role: "user" | "assistant";
  text: string;
  turn: string | null;
}

/** Ядро → UI: состояние диалога после перехода или при подключении. */
export interface BranchState {
  v: Version;
  type: "branch.state";
  data: BranchStateData;
}

/** Активный путь, все ветки и контрольные точки. */
export interface BranchStateData {
  messages: BranchMessageData[];
  branches: BranchData[];
  checkpoints: CheckpointData[];
  problem: string | null;
}

/** Почему ход прерван. */
export type CancelReason = "user_stop" | "new_message" | "barge_in" | "error";

/** Почему ход прерван; `message` — текст ошибки при `reason == "error"`. */
export interface CancelledData {
  reason: CancelReason;
  message: string;
}

/** UI → Ядро: остановить ответ. */
export interface ChatCancel {
  v: Version;
  type: "chat.cancel";
  data: EmptyData;
}

/** Ядро → UI: порция текста ответа. */
export interface ChatDelta {
  v: Version;
  type: "chat.delta";
  turn: string;
  data: DeltaData;
}

/** UI → Ядро: новая реплика; прерывает текущий ход. */
export interface ChatSend {
  v: Version;
  type: "chat.send";
  data: SendData;
}

/** Ядро → UI: инструмент нашёл источники для этого ответа (FR-25). */
export interface ChatSources {
  v: Version;
  type: "chat.sources";
  data: SourcesData;
}

/** Контрольная точка. */
export interface CheckpointData {
  name: string;
  turn: string;
}

/** Бэкенд, о состоянии которого сообщается в UI. */
export type Component = "llm" | "tts" | "stt";

/** Порция текста ответа. */
export interface DeltaData {
  text: string;
}

/** Единственный источник списка эмоций: из него строятся промпт персоны и разбор ответа. */
export type Emotion = "neutral" | "happy" | "sad" | "angry" | "surprised" | "embarrassed" | "thinking";

/** Эмоция аватара; `intensity` 0…1 (затухание — Этап 8). */
export interface EmotionData {
  emotion: Emotion;
  intensity: number;
}

/** Сообщение без полезной нагрузки. */
export type EmptyData = Record<string, never>;

/** `confirm` — пользователь подтвердил: без него очистка не выполняется. */
export interface EraseData {
  confirm: boolean;
}

/** `problem` — None, если всё удалено. */
export interface ErasedData {
  problem: string | null;
}

/** Что пошло не так — UI выбирает реакцию по коду, текст показывает пользователю. */
export type ErrorCode = "bad_message" | "llm_unavailable" | "generation_failed" | "internal";

/** Ошибка для пользователя. */
export interface ErrorData {
  code: ErrorCode;
  message: string;
}

/** Ядро → UI: ошибка; `turn` — None, если не относится к ходу (битое сообщение). */
export interface ErrorMessage {
  v: Version;
  type: "error";
  turn: string | null;
  data: ErrorData;
}

/** Факт с его источником. */
export interface FactData {
  note: string;
  text: string;
  source: string;
  importance: number;
  created: string;
}

/** Какой факт удалить. */
export interface FactDeleteData {
  note: string;
}

/** Новый текст факта. */
export interface FactSaveData {
  note: string;
  text: string;
}

/** Список фактов; `problem` — что не удалось сделать. */
export interface FactsData {
  facts: FactData[];
  problem: string | null;
}

/** Итог установки: `problem` — None, если всё поставлено. */
export interface FinishedData {
  problem: string | null;
}

/** Ядро → UI: пользователь заговорил — оборвать голос витюбера сразу (Этап 11). */
export interface InputBargeIn {
  v: Version;
  type: "input.barge_in";
  data: EmptyData;
}

/** Ядро → UI: распознанная фраза — реплика пользователя в чате; за ней начнётся ход. */
export interface InputFinal {
  v: Version;
  type: "input.final";
  data: DeltaData;
}

/** Ядро → UI: промежуточный текст фразы пользователя. */
export interface InputHypothesis {
  v: Version;
  type: "input.hypothesis";
  data: DeltaData;
}

/** UI → Ядро: черновик реплики (с дебаунсом ~300 мс) — прогрев кэша LLM, T-05. */
export interface InputTyping {
  v: Version;
  type: "input.typing";
  data: TypingData;
}

/** Что выбрал пользователь в мастере. */
export interface InstallData {
  item_ids: string[];
  voice: string;
}

/** Модель под управлением менеджера; `waiting_reason` — почему ждёт. */
export interface ManagedModelData {
  name: string;
  vram_mb: number;
  priority: string;
  state: string;
  users: number;
  waiting_reason: string | null;
}

/** UI → Ядро: удалить всю память. */
export interface MemoryErase {
  v: Version;
  type: "memory.erase";
  data: EraseData;
}

/** Ядро → UI: итог очистки. */
export interface MemoryErased {
  v: Version;
  type: "memory.erased";
  data: ErasedData;
}

/** UI → Ядро: удалить факт. */
export interface MemoryFactDelete {
  v: Version;
  type: "memory.fact_delete";
  data: FactDeleteData;
}

/** UI → Ядро: исправить факт. */
export interface MemoryFactSave {
  v: Version;
  type: "memory.fact_save";
  data: FactSaveData;
}

/** Ядро → UI: факты памяти (S-16.2). */
export interface MemoryFacts {
  v: Version;
  type: "memory.facts";
  data: FactsData;
}

/** UI → Ядро: открыта панель памяти, нужен список. */
export interface MemoryList {
  v: Version;
  type: "memory.list";
  data: EmptyData;
}

/** Ядро → UI: замер стадии; `turn` — None вне хода (прогрев). */
export interface MetricsSpan {
  v: Version;
  type: "metrics.span";
  turn: string | null;
  data: SpanData;
}

/** Текст для пользователя. */
export interface NoticeData {
  text: string;
}

/** Закреплённая модель: основная LLM, распознавание речи. */
export interface PinnedModelData {
  name: string;
  vram_mb: number;
}

/** UI → Ядро: разговор не запоминается (S-17.2). */
export interface PrivacySet {
  v: Version;
  type: "privacy.set";
  data: PrivacySetData;
}

/** Включить или выключить приватный режим. */
export interface PrivacySetData {
  enabled: boolean;
}

/** Ядро → UI: состояние режима; приходит при подключении и после переключения. */
export interface PrivacyState {
  v: Version;
  type: "privacy.state";
  data: PrivacyStateData;
}

/** Режим и можно ли очистить память (она может быть выключена). */
export interface PrivacyStateData {
  enabled: boolean;
  erasable: boolean;
}

/** Сколько байт готово из общего числа и какой файл качается. */
export interface ProgressData {
  done: number;
  total: number;
  file: string;
}

/** Снимок видеопамяти: `limit_mb` учитывает другие программы, `capacity_mb` — только конфиг. */
export interface ResourcesData {
  limit_mb: number;
  capacity_mb: number;
  free_mb: number;
  pinned: PinnedModelData[];
  models: ManagedModelData[];
}

/** Ядро → UI: снимок для панели ресурсов, только пока она открыта (S-12.10). */
export interface ResourcesMessage {
  v: Version;
  type: "resources.snapshot";
  data: ResourcesData;
}

/** UI → Ядро: панель ресурсов открыли или закрыли; закрытая ничего не считает. */
export interface ResourcesWatch {
  v: Version;
  type: "resources.watch";
  data: WatchData;
}

/** Реплика пользователя. */
export interface SendData {
  text: string;
}

/** UI → Ядро: прервать загрузку; скачанное продолжится при следующей попытке. */
export interface SetupCancel {
  v: Version;
  type: "setup.cancel";
  data: EmptyData;
}

/** Состояние мастера: `gpu_total_mb` — None, если карта NVIDIA не найдена. */
export interface SetupData {
  needed: boolean;
  gpu_total_mb: number | null;
  voices: string[];
  voice: string;
  warnings: string[];
  items: SetupItemData[];
}

/** Ядро → UI: установка закончена; после успеха приложение перезапускается. */
export interface SetupFinished {
  v: Version;
  type: "setup.finished";
  data: FinishedData;
}

/** UI → Ядро: согласие на загрузку; без этого сообщения ничего не скачивается (S-13.2). */
export interface SetupInstall {
  v: Version;
  type: "setup.install";
  data: InstallData;
}

/** Компонент в мастере; `license` пользователь видит до согласия. */
export interface SetupItemData {
  id: string;
  title: string;
  license: string;
  size: number;
  required: boolean;
  recommended: boolean;
  installed: boolean;
}

/** Ядро → UI: ход загрузки. */
export interface SetupProgress {
  v: Version;
  type: "setup.progress";
  data: ProgressData;
}

/** Ядро → UI: нужен ли мастер и что он предлагает; приходит при подключении. */
export interface SetupStateMessage {
  v: Version;
  type: "setup.state";
  data: SetupData;
}

/** Откуда взят ответ. */
export interface SourceData {
  title: string;
  url: string;
}

/** Источники текущего ответа. */
export interface SourcesData {
  sources: SourceData[];
}

/** Замер стадии хода для панели метрик (FR-15). */
export interface SpanData {
  name: string;
  ms: number;
}

/** Ядро → UI: состояние бэкенда (вне хода). */
export interface Status {
  v: Version;
  type: "status";
  data: StatusData;
}

/** Состояние бэкенда для статус-бара. */
export interface StatusData {
  component: Component;
  state: BackendState;
}

/** Ядро → UI: ход прерван — UI сбрасывает аудиобуфер. */
export interface TurnCancelledMessage {
  v: Version;
  type: "turn.cancelled";
  turn: string;
  data: CancelledData;
}

/** Ядро → UI: ответ закончен полностью. */
export interface TurnFinishedMessage {
  v: Version;
  type: "turn.finished";
  turn: string;
  data: EmptyData;
}

/** Ядро → UI: ход начат — аватар «думает» (T-17). */
export interface TurnStartedMessage {
  v: Version;
  type: "turn.started";
  turn: string;
  data: EmptyData;
}

/** Черновик реплики, пока пользователь печатает; пустой — поле очищено. */
export interface TypingData {
  text: string;
}

export type Version = 1;

/** Ядро → UI: реплика зрителя заблокирована как атака; ведущий решает, что делать (FR-31). */
export interface ViewerBlockedMessage {
  v: Version;
  type: "viewer.blocked";
  data: BlockedData;
}

/** Видно ли окно. */
export interface VisibilityData {
  visible: boolean;
}

/** Открыта ли панель ресурсов. */
export interface WatchData {
  enabled: boolean;
}

/** UI → Ядро: окно свернули или вернули; свёрнутому персонаж сам не заговорит (S-15.1). */
export interface WindowVisibility {
  v: Version;
  type: "window.visibility";
  data: VisibilityData;
}

export type InboundMessage = ChatSend | ChatCancel | InputTyping | ResourcesWatch | SetupInstall | SetupCancel | PrivacySet | MemoryErase | MemoryList | MemoryFactSave | MemoryFactDelete | BranchGo | BranchCheckpoint | WindowVisibility;

export type OutboundMessage = TurnStartedMessage | ChatDelta | AvatarEmotion | TurnFinishedMessage | TurnCancelledMessage | MetricsSpan | Status | InputBargeIn | InputHypothesis | InputFinal | ResourcesMessage | SetupStateMessage | SetupProgress | SetupFinished | ViewerBlockedMessage | BackendNoticeMessage | PrivacyState | MemoryErased | MemoryFacts | BranchState | ChatSources | ErrorMessage;
