import { describe, expect, it } from "vitest";

import { DEFAULT_MAPPING, parseMapping } from "../mapping";
import { loadMapping, loadSettings, withExpressions, type Fetcher } from "./settings";

/** Ответ сервера: тело, код и тип содержимого. */
function serve(body: unknown, status = 200, type = "application/json"): Fetcher {
  return () =>
    Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
      headers: { get: (name: string) => (name.toLowerCase() === "content-type" ? type : null) },
    });
}

const MODEL3 = {
  Version: 3,
  FileReferences: {
    Moc: "haru.moc3",
    Expressions: [
      { Name: "Smile", File: "old/Smile.exp3.json" },
      { Name: "Wink", File: "Wink.exp3.json" },
    ],
  },
};

describe("withExpressions", () => {
  it("дописывает выражения маппинга поверх одноимённых и ставит url", () => {
    const settings = withExpressions(MODEL3, "/avatars/haru/haru.model3.json", {
      Smile: "e/Smile.exp3.json",
      Sad: "e/Sad.exp3.json",
    });
    expect(settings.url).toBe("/avatars/haru/haru.model3.json");
    expect(settings.FileReferences).toEqual({
      Moc: "haru.moc3",
      Expressions: [
        { Name: "Wink", File: "Wink.exp3.json" },
        { Name: "Smile", File: "e/Smile.exp3.json" },
        { Name: "Sad", File: "e/Sad.exp3.json" },
      ],
    });
    expect(MODEL3.FileReferences.Expressions).toHaveLength(2);
  });

  it("не манифест — ошибка", () => {
    expect(() => withExpressions({ Version: 3 }, "/x", {})).toThrow("FileReferences");
  });
});

describe("loadMapping", () => {
  it("файл есть — разобран", async () => {
    const mapping = await loadMapping("/m", serve({ version: 1, frame: { zoom: 2 } }));
    expect(mapping.frame.zoom).toBe(2);
  });

  it("404 или index.html вместо файла (SPA-резерв Vite) — маппинга нет", async () => {
    expect(await loadMapping("/m", serve(null, 404))).toBe(DEFAULT_MAPPING);
    expect(await loadMapping("/m", serve(null, 200, "text/html"))).toBe(DEFAULT_MAPPING);
  });

  it("битый маппинг и ошибка сервера — ошибка", async () => {
    await expect(loadMapping("/m", serve({ version: 9 }))).rejects.toThrow("version");
    await expect(loadMapping("/m", serve(null, 500))).rejects.toThrow("HTTP 500");
  });
});

describe("loadSettings", () => {
  it("манифест с выражениями маппинга", async () => {
    const mapping = parseMapping({ version: 1, expressions: { Sad: "e/Sad.exp3.json" } });
    const settings = await loadSettings("/a/a.model3.json", mapping, serve(MODEL3));
    expect(settings.url).toBe("/a/a.model3.json");
  });

  it("нет файла модели (index.html вместо него) — понятная ошибка", async () => {
    await expect(
      loadSettings("/a/a.model3.json", DEFAULT_MAPPING, serve(null, 200, "text/html")),
    ).rejects.toThrow("нет файла модели /a/a.model3.json");
  });
});
