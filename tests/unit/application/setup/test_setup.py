"""Мастер: рекомендация, проверка сумм, докачка, нехватка места, выбор пользователя."""

import asyncio
import hashlib
import tomllib
from collections.abc import AsyncGenerator, Mapping
from pathlib import Path

import pytest

from vtuber.application.setup import (
    CatalogFile,
    CatalogItem,
    Installer,
    InstallProgress,
    SetupCatalog,
    SetupChoice,
    SetupWizard,
    recommend,
)
from vtuber.bootstrap.setup import load_catalog, write_choice
from vtuber.domain import GpuMemory, SetupFailed

LOTS = 10**15
CONTENT = {"http://x/llm": b"l" * 1000, "http://x/stt": b"s" * 100}


def _listing(path: Path) -> list[Path]:
    return list(path.iterdir())


def _read(path: Path) -> bytes:
    return path.read_bytes()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file(url: str, path: str, *, sha: str | None = None) -> CatalogFile:
    data = CONTENT[url]
    return CatalogFile(path=path, url=url, size=len(data), sha256=sha or _sha(data))


def _catalog(*, llm_sha: str | None = None) -> SetupCatalog:
    llm = CatalogItem(
        id="llm",
        title="Мозг",
        license="Gemma",
        required=True,
        min_vram_mb=11000,
        files=(_file("http://x/llm", "models/llm/m.gguf", sha=llm_sha),),
    )
    stt = CatalogItem(
        id="stt",
        title="Слух",
        license="MIT",
        required=False,
        min_vram_mb=1700,
        files=(_file("http://x/stt", "models/stt/s.bin"),),
    )
    return SetupCatalog(
        llm_item="llm",
        llm_model_path="models/llm/m.gguf",
        voices=("xenia", "baya"),
        default_voice="xenia",
        items=(llm, stt),
    )


class _Fetcher:
    def __init__(self, *, break_after: int | None = None) -> None:
        self.break_after = break_after
        self.offsets: list[int] = []

    async def fetch(self, url: str, offset: int) -> AsyncGenerator[bytes]:
        self.offsets.append(offset)
        data = CONTENT[url][offset:]
        if self.break_after is not None:
            yield data[: self.break_after]
            raise SetupFailed("обрыв")
        yield data


class _Probe:
    def __init__(self, memory: GpuMemory | None) -> None:
        self._memory = memory

    async def memory(self) -> GpuMemory | None:
        return self._memory


async def _ignore(_: InstallProgress) -> None:
    await asyncio.sleep(0)


def _installer(root: Path, fetcher: _Fetcher, free: int = LOTS) -> Installer:
    return Installer(root, fetcher, lambda _: free)


def test_recommends_everything_on_target_card() -> None:
    result = recommend(_catalog(), GpuMemory(16384, 0))
    assert result.item_ids == ("llm", "stt")
    assert result.voice == "xenia"
    assert result.warnings == ()


def test_small_card_keeps_required_and_warns() -> None:
    result = recommend(_catalog(), GpuMemory(1000, 0))
    assert result.item_ids == ("llm",)
    assert len(result.warnings) == 2
    assert "медленными" in result.warnings[0]


def test_no_nvidia_card_warns_but_recommends() -> None:
    result = recommend(_catalog(), None)
    assert result.item_ids == ("llm", "stt")
    assert "NVIDIA" in result.warnings[0]


async def test_install_places_verified_file_and_reports_progress(tmp_path: Path) -> None:
    catalog = _catalog()
    seen: list[InstallProgress] = []

    async def progress(value: InstallProgress) -> None:
        seen.append(value)

    installer = _installer(tmp_path, _Fetcher())
    assert not installer.is_installed(catalog.items[0])
    await installer.install(catalog.items, progress)
    assert installer.is_installed(catalog.items[0])
    assert _read(tmp_path / "models/llm/m.gguf") == CONTENT["http://x/llm"]
    assert not [p for p in _listing(tmp_path / "models/llm") if p.suffix == ".part"]
    assert seen[-1].done == seen[-1].total == 1100


async def test_wrong_checksum_leaves_nothing_behind(tmp_path: Path) -> None:
    catalog = _catalog(llm_sha="0" * 64)
    installer = _installer(tmp_path, _Fetcher())
    with pytest.raises(SetupFailed, match="повреждённым"):
        await installer.install(catalog.items[:1], _ignore)
    assert _listing(tmp_path / "models/llm") == []


async def test_break_resumes_from_where_it_stopped(tmp_path: Path) -> None:
    catalog = _catalog()
    with pytest.raises(SetupFailed, match="обрыв"):
        await _installer(tmp_path, _Fetcher(break_after=300)).install(catalog.items[:1], _ignore)
    assert tmp_path / "models/llm/m.gguf" not in _listing(tmp_path / "models/llm")
    fetcher = _Fetcher()
    await _installer(tmp_path, fetcher).install(catalog.items[:1], _ignore)
    assert fetcher.offsets == [300]
    assert _read(tmp_path / "models/llm/m.gguf") == CONTENT["http://x/llm"]


async def test_installed_file_is_not_downloaded_again(tmp_path: Path) -> None:
    catalog = _catalog()
    await _installer(tmp_path, _Fetcher()).install(catalog.items[:1], _ignore)
    fetcher = _Fetcher()
    await _installer(tmp_path, fetcher).install(catalog.items[:1], _ignore)
    assert fetcher.offsets == []


async def test_not_enough_disk_stops_before_download(tmp_path: Path) -> None:
    fetcher = _Fetcher()
    with pytest.raises(SetupFailed, match="места на диске"):
        await _installer(tmp_path, fetcher, free=1).install(_catalog().items, _ignore)
    assert fetcher.offsets == []


async def test_path_outside_root_is_refused(tmp_path: Path) -> None:
    evil = CatalogItem(
        id="x",
        title="x",
        license="x",
        required=False,
        min_vram_mb=0,
        files=(_file("http://x/stt", "../../evil.bin"),),
    )
    with pytest.raises(SetupFailed, match="за пределы"):
        await _installer(tmp_path, _Fetcher()).install((evil,), _ignore)


def _wizard(
    root: Path,
    written: list[Mapping[str, Mapping[str, str | bool]]],
    gpu: GpuMemory | None = None,
) -> SetupWizard:
    probe = _Probe(gpu or GpuMemory(16384, 0))
    return SetupWizard(_catalog(), _installer(root, _Fetcher()), probe, written.append)


async def _run(wizard: SetupWizard, choice: SetupChoice) -> str | None:
    done: asyncio.Future[str | None] = asyncio.get_running_loop().create_future()

    async def finished(problem: str | None) -> None:
        done.set_result(problem)

    wizard.start(choice, _ignore, finished)
    return await asyncio.wait_for(done, 2)


async def test_wizard_nothing_downloaded_until_started(tmp_path: Path) -> None:
    written: list[Mapping[str, Mapping[str, str | bool]]] = []
    state = await _wizard(tmp_path, written).state()
    assert state.needed
    assert state.installed == ()
    assert _listing(tmp_path) == []


async def test_wizard_installs_choice_and_writes_config(tmp_path: Path) -> None:
    written: list[Mapping[str, Mapping[str, str | bool]]] = []
    wizard = _wizard(tmp_path, written)
    assert await _run(wizard, SetupChoice(("llm",), "baya")) is None
    assert written[0]["setup"] == {"enabled": True}
    assert written[0]["llama_server"] == {"autostart": True, "model": "models/llm/m.gguf"}
    assert written[0]["tts.silero"] == {"speaker": "baya"}
    state = await wizard.state()
    assert not state.needed
    assert state.installed == ("llm",)


@pytest.mark.parametrize(
    "choice",
    [
        SetupChoice(("stt",), "xenia"),
        SetupChoice(("llm", "нет"), "xenia"),
        SetupChoice(("llm",), "нет"),
    ],
)
def test_wizard_refuses_bad_choice(tmp_path: Path, choice: SetupChoice) -> None:
    wizard = _wizard(tmp_path, [])

    async def noop(_: str | None) -> None:
        await asyncio.sleep(0)

    with pytest.raises(SetupFailed):
        wizard.start(choice, _ignore, noop)


def test_choice_file_is_read_back_as_toml(tmp_path: Path) -> None:
    path = tmp_path / "config" / "setup.toml"
    write_choice(
        path, {"llama_server": {"autostart": True, "model": 'a"b'}, "tts.silero": {"speaker": "ё"}}
    )
    loaded = tomllib.loads(path.read_text(encoding="utf-8"))
    assert loaded["llama_server"] == {"autostart": True, "model": 'a"b'}
    assert loaded["tts"]["silero"]["speaker"] == "ё"


def test_shipped_catalog_is_valid_and_pinned() -> None:
    root = Path(__file__).parents[4]
    catalog = load_catalog(root / "config" / "catalog.toml")
    assert catalog.default_voice in catalog.voices
    assert catalog.llm_item in {item.id for item in catalog.items}
    for item in catalog.items:
        for file in item.files:
            assert file.url.startswith("https://")
            assert file.path.startswith("models/")
