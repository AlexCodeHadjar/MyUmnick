"""`python -m vtuber` целиком: конфиг, персона, реестр бэкендов, прогрев, чат — против заглушки."""

import asyncio
import io
import json
from pathlib import Path

import pytest
import structlog

from tests.llm_stub import LLMStub
from vtuber.bootstrap import Console, main, run

ROOT = Path(__file__).resolve().parents[2]


def _env(tmp_path: Path, base_url: str) -> dict[str, str]:
    return {
        "VTUBER_LLM__BASE_URL": base_url,
        "VTUBER_LLM__CONNECT_TIMEOUT_S": "0.2",
        "VTUBER_LOGGING__FILE": str(tmp_path / "app.jsonl"),
        "VTUBER_TELEMETRY__TRACES_FILE": str(tmp_path / "traces.jsonl"),
        "VTUBER_MEMORY__ENABLED": "false",
        "VTUBER_STT__ENABLED": "false",
    }


async def test_chat_answers_writes_logs_and_traces(tmp_path: Path) -> None:
    out = io.StringIO()
    console = Console(io.StringIO("Привет!\n"), out)

    async with LLMStub("<happy>Привет-привет!", chunk_size=4, delay_s=0) as stub:
        # main сама запускает asyncio.run — в отдельном потоке; заглушка живёт в цикле теста.
        code = await asyncio.to_thread(
            main, ["--root", str(ROOT)], _env(tmp_path, stub.url), console
        )
    structlog.reset_defaults()

    assert code == 0
    assert "[happy] Привет-привет!" in out.getvalue()
    assert "TTFT" in out.getvalue()
    paths = [path for path, _ in stub.requests]
    assert paths[:2] == ["/apply-template", "/completion"]  # прогрев префикса (T-06)
    assert "/v1/chat/completions" in paths
    assert "llm.ready" in (tmp_path / "app.jsonl").read_text(encoding="utf-8")
    traces = (tmp_path / "traces.jsonl").read_text(encoding="utf-8").splitlines()
    assert {json.loads(line)["name"] for line in traces} >= {"llm.first_token", "llm.stream"}


def test_unavailable_server_exits_with_code_2(tmp_path: Path) -> None:
    out = io.StringIO()

    code = main(
        ["--root", str(ROOT)], _env(tmp_path, "http://127.0.0.1:9"), Console(io.StringIO(), out)
    )
    structlog.reset_defaults()

    assert code == 2
    assert "start_llm" in out.getvalue()


def test_bad_config_exits_with_code_1(tmp_path: Path) -> None:
    out = io.StringIO()
    env = _env(tmp_path, "http://127.0.0.1:9") | {"VTUBER_LLM__BACKEND": "нет-такого"}

    code = main(["--root", str(ROOT)], env, Console(io.StringIO(), out))
    structlog.reset_defaults()

    assert code == 1
    assert "нет-такого" in out.getvalue()
    assert "llamacpp, openai_compat" in out.getvalue()


def test_console_entry_reports_missing_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["vtuber", "--root", str(tmp_path)])

    assert run() == 1
    assert "default.toml" in capsys.readouterr().out
