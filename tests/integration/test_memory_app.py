"""`python -m vtuber` с фоновой памятью (S-10.4): после хода и простоя факт — в базе на диске."""

import asyncio
import io
import sqlite3
import time
from pathlib import Path

import pytest
import structlog

from tests.contract.memory_factories import E5_DIR
from tests.llm_stub import LLMStub
from vtuber.bootstrap import Console, main

ROOT = Path(__file__).resolve().parents[2]
# Ответ заглушки годится и для диалога, и для извлечения фактов (тот же сервер, слоты 0 и 1).
FACTS_REPLY = '{"facts": [{"text": "Пользователя зовут Алексей", "importance": 1}]}'


class _SlowStdin:
    """Одна реплика, затем пауза (простой, фон работает) и конец ввода."""

    def __init__(self, pause_s: float) -> None:
        self._lines = ["Меня зовут Алексей\n"]
        self._pause_s = pause_s

    def readline(self) -> str:
        if self._lines:
            return self._lines.pop()
        time.sleep(self._pause_s)  # поток чтения консоли — не цикл событий
        return ""


@pytest.mark.slow
@pytest.mark.skipif(not (E5_DIR / "model.onnx").is_file(), reason=f"нет модели e5 в {E5_DIR}")
async def test_fact_from_chat_lands_in_memory_store(tmp_path: Path) -> None:
    store = tmp_path / "memory" / "facts.sqlite"
    async with LLMStub(FACTS_REPLY, chunk_size=16, delay_s=0) as stub:
        env = {
            "VTUBER_LLM__BASE_URL": stub.url,
            "VTUBER_LOGGING__FILE": str(tmp_path / "app.jsonl"),
            "VTUBER_TELEMETRY__TRACES_FILE": str(tmp_path / "traces.jsonl"),
            "VTUBER_MEMORY__STORE_PATH": str(store),
            "VTUBER_MEMORY__VAULT_PATH": str(store.parent / "vault"),
            "VTUBER_SCHEDULER__IDLE_AFTER_MS": "50",
        }
        console = Console(_SlowStdin(pause_s=3), io.StringIO())
        code = await asyncio.to_thread(main, ["--root", str(ROOT)], env, console)
    structlog.reset_defaults()

    assert code == 0
    with sqlite3.connect(store) as db:
        rows = db.execute("select text, source from facts").fetchall()
    assert rows == [("Пользователя зовут Алексей", "extracted")]
    # Фон шёл в своём слоте: кэш диалога (слот 0) не тронут.
    bodies = stub.bodies("/v1/chat/completions")
    slots = {body.get("id_slot") for body in bodies if isinstance(body, dict)}
    assert slots == {0, 1}
