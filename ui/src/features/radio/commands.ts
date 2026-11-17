/**
 * Команды радио от спутника (ADR-0049): кнопки таблички над его головой → событие Tauri главному окну,
 * где играет плеер.
 */
import { emitTo, listen, type UnlistenFn } from "@tauri-apps/api/event";

import { isRadioCommand, type RadioCommand } from "./stations";

const EVENT = "radio-command";

/** Главное окно: выполнять команды спутника. */
export function listenRadioCommands(run: (command: RadioCommand) => void): Promise<UnlistenFn> {
  return listen<unknown>(EVENT, (event) => {
    if (isRadioCommand(event.payload)) run(event.payload);
  });
}

/** Спутник: отправить команду главному окну. */
export function sendRadioCommand(command: RadioCommand): void {
  void emitTo("main", EVENT, command).catch(() => undefined);
}
