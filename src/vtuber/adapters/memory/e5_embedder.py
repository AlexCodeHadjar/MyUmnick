"""Эмбеддер multilingual-e5-small в ONNX на CPU (ADR-0015).

onnxruntime, tokenizers и numpy импортируются только при загрузке модели: пакет
`adapters.memory` (и хранилище) импортируется и без группы `memory`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path  # noqa: TC003 — pydantic разрешает аннотацию поля конфига в рантайме
from typing import TYPE_CHECKING, Protocol, Self

from pydantic import Field

from vtuber.domain import EmbedKind, MemoryUnavailable, Vector
from vtuber.kernel import ConfigSection

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType

    import numpy as np
    import numpy.typing as npt
    from tokenizers import Tokenizer

MODEL_FILE = "model.onnx"
TOKENIZER_FILE = "tokenizer.json"
# Предел длины входа у e5 (позиционные эмбеддинги XLM-R).
MAX_MODEL_TOKENS = 512


class E5Config(ConfigSection):
    """Настройки эмбеддера: каталог модели, её размерность, потоки CPU, длина и пакет."""

    model_dir: Path
    dimensions: int = Field(gt=0)
    threads: int = Field(gt=0)
    max_tokens: int = Field(gt=0, le=MAX_MODEL_TOKENS)
    batch_size: int = Field(gt=0)


class OnnxSession(Protocol):
    """То, что нужно от `onnxruntime.InferenceSession`: прогон по именам входов."""

    def run(
        self, output_names: None, input_feed: dict[str, npt.NDArray[np.int64]]
    ) -> list[npt.NDArray[np.float32]]:
        """Выходы модели по порядку; у e5 первый — `last_hidden_state`."""
        ...


class E5Embedder:
    """Реализует EmbedderPort; модель грузится один раз в `async with` (R-40).

    Модели нет — адаптер не падает при старте, а отвечает `MemoryUnavailable`: ход идёт без
    памяти, как без голоса при недоступном TTS.
    """

    def __init__(self, cfg: E5Config) -> None:
        self._cfg = cfg
        self._session: OnnxSession | None = None
        self._tokenizer: Tokenizer | None = None
        self._unavailable = "e5 не загружена: адаптер используется вне `async with`"

    async def __aenter__(self) -> Self:
        try:
            self._session, self._tokenizer = await asyncio.to_thread(self._load)
        except (OSError, RuntimeError, ValueError, ImportError) as error:
            self._unavailable = (
                f"Модель e5 не загрузилась из {self._cfg.model_dir}: {error}. Файлы "
                f"{MODEL_FILE} и {TOKENIZER_FILE} — из intfloat/multilingual-e5-small/onnx "
                "(ADR-0015)"
            )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._session = None
        self._tokenizer = None

    @property
    def dimensions(self) -> int:
        """Размерность векторов модели (у e5-small — 384)."""
        return self._cfg.dimensions

    async def embed(self, texts: Sequence[str], kind: EmbedKind) -> list[Vector]:
        """Векторы единичной длины по порядку; пакеты по `batch_size` — в потоке (R-34)."""
        session, tokenizer = self._session, self._tokenizer
        if session is None or tokenizer is None:
            raise MemoryUnavailable(self._unavailable)
        prefixed = [f"{kind.value}: {text}" for text in texts]
        step = self._cfg.batch_size
        vectors: list[Vector] = []
        for start in range(0, len(prefixed), step):
            batch = prefixed[start : start + step]
            vectors += await asyncio.to_thread(_encode, session, tokenizer, batch)
        return vectors

    def _load(self) -> tuple[OnnxSession, Tokenizer]:
        from tokenizers import Tokenizer  # noqa: PLC0415 — см. модуль

        model_dir = self._cfg.model_dir
        for name in (MODEL_FILE, TOKENIZER_FILE):
            if not (model_dir / name).is_file():
                msg = f"нет файла {model_dir / name}"
                raise FileNotFoundError(msg)
        session = _open_session(model_dir / MODEL_FILE, self._cfg.threads)
        tokenizer = Tokenizer.from_file(str(model_dir / TOKENIZER_FILE))
        tokenizer.enable_truncation(self._cfg.max_tokens)
        tokenizer.enable_padding()
        # Прогрев: первый прогон ONNX медленнее — платим при загрузке, а не в ходе (T-06).
        dims = len(_encode(session, tokenizer, ["query: привет"])[0])
        if dims != self._cfg.dimensions:
            msg = f"модель отдаёт векторы размерности {dims}, в конфиге — {self._cfg.dimensions}"
            raise ValueError(msg)
        return session, tokenizer


def _open_session(model: Path, threads: int) -> OnnxSession:
    # Типов у onnxruntime нет; нужное от сессии описано протоколом `OnnxSession`.
    import onnxruntime as ort  # type: ignore[import-untyped]  # noqa: PLC0415 — см. модуль

    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    try:
        session: OnnxSession = ort.InferenceSession(
            str(model), options, providers=["CPUExecutionProvider"]
        )
    # Ошибки onnxruntime (pybind) не наследуют OSError — переводятся на границе адаптера.
    except Exception as error:
        msg = f"onnxruntime не открыл модель {model}: {error}"
        raise RuntimeError(msg) from error
    return session


def _encode(session: OnnxSession, tokenizer: Tokenizer, texts: list[str]) -> list[Vector]:
    """Токены → скрытые состояния → среднее по маске → нормировка (как в карточке e5)."""
    import numpy as np  # noqa: PLC0415 — см. модуль

    encodings = tokenizer.encode_batch(texts)
    ids = np.array([e.ids for e in encodings], dtype=np.int64)
    mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
    feed = {"input_ids": ids, "attention_mask": mask, "token_type_ids": np.zeros_like(ids)}
    hidden = session.run(None, feed)[0]
    weights = mask[..., None].astype(np.float32)
    pooled = (hidden * weights).sum(axis=1) / np.maximum(weights.sum(axis=1), 1.0)
    unit = pooled / np.linalg.norm(pooled, axis=1, keepdims=True)
    return [tuple(float(x) for x in row) for row in unit]
