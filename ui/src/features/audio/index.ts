// Публичный API фичи звука: плеер голоса и его подключение к ядру (ADR-0003).
import type { CoreClient } from "../../core";
import { VoicePlayer } from "./VoicePlayer";

export { VoicePlayer };

/**
 * Плеер, подключённый к клиенту ядра: кадры звука → плеер, отмена хода → сброс, начало звука →
 * замер TTFA. Звук не мешает чату: не создался (нет WebAudio) — ошибка наружу, чат работает.
 */
export async function connectVoice(client: CoreClient): Promise<VoicePlayer> {
  const player = await VoicePlayer.create();
  client.onAudio((frame) => {
    player.play(frame);
  });
  client.onCancel((turn) => {
    player.cancel(turn);
  });
  player.onStarted((turn) => {
    client.audioStarted(turn);
  });
  return player;
}
