import { describe, expect, it } from "vitest";

import { PcmQueue } from "./pcm-queue";

const FADE = 4;
const ones = (length: number): Float32Array => new Float32Array(length).fill(1);

function pull(queue: PcmQueue, length: number): { out: number[]; started: string | null } {
  const out = new Float32Array(length);
  const started = queue.pull(out);
  return { out: Array.from(out), started };
}

describe("PcmQueue", () => {
  it("пустая очередь — тишина", () => {
    const queue = new PcmQueue(FADE);
    expect(pull(queue, 3)).toEqual({ out: [0, 0, 0], started: null });
  });

  it("звук после тишины нарастает и сообщает о начале хода один раз", () => {
    const queue = new PcmQueue(FADE);
    queue.push(ones(6), "t-1");
    expect(pull(queue, 6)).toEqual({ out: [0.25, 0.5, 0.75, 1, 1, 1], started: "t-1" });
    queue.push(ones(2), "t-1");
    expect(pull(queue, 2).started).toBeNull();
  });

  it("фрагменты одного хода идут встык, без нового нарастания", () => {
    const queue = new PcmQueue(FADE);
    queue.push(ones(4), "t-1");
    queue.push(ones(2), "t-1");
    expect(pull(queue, 6).out.slice(4)).toEqual([1, 1]);
    expect(queue.buffered).toBe(0);
  });

  it("недобор — хвост тишиной, следующий звук снова с нарастания", () => {
    const queue = new PcmQueue(FADE);
    queue.push(ones(5), "t-1");
    expect(pull(queue, 7).out.slice(4)).toEqual([1, 0, 0]);
    queue.push(ones(2), "t-1");
    expect(pull(queue, 2)).toEqual({ out: [0.25, 0.5], started: "t-1" });
  });

  it("flush — затухание за FADE сэмплов и тишина, очередь пуста", () => {
    const queue = new PcmQueue(FADE);
    queue.push(ones(100), "t-1");
    pull(queue, 10);
    queue.flush();
    expect(queue.buffered).toBe(0);
    expect(pull(queue, 6).out).toEqual([0.75, 0.5, 0.25, 0, 0, 0]);
  });

  it("звук нового хода во время затухания не теряется", () => {
    const queue = new PcmQueue(FADE);
    queue.push(ones(100), "t-1");
    pull(queue, 10);
    queue.flush();
    queue.push(ones(2), "t-2");
    const { out, started } = pull(queue, 6);
    expect(out).toEqual([0.75, 0.5, 0.25, 0, 0.25, 0.5]);
    expect(started).toBe("t-2");
  });

  it("flush пустой очереди ничего не ломает", () => {
    const queue = new PcmQueue(FADE);
    queue.flush();
    queue.push(ones(1), "t-1");
    expect(pull(queue, 1)).toEqual({ out: [0.25], started: "t-1" });
  });
});

describe("PcmQueue: что звучит (S-8.2)", () => {
  it("playing — пока есть звук и пока идёт затухание; progress — сэмплы хода", () => {
    const queue = new PcmQueue(FADE);
    expect(queue.playing).toBe(false);
    expect(queue.progress).toBeNull();
    queue.push(ones(10), "t-1");
    pull(queue, 6);
    expect(queue.playing).toBe(true);
    expect(queue.progress).toEqual({ tag: "t-1", samples: 6 });
    queue.flush();
    pull(queue, 2);
    expect(queue.playing).toBe(true);
    pull(queue, 4);
    expect(queue.playing).toBe(false);
  });

  it("новый ход считается с нуля, пауза счёт хода не сбрасывает", () => {
    const queue = new PcmQueue(FADE);
    queue.push(ones(3), "t-1");
    pull(queue, 5);
    queue.push(ones(2), "t-1");
    pull(queue, 2);
    expect(queue.progress).toEqual({ tag: "t-1", samples: 5 });
    queue.push(ones(4), "t-2");
    pull(queue, 4);
    expect(queue.progress).toEqual({ tag: "t-2", samples: 4 });
  });
});
