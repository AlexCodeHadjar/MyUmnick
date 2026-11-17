/**
 * Пакет персонажа для телефона (Этап 24, ADR-0050): кадры поз и фразы — из тех же файлов, что у спутника
 * на ПК, чтобы не дублировать руками. Запуск: `node ui/scripts/export-mobile-pack.ts` из корня репозитория.
 */
import { copyFileSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { PET_RU } from "../src/features/companion/phrases/pet.ru.ts";

const SRC = "ui/public/characters/default";
const OUT = "mobile/android/app/src/main/assets/character";

/** Реплики болванчика без LLM: тык, бросок, встряска, голос и время суток. */
const EXTRA = {
  poke: ["Эй!", "Ай, не тыкай.", "Я тут, я тут.", "Чего?", "Палец убери, щекотно."],
  thrown: ["Аааа!", "Полетели!", "Ух ты, я лечу!", "Мягкой посадки мне…"],
  dizzy: ["Голова кружится…", "Не тряси, я же не коктейль!", "Ой-ой, всё плывёт."],
  wake: ["Слушаю.", "Да-да?", "Я тут. Что записать?"],
  saved: ["Записал.", "Готово, в блокноте.", "Запомнил!"],
  empty: ["Блокнот пуст."],
  idle: ["Скучаю немного.", "Может, что-нибудь записать?", "Хорошо тут, в кармане."],
  morning: ["Доброе утро!", "Утро. Кофе уже был?"],
  night: ["Поздно уже, спать пора.", "Я бы прилёг…"],
  handoff_out: ["Бегу на компьютер!", "Встретимся на большом экране."],
  handoff_in: ["Я тут! Прибежал с компьютера.", "Оп, теперь я в кармане."],
};

mkdirSync(OUT, { recursive: true });
const frames = readdirSync(SRC).filter((name) => name.endsWith(".webp"));
for (const name of frames) copyFileSync(join(SRC, name), join(OUT, name));
writeFileSync(join(OUT, "phrases.json"), JSON.stringify({ pet: PET_RU, ...EXTRA }, null, 1));
writeFileSync(
  join(OUT, "index.json"),
  JSON.stringify(frames.map((name) => name.replace(".webp", ""))),
);
console.log(`кадров: ${frames.length}, фразы: phrases.json → ${OUT}`);
