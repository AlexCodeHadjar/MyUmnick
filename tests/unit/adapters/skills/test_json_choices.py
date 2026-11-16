from pathlib import Path

from vtuber.adapters.skills import JsonSkillChoices


async def test_choices_round_trip_and_survive_broken_file(tmp_path: Path) -> None:
    path = tmp_path / "data" / "skills.json"
    store = JsonSkillChoices(path)
    assert await store.load() == {}

    await store.save({"tools.timer": False, "web_search": True})
    assert await JsonSkillChoices(path).load() == {"tools.timer": False, "web_search": True}

    path.write_text('{"a": "yes", "b": false}', encoding="utf-8")
    assert await store.load() == {"b": False}
    path.write_text("not json", encoding="utf-8")
    assert await store.load() == {}
