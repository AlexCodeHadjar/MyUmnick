/** Окно Tauri за портом режима. API грузится при первом входе: обычному окну он не нужен. */
import { isTauri } from "@tauri-apps/api/core";

import { OVERLAY_SIZE, type Point, type WindowPort } from "./mode";

/** Размеры обычного окна из tauri.conf.json: при запуске сразу поверх стола прошлых размеров нет. */
const NORMAL = { width: 1280, height: 760, minWidth: 800, minHeight: 500 } as const;

export function tauriWindow(): WindowPort | null {
  return isTauri() ? new TauriWindow() : null;
}

class TauriWindow implements WindowPort {
  async #api(): Promise<typeof import("@tauri-apps/api/window")> {
    return import("@tauri-apps/api/window");
  }

  async enterOverlay(pinned: boolean): Promise<void> {
    const api = await this.#api();
    const current = api.getCurrentWindow();
    await current.setDecorations(false);
    await current.setShadow(false);
    await current.setMinSize(null);
    await current.setSize(new api.LogicalSize(OVERLAY_SIZE.width, OVERLAY_SIZE.height));
    await current.setAlwaysOnTop(pinned);
  }

  async leaveOverlay(): Promise<void> {
    const api = await this.#api();
    const current = api.getCurrentWindow();
    await current.setIgnoreCursorEvents(false);
    await current.setAlwaysOnTop(false);
    await current.setDecorations(true);
    await current.setShadow(true);
    await current.setMinSize(new api.LogicalSize(NORMAL.minWidth, NORMAL.minHeight));
    await current.setSize(new api.LogicalSize(NORMAL.width, NORMAL.height));
  }

  async setPinned(pinned: boolean): Promise<void> {
    const api = await this.#api();
    await api.getCurrentWindow().setAlwaysOnTop(pinned);
  }

  async passClicks(pass: boolean): Promise<void> {
    const api = await this.#api();
    await api.getCurrentWindow().setIgnoreCursorEvents(pass);
  }

  async startDrag(): Promise<void> {
    const api = await this.#api();
    await api.getCurrentWindow().startDragging();
  }

  async cursor(): Promise<Point> {
    const api = await this.#api();
    const current = api.getCurrentWindow();
    const [cursor, origin, scale] = await Promise.all([
      api.cursorPosition(),
      current.innerPosition(),
      current.scaleFactor(),
    ]);
    return { x: (cursor.x - origin.x) / scale, y: (cursor.y - origin.y) / scale };
  }
}
