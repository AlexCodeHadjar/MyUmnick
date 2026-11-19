// Версия в окне (просьба пользователя 2026-11-18: видно, что запущен свежий код): номер из package.json,
// коммит (`*` — есть несохранённые в git правки) и время запуска сборки. JS, а не TS: типов Node в
// проекте нет (новая зависимость — только через ADR).
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";

export function buildStamp() {
  // Путь — от этого файла, а не от текущей папки: Vite запускают и из корня проекта (`vite ui`).
  const version = JSON.parse(
    readFileSync(new URL("./package.json", import.meta.url), "utf8"),
  ).version;
  let commit = "";
  try {
    const hash = execSync("git rev-parse --short HEAD").toString().trim();
    const dirty = execSync("git status --porcelain").toString().trim() !== "";
    commit = ` · ${hash}${dirty ? "*" : ""}`;
  } catch {
    // Нет git (архив исходников) — только номер и время.
  }
  const time = new Date().toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
  return `v${version}${commit} · ${time}`;
}
