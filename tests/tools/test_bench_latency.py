import asyncio
import io
import json
from pathlib import Path

import pytest

from tests.fakes import FakeLLM
from tests.llm_stub import LLMStub
from tools.bench_latency import (
    WARMUP_MESSAGES,
    BenchPrompt,
    Sample,
    load_prompts,
    main,
    measure,
    percentile,
    render,
    run_bench,
    run_speculative_bench,
    summarize,
)
from tools.llm_client import SYSTEM_PROMPT
from vtuber.domain import Message, Role
from vtuber.ports import GenerationParams

ROOT = Path(__file__).resolve().parents[2]
PARAMS = GenerationParams(max_tokens=32, temperature=0.7)


def test_percentile_uses_nearest_rank() -> None:
    values = [float(value) for value in range(1, 21)]

    assert percentile(values, 0.5) == 10
    assert percentile(values, 0.95) == 19
    assert percentile(values, 1.0) == 20
    assert percentile([7.0], 0.95) == 7


async def test_measure_counts_deltas_and_orders_times() -> None:
    llm = FakeLLM("Привет, как дела?", chunk_size=4, delay_ms=1)

    sample = await measure(llm, BenchPrompt(id="p", kind="short", text="Привет"), PARAMS)

    assert sample.deltas == 5
    assert 0 < sample.ttft_ms <= sample.total_ms


async def test_bench_warms_up_then_goes_round_robin() -> None:
    llm = FakeLLM("ок")
    prompts = [BenchPrompt(id=name, kind="short", text=name) for name in ("a", "b")]

    samples = await run_bench(llm, prompts, PARAMS, runs=2)

    assert [sample.prompt_id for sample in samples] == ["a", "b", "a", "b"]
    assert llm.prefills == [WARMUP_MESSAGES]
    user_texts = [messages[-1].text for messages, _ in llm.calls]
    assert user_texts == ["Привет!", "a", "b", "a", "b"]


async def test_speculative_bench_prefills_draft_before_each_measure() -> None:
    llm = FakeLLM("ок")
    prompts = [BenchPrompt(id="a", kind="long", text="Расскажи мне про котов")]

    samples = await run_speculative_bench(llm, prompts, PARAMS, runs=1)

    assert [sample.prompt_id for sample in samples] == ["a"]
    system = Message(Role.SYSTEM, SYSTEM_PROMPT)
    assert llm.prefills == [WARMUP_MESSAGES, (system, Message(Role.USER, "Расскажи мне про"))]


def test_summary_and_table_cover_ttft_total_and_tps() -> None:
    samples = [Sample("p", ttft_ms=100.0 + i, total_ms=500.0, deltas=41) for i in range(10)]

    summary = summarize(samples)
    table = render(summary, len(samples))

    assert summary["TTFT, мс"].p50 == 104
    assert summary["TTFT, мс"].p95 == 109
    assert summary["TPS"].p50 == pytest.approx(100.0, rel=0.05)
    assert "TTFT" in table
    assert "p95" in table


def test_repository_prompts_are_valid_and_varied() -> None:
    prompts = load_prompts(ROOT / "bench" / "prompts_ru.jsonl")

    assert 30 <= len(prompts) <= 50
    assert len({prompt.id for prompt in prompts}) == len(prompts)
    assert {prompt.kind for prompt in prompts} == {"short", "medium", "long", "memory"}


async def test_cli_measures_real_http_adapter_against_stub(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts.jsonl"
    prompts.write_text('{"id": "p1", "kind": "short", "text": "Привет"}\n', encoding="utf-8")
    output = io.StringIO()

    report = tmp_path / "report.json"

    async with LLMStub("Привет-привет!", chunk_size=4, delay_s=0) as stub:
        env = {"VTUBER_LLM__BASE_URL": stub.url}
        argv = ["--prompts", str(prompts), "--runs", "2", "--speculative", "--out", str(report)]
        # main сама запускает asyncio.run — в отдельном потоке, заглушка живёт в цикле теста.
        code = await asyncio.to_thread(main, argv, env, output)

    assert code == 0
    assert "TTFT" in output.getvalue()
    assert len(json.loads(report.read_text(encoding="utf-8"))["samples"]) == 2
    # Прогрев черновиком дошёл до сервера: шаблон и /completion без генерации на каждый замер.
    assert len(stub.bodies("/completion")) >= 2


def test_cli_reports_unavailable_server_with_exit_code_2() -> None:
    output = io.StringIO()
    env = {"VTUBER_LLM__BASE_URL": "http://127.0.0.1:9", "VTUBER_LLM__CONNECT_TIMEOUT_S": "0.2"}

    code = main(["--runs", "1"], env, output)

    assert code == 2
    assert "start_llm" in output.getvalue()
