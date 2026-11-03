/**
 * Снимок экрана (S-18.2): только по явному действию, один кадр и сразу конец захвата. Окно выбирает
 * сам пользователь в системном диалоге. Снимок живёт только в памяти (ADR-0025).
 */
import { encodeFrame, type Attachment, type ImageSize } from "./image";

const SCREEN_REQUEST =
  /(?:посмотри|взгляни|глянь)\s+(?:на\s+)?(?:мой\s+|моё\s+|мое\s+|этот\s+|это\s+)?(?:экран|окно)|что\s+(?:у\s+меня\s+)?на\s+экране/iu;

/** Просит ли реплика посмотреть на экран; решает только открыть диалог, снимка без него нет. */
export function asksForScreen(text: string): boolean {
  return SCREEN_REQUEST.test(text);
}

/** Открыть ли диалог вместо отправки: снимок уже есть — значит, пользователь решает его судьбу. */
export function wantsCapture(text: string, hasAttachment: boolean): boolean {
  return !hasAttachment && asksForScreen(text);
}

/** Что нужно от потока: остановить его. */
export interface Stoppable {
  getTracks(): { stop(): void }[];
}

/** Что нужно от захвата: в тестах — подмена. */
export interface ScreenSource<S extends Stoppable, F> {
  /** Системный диалог выбора окна; отказ — исключение. */
  pick(): Promise<S>;
  /** Один кадр потока. */
  frame(stream: S): Promise<{ source: F; size: ImageSize }>;
}

function browserSource(): ScreenSource<MediaStream, CanvasImageSource> {
  return {
    pick: () => navigator.mediaDevices.getDisplayMedia({ video: true, audio: false }),
    frame: async (stream) => {
      const video = document.createElement("video");
      video.muted = true;
      video.srcObject = stream;
      await video.play();
      return { source: video, size: { width: video.videoWidth, height: video.videoHeight } };
    },
  };
}

/**
 * Снимок выбранного окна; null — пользователь передумал. Захват завершается при любом исходе, чтобы
 * системный индикатор записи погас и экран больше никто не видел.
 */
export async function captureFrom<S extends Stoppable, F>(
  source: ScreenSource<S, F>,
  encode: (frame: F, size: ImageSize) => Attachment,
): Promise<Attachment | null> {
  let stream: S;
  try {
    stream = await source.pick();
  } catch {
    return null;
  }
  try {
    const { source: frame, size } = await source.frame(stream);
    return encode(frame, size);
  } finally {
    for (const track of stream.getTracks()) {
      track.stop();
    }
  }
}

export function captureScreen(): Promise<Attachment | null> {
  return captureFrom(browserSource(), encodeFrame);
}
