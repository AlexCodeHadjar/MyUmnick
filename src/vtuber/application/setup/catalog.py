"""Что нужно приложению и что посоветовать этой машине (S-13.2): каталог и рекомендация."""

from dataclasses import dataclass

from pydantic import Field

from vtuber.domain import GpuMemory
from vtuber.kernel import ConfigSection


class CatalogFile(ConfigSection):
    """Файл компонента: откуда, куда (от корня) и как проверить; адрес закреплён на ревизии."""

    path: str
    url: str
    size: int = Field(gt=0)
    sha256: str = Field(pattern="^[0-9a-f]{64}$")


class CatalogItem(ConfigSection):
    """Компонент: модель или голос; `license` пользователь видит до согласия на загрузку.

    `min_vram_mb` — 0, если видеопамять не нужна; `required` — без него диалога не будет.
    """

    id: str
    title: str
    license: str
    required: bool
    min_vram_mb: int = Field(ge=0)
    files: tuple[CatalogFile, ...]

    @property
    def size(self) -> int:
        """Сколько скачивать, байт."""
        return sum(file.size for file in self.files)


class SetupCatalog(ConfigSection):
    """`config/catalog.toml`: компоненты, голоса Silero и основная LLM."""

    llm_item: str
    llm_model_path: str
    voices: tuple[str, ...]
    default_voice: str
    items: tuple[CatalogItem, ...]


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Совет этой машине; `warnings` показываются пользователю как есть."""

    item_ids: tuple[str, ...]
    voice: str
    warnings: tuple[str, ...]


def recommend(catalog: SetupCatalog, gpu: GpuMemory | None) -> Recommendation:
    """Всё, что помещается; обязательное советуется всегда, но с предупреждением."""
    total = None if gpu is None else gpu.total_mb
    chosen: list[str] = []
    warnings: list[str] = []
    if total is None:
        warnings.append(
            "Видеокарта NVIDIA не найдена. Модель запустится медленно или не запустится совсем."
        )
    for item in catalog.items:
        fits = total is None or item.min_vram_mb <= total
        if fits or item.required:
            chosen.append(item.id)
        if not fits and total is not None:
            warnings.append(
                f"«{item.title}» нужно {item.min_vram_mb} МБ видеопамяти, а на этой карте "
                f"{total} МБ: {_consequence(item)}"
            )
    return Recommendation(tuple(chosen), catalog.default_voice, tuple(warnings))


def _consequence(item: CatalogItem) -> str:
    if item.required:
        return "ответы будут медленными или модель не запустится."
    return "компонент можно поставить вручную, но он не советуется."
