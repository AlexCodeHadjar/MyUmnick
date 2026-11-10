import { describe, expect, it } from "vitest";

import { en } from "./en";
import { isLang, messagesFor } from "./locale.svelte";
import { ru } from "./ru";

const CYRILLIC = /[А-Яа-яЁё]/u;
// Диагностика для разработчика и логи: пользователь её не видит (ru.ts — словарь, screen.ts — русские
// просьбы «посмотри на экран», protocol.gen.ts — генерируется из ядра).
const ALLOWED = new Set([
  "core/i18n/ru.ts",
  "core/protocol.gen.ts",
  "core/frames.ts",
  "core/transport.ts",
  "app/main.ts",
  "features/chat/screen.ts",
  // Имя и подпись плитки — на языке своего издания: язык ещё не выбран.
  "features/edition/editions.ts",
  "features/chat/image.ts",
  "features/avatar/mapping.ts",
  "features/avatar/live2d/core-loader.ts",
  "features/avatar/live2d/settings.ts",
]);

// Исходники как текст через Vite: без node-типов (их в UI нет, ADR-0010).
const FILES = import.meta.glob<string>(
  ["../../**/*.ts", "../../**/*.svelte", "!../../**/*.test.ts"],
  {
    query: "?raw",
    import: "default",
    eager: true,
  },
);

/** Путь от `src/`: glob отдаёт пути относительно этого файла (`./ru.ts`, `../frames.ts`). */
function fromSrc(path: string): string {
  return new URL(path, "file:///src/core/i18n/").pathname.replace(/^\/src\//u, "");
}

/** Строки кода без комментариев и вызовов console.* — то, что может увидеть пользователь. */
function visibleLines(text: string): string[] {
  const noBlocks = text.replace(/\/\*[\s\S]*?\*\//gu, "").replace(/<!--[\s\S]*?-->/gu, "");
  return noBlocks
    .split("\n")
    .map((line) => line.replace(/(^|\s)\/\/.*$/u, ""))
    .filter((line) => CYRILLIC.test(line) && !/console\.(warn|error|log)/u.test(line));
}

function keysOf(value: object, prefix = ""): string[] {
  return Object.entries(value).flatMap(([key, child]: [string, unknown]) =>
    typeof child === "object" && child !== null
      ? keysOf(child, `${prefix}${key}.`)
      : [`${prefix}${key}`],
  );
}

describe("i18n", () => {
  it("UI has no Russian strings outside the dictionary", () => {
    const offenders = Object.entries(FILES)
      .filter(([path]) => !ALLOWED.has(fromSrc(path)))
      .flatMap(([path, text]) =>
        visibleLines(text).map((line) => `${fromSrc(path)}: ${line.trim()}`),
      );

    expect(Object.keys(FILES).length).toBeGreaterThan(50);

    expect(offenders).toEqual([]);
  });

  it("English dictionary has the same keys and no Cyrillic", () => {
    expect(keysOf(en).sort()).toEqual(keysOf(ru).sort());
    expect(JSON.stringify(en)).not.toMatch(CYRILLIC);
  });

  it("formatted messages follow the language", () => {
    expect(messagesFor("en").metrics.note(50)).toBe("Last 50 measurements of each stage.");
    expect(messagesFor("ru").onboarding.gb("6.9")).toBe("6.9 ГБ");
    expect(isLang("en")).toBe(true);
    expect(isLang("de")).toBe(false);
  });
});
