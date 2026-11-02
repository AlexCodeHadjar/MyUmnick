import { describe, expect, it } from "vitest";

import { MIC_FRAME_SAMPLES, MicFramer, MIC_SAMPLE_RATE } from "./framer";

describe("MicFramer", () => {
  it("режет поток на кадры ровно по 20 мс, хвост ждёт следующего куска", () => {
    const frames: Int16Array[] = [];
    const framer = new MicFramer(MIC_SAMPLE_RATE, (pcm) => frames.push(pcm));

    framer.push(new Float32Array(MIC_FRAME_SAMPLES + 10));
    expect(frames).toHaveLength(1);
    expect(frames[0]).toHaveLength(MIC_FRAME_SAMPLES);

    framer.push(new Float32Array(MIC_FRAME_SAMPLES - 10));
    expect(frames).toHaveLength(2);
  });

  it("48 кГц → 16 кГц: длительность сохраняется", () => {
    const frames: Int16Array[] = [];
    const framer = new MicFramer(48_000, (pcm) => frames.push(pcm));

    framer.push(new Float32Array(48_000));

    expect(Math.abs(frames.length - 50)).toBeLessThanOrEqual(1);
  });

  it("float → s16 с ограничением шкалы, кадры не делят буфер", () => {
    const frames: Int16Array[] = [];
    const framer = new MicFramer(MIC_SAMPLE_RATE, (pcm) => frames.push(pcm));
    const samples = new Float32Array(MIC_FRAME_SAMPLES * 2).fill(0.5);
    samples[0] = 2;
    samples[1] = -2;

    framer.push(samples);

    expect(frames[0]?.[0]).toBe(32767);
    expect(frames[0]?.[1]).toBe(-32768);
    expect(frames[0]?.[2]).toBe(16384);
    expect(frames[0]).not.toBe(frames[1]);
  });

  it("silence дописывает нули: push-to-talk сразу закрывает фразу", () => {
    const frames: Int16Array[] = [];
    const framer = new MicFramer(MIC_SAMPLE_RATE, (pcm) => frames.push(pcm));

    framer.silence(40);

    expect(frames).toHaveLength(2);
    expect(frames.every((frame) => frame.every((sample) => sample === 0))).toBe(true);
  });
});
