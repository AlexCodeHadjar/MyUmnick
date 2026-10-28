"""Секция `[tts]`: какой движок говорит и настройки каждого (ADR-0012, ADR-0013)."""

from pathlib import Path

from pydantic import Field

from vtuber.adapters.tts.piper import PiperConfig
from vtuber.adapters.tts.silero import SileroConfig
from vtuber.kernel import ConfigSection


class TTSConfig(ConfigSection):
    """Секция `[tts]`.

    `backend` — имя движка из реестра bootstrap (`silero`, `piper`) или `none` — без голоса.
    Пути к моделям в конфиге — относительно корня проекта (`resolved`).
    """

    backend: str = Field(min_length=1)
    silero: SileroConfig
    piper: PiperConfig

    def resolved(self, root: Path) -> "TTSConfig":
        """Копия с путями моделей от корня проекта: запуск не зависит от текущего каталога."""
        return self.model_copy(
            update={
                "silero": self.silero.model_copy(
                    update={"model_path": root / self.silero.model_path}
                ),
                "piper": self.piper.model_copy(update={"model_path": root / self.piper.model_path}),
            }
        )
