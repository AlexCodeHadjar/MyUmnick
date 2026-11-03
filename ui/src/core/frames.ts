/**
 * Разбор входящих кадров ядра — граница транспорта (R-62): всё, что пришло по сокету,
 * проверяется здесь один раз, дальше код работает с типами из protocol.gen.ts (R-64).
 */
import { PROTOCOL_VERSION, type OutboundMessage } from "./protocol.gen";

/** Тип бинарного кадра «звук» — `AUDIO_FRAME_TYPE` в `gateway/codec.py`. */
const AUDIO_FRAME_TYPE = 0x01;

/** Заголовок аудиокадра `<BBHIQ`: тип, версия, seq, sample_rate, turn_id — docs/protocol.md. */
export const AUDIO_HEADER_SIZE = 16;

/** Тип бинарного кадра «микрофон» — `MIC_FRAME_TYPE` в `gateway/codec.py`. */
const MIC_FRAME_TYPE = 0x02;
/** Заголовок кадра микрофона `<BBHI`: тип, версия, seq, sample_rate. */
export const MIC_HEADER_SIZE = 8;
const SEQ_MODULO = 65536;

/** Кадр микрофона для ядра: заголовок + PCM s16le моно. */
export function encodeMicFrame(seq: number, sampleRate: number, pcm: Int16Array): ArrayBuffer {
  const frame = new ArrayBuffer(MIC_HEADER_SIZE + pcm.byteLength);
  const view = new DataView(frame);
  view.setUint8(0, MIC_FRAME_TYPE);
  view.setUint8(1, PROTOCOL_VERSION);
  view.setUint16(2, seq % SEQ_MODULO, true);
  view.setUint32(4, sampleRate, true);
  pcm.forEach((sample, index) => {
    view.setInt16(MIC_HEADER_SIZE + index * 2, sample, true);
  });
  return frame;
}

/** Ширина номера хода в JSON: `turn_ref` в `gateway/protocol.py` (`t-000042`). */
const TURN_DIGITS = 6;

/** Аудиокадр ядра. `turn` — в том же виде, что в JSON-сообщениях, чтобы их сопоставлять. */
export interface AudioFrame {
  seq: number;
  sampleRate: number;
  turn: string;
  pcm: Int16Array;
}

/** Кадр не соответствует протоколу: ядро другой версии или повреждённые данные. */
export class FrameError extends Error {
  override name = "FrameError";
}

/**
 * Список типов сообщений ядра. `satisfies` сверяет его с объединением `OutboundMessage`:
 * новый тип в протоколе без строки здесь — ошибка компиляции, а не тихий отброс.
 */
const OUTBOUND_TYPES = {
  "turn.started": true,
  "chat.delta": true,
  "avatar.emotion": true,
  "avatar.gesture": true,
  "turn.finished": true,
  "turn.cancelled": true,
  "metrics.span": true,
  status: true,
  "input.barge_in": true,
  "input.hypothesis": true,
  "input.final": true,
  "resources.snapshot": true,
  "setup.state": true,
  "setup.progress": true,
  "setup.finished": true,
  "viewer.blocked": true,
  "backend.notice": true,
  "privacy.state": true,
  "memory.erased": true,
  "memory.facts": true,
  "branch.state": true,
  "chat.sources": true,
  "chat.attachment": true,
  error: true,
} satisfies Record<OutboundMessage["type"], true>;

/** Номер хода из аудиокадра в виде JSON-сообщений. */
export function turnRef(turnId: bigint): string {
  return `t-${turnId.toString().padStart(TURN_DIGITS, "0")}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Проверяет конверт, а не каждое поле `data`: ядро сериализует те же pydantic-модели, из
 * которых сгенерированы типы, — поля внутри согласованы по построению. Конверт ловит главное:
 * чужую версию протокола и неизвестный тип.
 */
function isOutboundMessage(value: unknown): value is OutboundMessage {
  if (!isRecord(value) || value.v !== PROTOCOL_VERSION || !isRecord(value.data)) {
    return false;
  }
  const type = value.type;
  const turn = value.turn;
  const turnOk = turn === undefined || turn === null || typeof turn === "string";
  return typeof type === "string" && Object.hasOwn(OUTBOUND_TYPES, type) && turnOk;
}

/** Текстовый кадр → сообщение ядра; `FrameError`, если это не сообщение протокола. */
export function parseMessage(raw: string): OutboundMessage {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch (error) {
    throw new FrameError("Кадр ядра — не JSON", { cause: error });
  }
  if (!isOutboundMessage(value)) {
    throw new FrameError(`Неизвестное сообщение ядра: ${raw.slice(0, 120)}`);
  }
  return value;
}

/**
 * Бинарный кадр → аудиокадр. PCM не копируется: `Int16Array` смотрит в тот же буфер
 * (s16le совпадает с порядком байт x86/ARM; смещение 16 выровнено под int16).
 */
export function decodeAudioFrame(buffer: ArrayBuffer): AudioFrame {
  if (buffer.byteLength < AUDIO_HEADER_SIZE) {
    throw new FrameError(`Аудиокадр короче заголовка: ${String(buffer.byteLength)} байт`);
  }
  const view = new DataView(buffer);
  const kind = view.getUint8(0);
  const version = view.getUint8(1);
  if (kind !== AUDIO_FRAME_TYPE || version !== PROTOCOL_VERSION) {
    throw new FrameError(`Чужой бинарный кадр: тип ${String(kind)}, версия ${String(version)}`);
  }
  const pcmBytes = buffer.byteLength - AUDIO_HEADER_SIZE;
  if (pcmBytes % Int16Array.BYTES_PER_ELEMENT !== 0) {
    throw new FrameError(`PCM s16 с нечётным числом байт: ${String(pcmBytes)}`);
  }
  return {
    seq: view.getUint16(2, true),
    sampleRate: view.getUint32(4, true),
    turn: turnRef(view.getBigUint64(8, true)),
    pcm: new Int16Array(buffer, AUDIO_HEADER_SIZE, pcmBytes / Int16Array.BYTES_PER_ELEMENT),
  };
}
