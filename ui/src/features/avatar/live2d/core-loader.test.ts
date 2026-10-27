import { describe, expect, it } from "vitest";

import { CORE_MISSING_MESSAGE, loadCubismCore, type ScriptHost } from "./core-loader";

/** Хост, где `<script>` «грузится» по команде теста. */
class FakeHost implements ScriptHost {
  core = false;
  readonly scripts: { url: string; load: () => void; fail: () => void }[] = [];

  hasCore(): boolean {
    return this.core;
  }

  appendScript(url: string, onLoad: () => void, onError: () => void): void {
    this.scripts.push({ url, load: onLoad, fail: onError });
  }
}

describe("loadCubismCore", () => {
  it("Core уже есть — скрипт не добавляется", async () => {
    const host = new FakeHost();
    host.core = true;
    await loadCubismCore(host);
    expect(host.scripts).toEqual([]);
  });

  it("параллельные вызовы ждут один скрипт", async () => {
    const host = new FakeHost();
    const first = loadCubismCore(host, "/core.js");
    const second = loadCubismCore(host, "/core.js");
    expect(host.scripts.map((s) => s.url)).toEqual(["/core.js"]);
    host.core = true;
    host.scripts[0]?.load();
    await Promise.all([first, second]);
  });

  it("нет файла — понятная ошибка, следующая попытка грузит заново", async () => {
    const host = new FakeHost();
    const attempt = loadCubismCore(host);
    host.scripts[0]?.fail();
    await expect(attempt).rejects.toThrow(CORE_MISSING_MESSAGE);

    const retry = loadCubismCore(host);
    expect(host.scripts).toHaveLength(2);
    host.core = true;
    host.scripts[1]?.load();
    await retry;
  });

  it("скрипт загрузился, но Core не появился (вместо файла — HTML) — та же ошибка", async () => {
    const host = new FakeHost();
    const attempt = loadCubismCore(host);
    host.scripts[0]?.load();
    await expect(attempt).rejects.toThrow(CORE_MISSING_MESSAGE);
  });
});
