"""Гейт регрессий: роняет прогон при искусственной регрессии, чужие цифры не сравнивает (S-9.4)."""

import io
import json
from pathlib import Path

import httpx

from tools import bench_core, perf_gate
from tools.perf_gate import PerfReport, Stats, regressions
from vtuber.adapters.llm import LlamaCppLLM
from vtuber.bootstrap import load_app_config
from vtuber.bootstrap.memory import _background_llm
from vtuber.domain import Message, Role
from vtuber.ports import GenerationParams

ROOT = Path(__file__).resolve().parents[2]


def _report(p95: float, machine: str = "a") -> PerfReport:
    return PerfReport(machine=machine, metrics={"ttft": Stats(p50=p95 / 2, p95=p95)})


def _run(tmp_path: Path, base: PerfReport, now: PerfReport) -> tuple[int, str]:
    (tmp_path / "base.json").write_text(base.model_dump_json(), encoding="utf-8")
    (tmp_path / "now.json").write_text(now.model_dump_json(), encoding="utf-8")
    out = io.StringIO()
    code = perf_gate.main([str(tmp_path / "base.json"), str(tmp_path / "now.json")], out)
    return code, out.getvalue()


def test_growth_within_the_limit_passes(tmp_path: Path) -> None:
    assert _run(tmp_path, _report(100), _report(114))[0] == 0


def test_regression_fails_and_is_named(tmp_path: Path) -> None:
    code, text = _run(tmp_path, _report(100), _report(116))
    assert code == perf_gate.EXIT_REGRESSION
    assert "ttft" in text
    assert "+16 %" in text


def test_noise_below_a_millisecond_is_not_a_regression(tmp_path: Path) -> None:
    assert _run(tmp_path, _report(0.13), _report(0.17))[0] == 0


def test_lost_metric_is_a_failure() -> None:
    now = PerfReport(machine="a", metrics={})
    assert regressions(_report(100), now, 0.15)[0].now is None


def test_other_machine_is_not_compared(tmp_path: Path) -> None:
    code, text = _run(tmp_path, _report(100), _report(500, machine="b"))
    assert code == perf_gate.EXIT_NOT_COMPARABLE
    assert "Разные машины" in text


def test_broken_report_is_not_a_pass(tmp_path: Path) -> None:
    (tmp_path / "base.json").write_text("{}", encoding="utf-8")
    code = perf_gate.main([str(tmp_path / "base.json"), str(tmp_path / "нет.json")], io.StringIO())
    assert code == perf_gate.EXIT_NOT_COMPARABLE


def test_real_bench_with_injected_delay_trips_the_gate(tmp_path: Path) -> None:
    base, slow = tmp_path / "base.json", tmp_path / "slow.json"
    args = ["--turns", "5", "--out"]
    assert bench_core.main([*args, str(base)], {}, io.StringIO()) == 0
    assert bench_core.main([*args, str(slow), "--inject-delay-ms", "60"], {}, io.StringIO()) == 0
    assert json.loads(base.read_text(encoding="utf-8"))["metrics"]["core.first_text_ms"]
    assert perf_gate.main([str(base), str(slow)], io.StringIO()) == perf_gate.EXIT_REGRESSION


async def test_background_work_does_not_touch_the_dialogue_slot() -> None:
    cfg = load_app_config(ROOT, {})
    background = _background_llm(cfg)
    assert background.llamacpp.slot_id != cfg.llm.llamacpp.slot_id
    slots: list[int] = []

    def respond(request: httpx.Request) -> httpx.Response:
        slots.append(json.loads(request.content)["id_slot"])
        return httpx.Response(200, text="data: [DONE]\n\n")

    async with LlamaCppLLM(background, httpx.MockTransport(respond)) as llm:
        params = GenerationParams(max_tokens=4, temperature=0.1)
        _ = [delta async for delta in llm.stream([Message(Role.USER, "факты")], params)]
    assert slots == [cfg.memory.background_slot_id]
