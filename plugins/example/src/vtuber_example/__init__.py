"""Плагин-пример (docs/plugins.md): реакция на событие и своя секция конфига без правки ядра."""

from vtuber.domain import TurnFinished
from vtuber.kernel import ConfigSection, PluginContext


class ExampleConfig(ConfigSection):
    """Секция `[plugins.settings.example]`."""

    label: str


class ExamplePlugin:
    """После каждого законченного хода пишет в лог, сколько их было."""

    name = "example"

    def __init__(self) -> None:
        self._ctx: PluginContext | None = None
        self._label = ""
        self._turns = 0

    async def setup(self, ctx: PluginContext) -> None:
        """Прочитать настройки и подписаться на конец хода."""
        self._ctx = ctx
        self._label = ctx.settings(ExampleConfig).label
        ctx.subscribe(TurnFinished, self._on_turn)

    async def shutdown(self) -> None:
        """Запущенного в фоне нет: только итог в лог."""
        if self._ctx is not None:
            self._ctx.log.info("example.total", label=self._label, turns=self._turns)

    async def _on_turn(self, event: TurnFinished) -> None:
        self._turns += 1
        if self._ctx is not None:
            self._ctx.log.info("example.turn", label=self._label, turn=str(event.turn_id))
