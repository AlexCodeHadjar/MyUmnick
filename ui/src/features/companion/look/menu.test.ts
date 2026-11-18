import { describe, expect, it } from "vitest";

import { placeMenu } from "./menu";

const VIEW = { w: 1920, h: 1080 };
const SIZE = { w: 220, h: 300 };

describe("меню спутника у края экрана", () => {
  it("в середине — у курсора", () => {
    expect(placeMenu({ x: 500, y: 400 }, SIZE, VIEW)).toEqual({ x: 500, y: 400 });
  });

  it("у нижнего края — вверх от курсора", () => {
    expect(placeMenu({ x: 500, y: 1000 }, SIZE, VIEW)).toEqual({ x: 500, y: 700 });
  });

  it("у правого края — влево от курсора", () => {
    expect(placeMenu({ x: 1850, y: 400 }, SIZE, VIEW)).toEqual({ x: 1630, y: 400 });
  });

  it("выше экрана не уходит", () => {
    expect(placeMenu({ x: 10, y: 100 }, { w: 220, h: 1200 }, VIEW).y).toBe(8);
  });
});
