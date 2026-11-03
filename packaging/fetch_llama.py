"""Скачивает закреплённую сборку llama-server в `packaging/dist/llama/` с проверкой сумм (ADR-0019).

CUDA 13.4: Blackwell (RTX 5070 Ti) требует 12.8 или новее, поэтому сборка 12.4 не подходит.
Новая версия — только вместе с прогоном `scripts/start_llm.ps1` и обновлением таблицы ниже.
"""

import hashlib
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Final

TAG: Final = "b12064"
BASE_URL: Final = f"https://github.com/ggml-org/llama.cpp/releases/download/{TAG}"
ARCHIVES: Final = {
    f"llama-{TAG}-bin-win-cuda-13.4-x64.zip": (
        "8c4a9b04c3b1c7d52429a7b5e8a44b2b79cb0bacdc331a260ce5349c4444e883"
    ),
    "cudart-llama-bin-win-cuda-13.4-x64.zip": (
        "738f8c251ac22b70c3ae6f83a10cf222725df0395246a2cf58f32bdb85fbe668"
    ),
}
DIST: Final = Path(__file__).resolve().parent / "dist"
TARGET: Final = DIST / "llama"
DOWNLOADS: Final = Path(__file__).resolve().parent / "build" / "downloads"
CHUNK: Final = 1024 * 1024
ATTEMPTS: Final = 3


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch(name: str, expected: str) -> Path:
    path = DOWNLOADS / name
    if path.is_file() and _sha256(path) == expected:
        return path
    # Длинная загрузка иногда обрывается молча (проверено на 424 МБ): её ловит только сумма.
    for attempt in range(1, ATTEMPTS + 1):
        print(f"Скачивается {name}, попытка {attempt}")
        with urllib.request.urlopen(f"{BASE_URL}/{name}") as response, path.open("wb") as out:  # noqa: S310 — https, адрес задан здесь
            shutil.copyfileobj(response, out, CHUNK)
        if (actual := _sha256(path)) == expected:
            return path
        print(f"{name}: сумма {actual}, ожидалась {expected}")
        path.unlink()
    msg = f"{name}: сумма не совпала за {ATTEMPTS} попытки — файл удалён"
    raise ValueError(msg)


def main() -> int:
    """Код возврата 0; неверная сумма или сбой сети — исключение."""
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(TARGET, ignore_errors=True)
    TARGET.mkdir(parents=True)
    for name, expected in ARCHIVES.items():
        with zipfile.ZipFile(_fetch(name, expected)) as archive:
            archive.extractall(TARGET)
    if not (TARGET / "llama-server.exe").is_file():
        print("В архиве нет llama-server.exe", file=sys.stderr)
        return 1
    print(f"Готово: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
