"""Секция `[pipeline]`: настройки конвейера ответа."""

from vtuber.application.pipeline.chunker import ChunkerConfig
from vtuber.application.pipeline.filler import FillerConfig
from vtuber.kernel import ConfigSection


class PipelineConfig(ConfigSection):
    """Секция `[pipeline]`: нарезка фраз и междометия-заглушки."""

    chunker: ChunkerConfig
    filler: FillerConfig
