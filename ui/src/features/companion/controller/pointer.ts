import type { CompanionController } from "./controller";
export function pointerHandlers(
  controller: CompanionController,
  canvasElement: () => HTMLCanvasElement | undefined,
  closeMenu: () => void,
  openMain: () => void,
) {
  /** Отпускания мыши: частые клики — это поглаживание, а не двойной клик «открыть окно». */
  let ups: number[] = [];

  function dblclick(): void {
    const now = performance.now();
    if (ups.filter((t) => now - t < 1500).length > 2) return;
    openMain();
  }

  function down(event: PointerEvent): void {
    const canvas = canvasElement();
    if (event.button !== 0 || canvas === undefined) return;
    closeMenu();
    controller.gestures.down(event.clientX, event.clientY, performance.now());
    try {
      canvas.setPointerCapture(event.pointerId);
    } catch {
      // Указатель уже отпущен (короткий клик) — захват не нужен.
    }
  }

  function move(event: PointerEvent): void {
    controller.gestures.move(event.clientX, event.clientY, performance.now());
  }

  function up(event: PointerEvent): void {
    ups = [...ups.filter((t) => performance.now() - t < 1500), performance.now()];
    const point = {
      x: event.clientX,
      y: event.clientY,
      shift: event.shiftKey,
      ctrl: event.ctrlKey,
    };
    controller.gestures.up(point, performance.now());
  }

  function cancelAim(event: KeyboardEvent): void {
    if (event.key !== "Escape") return;
    closeMenu();
    if (controller.gestures.gesture === "aim") controller.gestures.cancel();
  }

  return { down, move, up, dblclick, cancelAim };
}
