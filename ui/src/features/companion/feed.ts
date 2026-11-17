/**
 * Главное окно → спутник (Этап 23, ADR-0045): громкость речи, эмоция и текст ответа 20 раз в секунду.
 * К ядру подключается только главное окно (шлюз держит одного клиента), поэтому спутник получает это
 * событием Tauri. Сообщения берутся мимо пачки кадров: у скрытого окна кадры не идут.
 */
import { emitTo } from "@tauri-apps/api/event";

import { locale, type CoreClient } from "../../core";
import type { RadioFeed } from "../radio";
import { loadSettings } from "./settings";

const EVERY_MS = 50;
/** Речь «идёт», пока рот открывался за последние 0,6 с: паузы между словами не гасят облачко. */
const SPEAKING_HOLD_MS = 600;

/** Запустить передачу; `mouth(dt)` — громкость голоса 0…1. Возвращает остановку. */
export function startFeed(
  client: CoreClient,
  mouth: (deltaMs: number) => number,
  radio: (time: number) => RadioFeed,
): () => void {
  let emotion = "neutral";
  let text = "";
  let lastVoice = 0;
  client.onMessage((message) => {
    if (message.type === "turn.started") text = "";
    else if (message.type === "chat.delta") text += message.data.text;
    else if (message.type === "avatar.emotion") emotion = message.data.emotion;
  });
  let last = performance.now();
  const timer = setInterval(() => {
    const now = performance.now();
    const level = mouth(now - last);
    last = now;
    if (level > 0.03) lastVoice = now;
    if (loadSettings(window.localStorage).when === "off") return;
    const speaking = now - lastVoice < SPEAKING_HOLD_MS;
    void emitTo("companion", "companion-feed", {
      mouth: level,
      speaking,
      emotion,
      text,
      lang: locale.lang,
      // Радио (ADR-0049): табличка над головой и пение спутника.
      radio: radio(now / 1000),
    }).catch(() => undefined);
  }, EVERY_MS);
  return () => {
    clearInterval(timer);
  };
}
