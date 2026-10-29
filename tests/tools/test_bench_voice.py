import asyncio
import io
import json
from pathlib import Path

import pytest

from tests.fakes import FakeTTS
from tools.bench_latency import BenchPrompt
from tools.bench_voice import (
    CHARS_PER_TOKEN,
    PhraseTiming,
    ScriptedLLM,
    TimedTTS,
    VoiceSample,
    main,
    playback_stalls,
    run_voice_bench,
    summarize_voice,
)
from vtuber.application.pipeline import ChunkerConfig, ReplyPipeline, Voice
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams

ROOT = Path(__file__).resolve().parents[2]
SILERO_MODEL = ROOT / "models" / "tts" / "silero" / "v5_6_ru.pt"
PARAMS = GenerationParams(max_tokens=64, temperature=0.7)
CHUNKER = ChunkerConfig(first_min_words=4, next_min_words=10, max_words=25)


def test_continuous_audio_has_no_stalls() -> None:
    # Фрагменты по 100 мс приходят раньше, чем доиграл предыдущий.
    assert playback_stalls([(0.0, 0.1), (50.0, 0.1), (150.0, 0.1)]) == []


def test_late_chunk_is_a_stall_counted_from_end_of_previous_audio() -> None:
    stalls = playback_stalls([(10.0, 0.1), (300.0, 0.2), (480.0, 0.1)])

    assert stalls == [pytest.approx(190.0)]
    assert playback_stalls([]) == []


def test_phrase_rtf_is_synthesis_time_over_audio_duration() -> None:
    assert PhraseTiming(synth_ms=300.0, audio_s=2.0).rtf == pytest.approx(0.15)
    assert PhraseTiming(synth_ms=10.0, audio_s=0.0).rtf == 0.0


async def test_scripted_llm_streams_reply_by_tokens_in_round_robin() -> None:
    llm = ScriptedLLM(ttft_ms=0, tps=10_000, replies=("абвгдеж", "ок"))

    first = [delta async for delta in llm.stream((), PARAMS)]
    second = [delta async for delta in llm.stream((), PARAMS)]

    assert "".join(first) == "абвгдеж"
    assert all(len(delta) <= CHARS_PER_TOKEN for delta in first)
    assert second == ["ок"]


async def test_voice_bench_measures_ttfa_rtf_and_skips_warmup() -> None:
    tts = TimedTTS(FakeTTS(rtf=0.1, chunk_ms=50))
    llm = ScriptedLLM(ttft_ms=20, tps=500)
    pipeline = ReplyPipeline(llm, PARAMS, Telemetry(EventBus()), Voice(tts, CHUNKER))
    prompts = [BenchPrompt(id=name, kind="short", text=name) for name in ("a", "b")]

    samples = await run_voice_bench(pipeline, tts, prompts, runs=1)

    assert [sample.prompt_id for sample in samples] == ["a", "b"]
    for sample in samples:
        assert sample.ttfa_ms is not None
        assert 20 <= sample.ttft_ms <= sample.ttfa_ms
        assert sample.audio_s > 0
    assert len(tts.phrases) >= 2
    # Только снизу: таймер Windows (~15.6 мс) растягивает паузы FakeTTS в разы.
    assert all(phrase.rtf > 0.05 for phrase in tts.phrases)


def test_summary_skips_silent_replies_and_reports_voice_share() -> None:
    samples = [
        VoiceSample("a", ttft_ms=100.0, ttfa_ms=300.0, audio_s=2.0, max_stall_ms=0.0),
        VoiceSample("b", ttft_ms=100.0, ttfa_ms=None, audio_s=0.0, max_stall_ms=0.0),
    ]

    summary = summarize_voice(samples, [PhraseTiming(100.0, 1.0)])

    assert summary["TTFA, мс"].p50 == 300
    assert summary["TTFA - TTFT, мс"].max == 200
    assert summary["RTF фразы"].p50 == pytest.approx(0.1)


def test_cli_requires_a_tts_engine() -> None:
    output = io.StringIO()

    code = main(["--simulate-llm", "--tts", "none"], {}, output)

    assert code == 1
    assert "--tts" in output.getvalue()


@pytest.mark.slow
@pytest.mark.skipif(not SILERO_MODEL.is_file(), reason=f"нет модели Silero {SILERO_MODEL}")
async def test_cli_with_silero_and_simulated_llm(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts.jsonl"
    prompts.write_text('{"id": "p1", "kind": "short", "text": "Привет"}\n', encoding="utf-8")
    report = tmp_path / "voice.json"
    output = io.StringIO()
    argv = ["--prompts", str(prompts), "--tts", "silero", "--simulate-llm", "--out", str(report)]

    code = await asyncio.to_thread(main, argv, {}, output)

    assert code == 0, output.getvalue()
    assert "TTFA" in output.getvalue()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["samples"][0]["ttfa_ms"] > 250
    assert data["summary"]["RTF фразы"]["p50"] < 0.3
