/**
 * Картинка к реплике (S-18.1): уменьшается в браузере, модели большое не нужно, а кадр по сокету
 * должен быть коротким. Живёт только в памяти: файлов не создаёт (S-18.2).
 */
import type { ImageData as AttachedImage } from "../../core";

/** Больше длинной стороны модели всё равно не увидят: проектор сжимает картинку сам. */
export const MAX_IMAGE_SIDE = 1024;
const JPEG_QUALITY = 0.85;
const JPEG_PREFIX = "data:image/jpeg;base64,";

export interface ImageSize {
  width: number;
  height: number;
}

export interface Attachment {
  image: AttachedImage;
  /** Для показа в чате. */
  preview: string;
}

/** Размер, в который картинка вписывается целиком; меньшая не растягивается. */
export function fitSize(size: ImageSize, maxSide: number = MAX_IMAGE_SIDE): ImageSize {
  const scale = Math.min(1, maxSide / Math.max(size.width, size.height, 1));
  return {
    width: Math.max(1, Math.round(size.width * scale)),
    height: Math.max(1, Math.round(size.height * scale)),
  };
}

/** Кадр (файл или снимок) → JPEG в base64. Ошибка — у вызывающего: показать, что не вышло. */
export function encodeFrame(source: CanvasImageSource, size: ImageSize): Attachment {
  const target = fitSize(size);
  const canvas = document.createElement("canvas");
  canvas.width = target.width;
  canvas.height = target.height;
  const context = canvas.getContext("2d");
  if (context === null) {
    throw new Error("не удалось подготовить картинку");
  }
  context.drawImage(source, 0, 0, target.width, target.height);
  const preview = canvas.toDataURL("image/jpeg", JPEG_QUALITY);
  return {
    image: { mime: "image/jpeg", base64: preview.slice(JPEG_PREFIX.length) },
    preview,
  };
}

export async function attachmentFromFile(file: Blob): Promise<Attachment> {
  const bitmap = await createImageBitmap(file);
  try {
    return encodeFrame(bitmap, { width: bitmap.width, height: bitmap.height });
  } finally {
    bitmap.close();
  }
}
