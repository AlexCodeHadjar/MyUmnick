import { describe, expect, it } from "vitest";

import {
  DEFAULT_STATIONS,
  isRadioCommand,
  parseRadio,
  station,
  stationsOf,
  step,
} from "./stations";

describe("радио: станции и настройки", () => {
  it("своя станция — только https и с именем", () => {
    expect(station(" Моя волна ", "https://example.com/live.mp3")).toEqual({
      name: "Моя волна",
      url: "https://example.com/live.mp3",
    });
    expect(station("Волна", "http://example.com/live.mp3")).toBeNull();
    expect(station("", "https://example.com/live.mp3")).toBeNull();
    expect(station("Волна", "не ссылка")).toBeNull();
  });

  it("по кругу вперёд и назад", () => {
    expect(step(0, -1, 7)).toBe(6);
    expect(step(6, 1, 7)).toBe(0);
    expect(step(3, 1, 0)).toBe(0);
  });

  it("битые и чужие настройки — умолчания, свои станции проверяются", () => {
    expect(parseRadio("{oops")).toEqual({ index: 0, volume: 0.6, custom: [] });
    const parsed = parseRadio(
      JSON.stringify({
        index: 7,
        volume: 0.3,
        custom: [{ name: "X", url: "https://x.example/s" }, { name: "Y", url: "ftp://y" }, 5],
      }),
    );
    expect(parsed.custom).toEqual([{ name: "X", url: "https://x.example/s" }]);
    expect(parsed.index).toBe(7);
    expect(stationsOf(parsed)).toHaveLength(DEFAULT_STATIONS.length + 1);
    expect(parseRadio(JSON.stringify({ index: 99, volume: 3 }))).toMatchObject({
      index: 0,
      volume: 0.6,
    });
  });

  it("команды спутника — только известные", () => {
    expect(["toggle", "next", "prev", "off"].every(isRadioCommand)).toBe(true);
    expect(isRadioCommand("rm -rf")).toBe(false);
    expect(DEFAULT_STATIONS.every((one) => one.url.startsWith("https://"))).toBe(true);
  });
});
