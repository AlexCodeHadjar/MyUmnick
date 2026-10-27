/** Геометрия сцены: вписать модель в панель и перевести курсор в направление взгляда. */

export interface Size {
  width: number;
  height: number;
}

export interface Placement {
  scale: number;
  /** Центр модели в координатах сцены, CSS-пиксели. */
  x: number;
  y: number;
}

/** Поля вокруг модели, доля сцены: не упираться в края при наклонах головы и физике волос. */
export const FIT_MARGIN = 0.05;

/** Масштаб «вписать целиком» с полями; модель по центру. Пустая сцена или модель — масштаб 0. */
export function fitModel(model: Size, stage: Size, margin = FIT_MARGIN): Placement {
  const room = 1 - 2 * margin;
  const scale =
    model.width > 0 && model.height > 0
      ? Math.max(
          0,
          Math.min((stage.width * room) / model.width, (stage.height * room) / model.height),
        )
      : 0;
  return { scale, x: stage.width / 2, y: stage.height / 2 };
}

/** Кадр маппинга (масштаб и сдвиг центра в долях сцены) поверх «вписать целиком». */
export function applyFrame(
  placement: Placement,
  stage: Size,
  frame: { zoom: number; offsetX: number; offsetY: number },
): Placement {
  return {
    scale: placement.scale * frame.zoom,
    x: placement.x + frame.offsetX * stage.width,
    y: placement.y + frame.offsetY * stage.height,
  };
}

/**
 * Курсор → взгляд: -1…1 по осям, y вверх (как `AvatarRenderer.lookAt`). За пределами сцены
 * значение обрезается — модель смотрит «в край», а не выворачивает шею.
 */
export function gazeAt(
  pointerX: number,
  pointerY: number,
  stage: Size & { left: number; top: number },
): [number, number] {
  const clamp = (value: number): number => Math.max(-1, Math.min(1, value));
  const halfW = stage.width / 2 || 1;
  const halfH = stage.height / 2 || 1;
  const x = (pointerX - (stage.left + halfW)) / halfW;
  const y = (stage.top + halfH - pointerY) / halfH;
  return [clamp(x), clamp(y)];
}
