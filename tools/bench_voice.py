"""Бенчмарк голоса: TTFA, RTF фраз и паузы между фразами на настоящем конвейере ответа.

Запуск: `uv run python -m tools.bench_voice [--tts silero|piper] [--simulate-llm] [--runs 1]
[--out файл.json]`. LLM — сервер из `[llm]` конфига; `--simulate-llm` — LLM-заглушка с TTFT
`--sim-ttft-ms` и темпом `--sim-tps` для машины без сервера: голосовая часть меряется честно,
TTFT — подставной, поэтому отдельно выводится «TTFA - TTFT» — вклад голоса. TTFA — до первого
звука, отданного ядром; сеть и плеер UI добавляют ≈ 20 мс (S-7.6). Методика — docs/performance.md.
"""

import argparse
import asyncio
import contextlib
import json
import os
import sys
import time
from collections.abc import AsyncGenerator, Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Final, Self, TextIO

from tools.bench_latency import (
    DEFAULT_PROMPTS,
    EXIT_FAILED,
    EXIT_UNAVAILABLE,
    MS_PER_S,
    NS_PER_MS,
    QUANTILES,
    BenchPrompt,
    Stats,
    load_prompts,
    percentile,
    render,
)
from tools.llm_client import ROOT, SYSTEM_PROMPT, open_llm
from vtuber.application.pipeline import ReplyPipeline, StreamParser, Voice
from vtuber.bootstrap import load_app_config, tts_backends
from vtuber.domain import (
    AudioChunk,
    AudioFormat,
    ConfigError,
    Emotion,
    Gesture,
    LLMUnavailable,
    Message,
    Role,
    VtuberError,
)
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams, LLMPort, TTSPort

CHARS_PER_TOKEN: Final = 3
"""Символов на токен у заглушки — как `chars_per_token` бюджета контекста."""
SCRIPTED_REPLIES: Final = (
    "<happy>Привет! Рада тебя видеть, как прошёл твой день?",
    "<thinking>Хм, хороший вопрос. Думаю, кошки всё-таки лучше: они независимые и тёплые.",
    "Ну, раз ты спрашиваешь, расскажу. Вчера я весь вечер учила новые слова и немного пела.",
    "<surprised>Ого, правда? Я и не знала, что ты умеешь играть на гитаре!",
    "<sad>Жаль, что так вышло. Но завтра будет новый день, и всё обязательно наладится.",
)
"""Ответы заглушки: 1–3 предложения, с тегом эмоции — как у модели с персоной (T-07)."""


class ScriptedLLM:
    """LLMPort без сервера: ответы по кругу, первый токен через `ttft_ms`, далее `tps` токенов/с."""

    def __init__(
        self, ttft_ms: float, tps: float, replies: Sequence[str] = SCRIPTED_REPLIES
    ) -> None:
        self._ttft_s = ttft_ms / MS_PER_S
        self._token_s = 1 / tps
        self._replies = replies
        self._count = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Ресурсов нет."""

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        """Ответ кусками по `CHARS_PER_TOKEN` символов; запрос и параметры не важны."""
        del messages, params
        reply = self._replies[self._count % len(self._replies)]
        self._count += 1
        await asyncio.sleep(self._ttft_s)
        for start in range(0, len(reply), CHARS_PER_TOKEN):
            yield reply[start : start + CHARS_PER_TOKEN]
            await asyncio.sleep(self._token_s)

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Кэша нет — прогревать нечего."""
        del messages
        await asyncio.sleep(0)


@dataclass(frozen=True, slots=True)
class PhraseTiming:
    """Синтез одной фразы: время от запроса до последнего фрагмента и длительность звука."""

    synth_ms: float
    audio_s: float

    @property
    def rtf(self) -> float:
        """Real-time factor: доля длительности звука, ушедшая на синтез (цель ≤ 0.3)."""
        return self.synth_ms / MS_PER_S / self.audio_s if self.audio_s > 0 else 0.0


@dataclass(slots=True)
class TimedTTS:
    """TTSPort-обёртка: меряет каждую фразу, не меняя звук."""

    inner: TTSPort
    clock: Callable[[], int] = time.perf_counter_ns
    phrases: list[PhraseTiming] = field(default_factory=list)

    @property
    def audio_format(self) -> AudioFormat:
        """Формат обёрнутого движка."""
        return self.inner.audio_format

    async def synthesize(self, phrase: str) -> AsyncGenerator[AudioChunk]:
        """Звук движка как есть; фраза со звуком попадает в `phrases`."""
        started, audio_s = self.clock(), 0.0
        async with contextlib.aclosing(self.inner.synthesize(phrase)) as chunks:
            async for chunk in chunks:
                audio_s += chunk.duration_s
                yield chunk
        if audio_s > 0:
            self.phrases.append(PhraseTiming((self.clock() - started) / NS_PER_MS, audio_s))


def playback_stalls(chunks: Sequence[tuple[float, float]]) -> list[float]:
    """Паузы звука сверх синтезированных, мс, по фрагментам (приход, мс; длительность, с).

    Плеер начинает с первым фрагментом и играет подряд; фрагмент, пришедший позже, чем доиграл
    предыдущий, — пауза (буфер опустел). Тишина внутри звука фразы — естественная, не считается.
    """
    stalls: list[float] = []
    cursor: float | None = None
    for arrival_ms, duration_s in chunks:
        if cursor is not None and arrival_ms > cursor:
            stalls.append(arrival_ms - cursor)
        start = arrival_ms if cursor is None else max(cursor, arrival_ms)
        cursor = start + duration_s * MS_PER_S
    return stalls


@dataclass(frozen=True, slots=True)
class VoiceSample:
    """Один ответ голосом; `ttfa_ms` — None, если звука не было."""

    prompt_id: str
    ttft_ms: float
    ttfa_ms: float | None
    audio_s: float
    max_stall_ms: float


class VoiceProbe:
    """ReplySink бенчмарка: время первого текста и приход каждого фрагмента звука."""

    def __init__(self, clock: Callable[[], int] = time.perf_counter_ns) -> None:
        self._clock = clock
        self._started = clock()
        self._first_text: float | None = None
        self._chunks: list[tuple[float, float]] = []

    async def text(self, delta: str) -> None:
        """Первый непустой текст — TTFT."""
        if self._first_text is None and delta:
            self._first_text = self._elapsed_ms()

    async def emotion(self, emotion: Emotion) -> None:
        """Эмоция задержку не меняет."""
        del emotion

    async def gesture(self, gesture: Gesture) -> None:
        """Жест задержку не меняет."""
        del gesture

    async def audio(self, chunk: AudioChunk) -> None:
        """Приход фрагмента и его длительность."""
        self._chunks.append((self._elapsed_ms(), chunk.duration_s))

    async def done(self) -> None:
        """Конец хода ничего не добавляет."""

    def sample(self, prompt_id: str) -> VoiceSample:
        """Итог хода; без текста TTFT — время всего хода."""
        first_audio = self._chunks[0][0] if self._chunks else None
        return VoiceSample(
            prompt_id,
            ttft_ms=self._first_text if self._first_text is not None else self._elapsed_ms(),
            ttfa_ms=first_audio,
            audio_s=sum(duration for _, duration in self._chunks),
            max_stall_ms=max(playback_stalls(self._chunks), default=0.0),
        )

    def _elapsed_ms(self) -> float:
        return (self._clock() - self._started) / NS_PER_MS


async def measure_voice(pipeline: ReplyPipeline, prompt: BenchPrompt) -> VoiceSample:
    """Один ход конвейера с голосом на реплику `prompt`."""
    messages = (Message(Role.SYSTEM, SYSTEM_PROMPT), Message(Role.USER, prompt.text))
    probe = VoiceProbe()
    await pipeline.run(messages, probe, StreamParser())
    return probe.sample(prompt.id)


async def run_voice_bench(
    pipeline: ReplyPipeline, tts: TimedTTS, prompts: Sequence[BenchPrompt], runs: int
) -> list[VoiceSample]:
    """Прогрев (неучитываемый ход), затем `runs` кругов по репликам, как в бенчмарке LLM."""
    if prompts:
        await measure_voice(pipeline, prompts[0])
    tts.phrases.clear()
    return [await measure_voice(pipeline, prompt) for _ in range(runs) for prompt in prompts]


def summarize_voice(
    samples: Sequence[VoiceSample], phrases: Sequence[PhraseTiming]
) -> dict[str, Stats]:
    """p50/p95/max: TTFT, TTFA, вклад голоса, худшая пауза ответа, RTF фраз."""
    voiced = [sample for sample in samples if sample.ttfa_ms is not None]
    metrics = {
        "TTFT, мс": [sample.ttft_ms for sample in voiced],
        "TTFA, мс": [sample.ttfa_ms or 0.0 for sample in voiced],
        "TTFA - TTFT, мс": [(sample.ttfa_ms or 0.0) - sample.ttft_ms for sample in voiced],
        "Пауза max, мс": [sample.max_stall_ms for sample in voiced],
        "RTF фразы": [phrase.rtf for phrase in phrases],
    }
    return {
        name: Stats(*(percentile(values, q) for _, q in QUANTILES))
        for name, values in metrics.items()
        if values
    }


def main(argv: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Код возврата: 0 — готово, 1 — сбой конфига, голоса или генерации, 2 — LLM недоступна."""
    args = _parse(argv)
    prompts = load_prompts(args.prompts)
    try:
        samples, phrases = asyncio.run(_bench(args, env, prompts))
    except LLMUnavailable as exc:
        print(f"LLM недоступна: {exc}", file=out)
        return EXIT_UNAVAILABLE
    except VtuberError as exc:
        print(f"Бенчмарк прерван: {exc}", file=out)
        return EXIT_FAILED
    summary = summarize_voice(samples, phrases)
    silent = sum(sample.ttfa_ms is None for sample in samples)
    print(render(summary, len(samples)) + f"\nБез звука: {silent}, фраз: {len(phrases)}", file=out)
    if args.out:
        report = {"summary": summary, "samples": samples, "phrases": phrases}
        text = json.dumps(report, default=asdict, ensure_ascii=False, indent=2)
        args.out.write_text(text, encoding="utf-8")
    return 0


async def _bench(
    args: argparse.Namespace, env: Mapping[str, str], prompts: Sequence[BenchPrompt]
) -> tuple[list[VoiceSample], list[PhraseTiming]]:
    cfg = load_app_config(ROOT, env)
    tts_cfg = cfg.tts.resolved(ROOT)
    engine = tts_backends().create(args.tts or tts_cfg.backend, tts_cfg)
    if engine is None:
        msg = "бенчмарку голоса нужен движок TTS: --tts silero или piper"
        raise ConfigError(msg)
    generation = cfg.llm.generation
    params = GenerationParams(max_tokens=generation.max_tokens, temperature=generation.temperature)
    llm_source = (
        ScriptedLLM(args.sim_ttft_ms, args.sim_tps)
        if args.simulate_llm
        else open_llm(args.backend, env)
    )
    async with engine as tts, llm_source as llm:
        timed = TimedTTS(tts)
        pipeline = _pipeline(llm, params, Voice(timed, cfg.pipeline.chunker))
        samples = await run_voice_bench(pipeline, timed, prompts, args.runs)
        return samples, timed.phrases


def _pipeline(llm: LLMPort, params: GenerationParams, voice: Voice) -> ReplyPipeline:
    # Замеры конвейера бенчмарку не нужны: свои — точнее (по фрагментам), шина без подписчиков.
    return ReplyPipeline(llm, params, Telemetry(EventBus()), voice)


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS)
    parser.add_argument("--runs", type=int, default=1, help="кругов по всем репликам")
    parser.add_argument("--tts", help="движок из реестра; по умолчанию [tts].backend")
    parser.add_argument("--backend", help="LLM-адаптер из реестра; по умолчанию [llm].backend")
    parser.add_argument("--simulate-llm", action="store_true", help="LLM-заглушка вместо сервера")
    parser.add_argument("--sim-ttft-ms", type=float, default=250.0, help="TTFT заглушки (NFR-01)")
    parser.add_argument("--sim-tps", type=float, default=40.0, help="токенов в секунду заглушки")
    parser.add_argument("--out", type=Path, help="сохранить замеры в JSON")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], os.environ, sys.stdout))
