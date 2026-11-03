"""Инструменты прогона на аренде, на заглушках: ошибка в скрипте стоит оплаченных часов."""

import asyncio
import base64
import json
import shutil
import subprocess
import zlib
from pathlib import Path

import pytest

from tests.fakes import FakeLLM
from tests.plugins.test_code_assistant import CODE, _Server
from tools.bench_vision import measure, sample_image, summary
from tools.check_assistant import Outcome, run_task
from tools.eval_code import CodeCase, render, run_cases
from vtuber.ports import GenerationParams

ROOT = Path(__file__).resolve().parents[2]
TSV = ROOT / "scripts" / "remote" / "models_extra.tsv"
COLUMNS = 8
SHA_LENGTH = 64


def test_generated_image_is_a_valid_png_and_differs() -> None:
    first = base64.b64decode(sample_image(0, side=8).base64)
    assert first.startswith(b"\x89PNG")
    start = first.index(b"IDAT") + 4
    assert zlib.decompress(first[start:-16])
    assert sample_image(0, side=8).base64 != sample_image(1, side=8).base64


async def test_vision_bench_sends_images_only_on_its_side() -> None:
    llm = FakeLLM("Вижу узор.")
    samples = await measure(llm, 2)
    messages = [call[0][-1] for call in llm.calls]
    assert [bool(m.images) for m in messages] == [True, False, True, False]
    assert set(summary(samples)) == {"image_ttft_ms", "text_ttft_ms"}


async def test_code_eval_reports_speed() -> None:
    case = CodeCase(id="add", task="Write add.", checks="assert add(1, 2) == 3")
    good = "```python\ndef add(a, b):\n    return a + b\n```"
    results = await run_cases(FakeLLM(good), [case], GenerationParams(16, 0.0))
    assert results[0].ttft_ms >= 0
    assert "TTFT" in render(results)


async def test_assistant_check_finds_code_in_the_chat() -> None:
    main, code = _Server("Write a prime check"), _Server(CODE)
    main_srv = await asyncio.start_server(main.handle, "127.0.0.1", 0)
    code_srv = await asyncio.start_server(code.handle, "127.0.0.1", 0)
    main_url = f"http://127.0.0.1:{main_srv.sockets[0].getsockname()[1]}"
    code_url = f"http://127.0.0.1:{code_srv.sockets[0].getsockname()[1]}"
    outcome = await run_task(main_url, code_url)
    main_srv.close()
    code_srv.close()
    assert outcome.problem == ""


@pytest.mark.parametrize(
    ("outcome", "word"),
    [
        (Outcome(spoken="Недоступен"), "ничего нет"),
        (Outcome(shown=["просто текст"], spoken="Готово"), "нет кода"),
        (Outcome(shown=["def a(): ..."], spoken="def a(): ..."), "в речь"),
    ],
)
def test_assistant_check_names_the_problem(outcome: Outcome, word: str) -> None:
    assert word in outcome.problem


def test_extra_models_are_pinned_and_verifiable() -> None:
    rows = [
        line.split("\t")
        for line in TSV.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    assert rows
    for row in rows:
        assert len(row) == COLUMNS, row[0]
        assert len(row[3]) == 40, f"{row[0]}: ревизия должна быть закреплена"
        assert int(row[5]) > 0
        assert len(row[6]) == SHA_LENGTH


@pytest.mark.parametrize(
    "script",
    ["run_my_set.sh", "start_llm.sh", "common.sh", "download_models.sh"],
)
def test_shell_scripts_parse(script: str) -> None:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("нет bash")
    done = subprocess.run(  # noqa: S603 — свой скрипт из репозитория
        [bash, "-n", str(ROOT / "scripts" / "remote" / script)],
        capture_output=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr


def test_report_is_json_ready(tmp_path: Path) -> None:
    out = tmp_path / "x.json"
    out.write_text(json.dumps(summary({"a": [1.0, 2.0]})), encoding="utf-8")
    assert json.loads(out.read_text(encoding="utf-8"))["a"]["p95"] == pytest.approx(2.0)
