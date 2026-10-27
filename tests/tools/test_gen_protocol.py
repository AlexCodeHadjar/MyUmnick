from pathlib import Path

import pytest

from tools import gen_protocol
from tools.gen_protocol import main, render_doc, render_ts, stale_files, ts_type


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"type": "string"}, "string"),
        ({"type": "number"}, "number"),
        ({"type": "integer"}, "number"),
        ({"type": "boolean"}, "boolean"),
        ({"const": "chat.send", "type": "string"}, '"chat.send"'),
        ({"const": 1, "type": "integer"}, "1"),
        ({"enum": ["a", "b"], "type": "string"}, '"a" | "b"'),
        ({"anyOf": [{"type": "string"}, {"type": "null"}]}, "string | null"),
        ({"$ref": "#/$defs/SendData"}, "SendData"),
        ({"type": "object", "properties": {}}, "Record<string, never>"),
    ],
)
def test_schema_nodes_map_to_ts(schema: dict[str, object], expected: str) -> None:
    assert ts_type(schema) == expected


def test_ts_has_every_message_and_both_unions() -> None:
    ts = render_ts()

    for name in ("ChatSend", "ChatCancel", "ChatDelta", "AvatarEmotion", "Status", "ErrorMessage"):
        assert f"export interface {name} {{" in ts
    assert "export type InboundMessage = ChatSend | ChatCancel;" in ts
    assert "export type OutboundMessage = TurnStartedMessage | ChatDelta" in ts
    assert 'type: "chat.delta";' in ts
    assert "turn: string | null;" in ts
    assert ts.endswith(";\n")


def test_doc_lists_every_message_type_and_audio_frame() -> None:
    doc = render_doc()

    for kind in ("chat.send", "chat.cancel", "turn.started", "chat.delta", "metrics.span", "error"):
        assert f"### `{kind}`" in doc
    assert "## Бинарный аудиокадр" in doc


def test_check_reports_stale_files_until_regenerated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gen_protocol, "TS_OUT", tmp_path / "ui" / "protocol.gen.ts")
    monkeypatch.setattr(gen_protocol, "DOC_OUT", tmp_path / "protocol.md")
    monkeypatch.setattr(gen_protocol, "ROOT", tmp_path)

    assert main(["--check"]) == 1
    assert main([]) == 0
    assert stale_files() == []

    (tmp_path / "protocol.md").write_text("правка руками", encoding="utf-8")
    assert stale_files() == [tmp_path / "protocol.md"]


def test_repository_generated_files_are_up_to_date() -> None:
    assert stale_files() == []
