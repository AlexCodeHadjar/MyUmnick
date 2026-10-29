/** Сообщения процессора плеера в основной поток и их проверка (данные из другого потока). */

export type PlayerEvent =
  | { type: "started"; tag: string }
  | { type: "progress"; tag: string; samples: number }
  | { type: "idle" };

export function isPlayerEvent(data: unknown): data is PlayerEvent {
  if (typeof data !== "object" || data === null || !("type" in data)) {
    return false;
  }
  const tagged = "tag" in data && typeof data.tag === "string";
  switch (data.type) {
    case "idle":
      return true;
    case "started":
      return tagged;
    case "progress":
      return tagged && "samples" in data && typeof data.samples === "number";
    default:
      return false;
  }
}
