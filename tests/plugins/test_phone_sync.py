import json
from pathlib import Path

from vtuber.kernel import EventBus, PluginContext
from vtuber_phone_sync import PhoneSyncPlugin
from vtuber_phone_sync.merge import parse_jsonl, pc_note_id


class FakePhone:
    """Телефон с папкой UmNick: `notes` — его notes.jsonl, `pushed` — что положил ПК."""

    def __init__(self, notes: str) -> None:
        self.notes = notes
        self.pushed: list[str] = []

    async def find(self) -> str | None:
        return "TECNO POVA 6 Pro 5G"

    async def pull_notes(self) -> str | None:
        return self.notes

    async def push_from_pc(self, payload: str) -> bool:
        self.pushed.append(payload)
        return True


def _line(note_id: str, text: str) -> str:
    return (
        json.dumps(
            {"id": note_id, "text": text, "created": "2026-11-17T10:00:00+03:00", "origin": "phone"}
        )
        + "\n"
    )


async def _plugin(tmp_path: Path, phone: FakePhone) -> PhoneSyncPlugin:
    plugin = PhoneSyncPlugin(phone)
    settings = {
        "notes_file": str(tmp_path / "notes.txt"),
        "ledger_file": str(tmp_path / "ledger.json"),
        "poll_s": 3600,
    }
    await plugin.setup(PluginContext("phone_sync", EventBus(), settings))
    await plugin.shutdown()
    return plugin


async def test_phone_notes_land_in_pc_notebook_once(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("хлеб\n", encoding="utf-8")
    phone = FakePhone(_line("a", "купить молоко") + "битая строка\n" + _line("b", "позвонить маме"))
    plugin = await _plugin(tmp_path, phone)

    assert await plugin.sync("p") == 2
    assert await plugin.sync("p") == 0
    lines = (tmp_path / "notes.txt").read_text(encoding="utf-8").splitlines()
    assert lines == ["хлеб", "купить молоко", "позвонить маме"]


async def test_pc_notes_go_to_phone_without_echo(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("хлеб\n", encoding="utf-8")
    phone = FakePhone(_line("a", "купить молоко"))
    plugin = await _plugin(tmp_path, phone)

    await plugin.sync("p")
    sent = parse_jsonl(phone.pushed[-1])
    assert [(note.id, note.text) for note in sent] == [(pc_note_id("хлеб"), "хлеб")]
