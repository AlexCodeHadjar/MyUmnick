"""Собирает ядро в `packaging/dist/vtuber-core/` и кладёт рядом конфиг и персоны (ADR-0019).

Запуск: `uv run --group packaging python packaging/fetch_llama.py`, затем `uv run --group packaging
python packaging/build_sidecar.py`. Окружение — `uv sync --all-extras`. Перед сборкой плагины
ставятся в окружение: их метаданные и код идут в комплект.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parent.parent
PACKAGING: Final = ROOT / "packaging"
DIST: Final = PACKAGING / "dist"
PLUGINS: Final = ("obs", "stream_chat", "stream_director", "tools")
SHIPPED_SETUP: Final = """[setup]
enabled = true

[llama_server]
autostart = true
"""


def _run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)  # noqa: S603 — команды заданы здесь же


def main() -> int:
    """Код возврата 0; сбой шага — исключение с его командой."""
    uv = shutil.which("uv") or "uv"
    for plugin in PLUGINS:
        _run(uv, "pip", "install", "--quiet", "-e", f"plugins/{plugin}")
    _run(
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        str(DIST),
        "--workpath",
        str(PACKAGING / "build"),
        str(PACKAGING / "vtuber_core.spec"),
    )
    target = DIST / "vtuber-core"
    for folder in ("config", "personas"):
        shutil.copytree(ROOT / folder, target / folder, dirs_exist_ok=True)
    (target / "config" / "user.toml").unlink(missing_ok=True)
    # В поставке мастер включён, а llama-server запускает само приложение.
    (target / "config" / "setup.toml").write_text(SHIPPED_SETUP, encoding="utf-8", newline="\n")
    # Рядом с ядром, путь — `[llama_server].executable`; без неё ядро всё равно работает.
    llama = DIST / "llama"
    if llama.is_dir():
        shutil.copytree(llama, target / "llama", dirs_exist_ok=True)
    print(f"Готово: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
