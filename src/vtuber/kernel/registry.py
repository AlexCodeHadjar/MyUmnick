"""Реестр фабрик по имени: реализация порта выбирается строкой в конфиге (OCP)."""

from collections.abc import Callable

from vtuber.domain import ConfigError


class Registry[A, T]:
    """Имя → фабрика `A → T`; например, `Registry[TTSConfig, TTSPort]` для движков TTS.

    Адаптер регистрирует себя одной строкой в своём модуле (`TTS.add("silero", SileroTTS)`),
    bootstrap создаёт выбранный по конфигу: `TTS.create(cfg.tts.backend, cfg.tts)`.
    """

    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._factories: dict[str, Callable[[A], T]] = {}

    def add(self, name: str, factory: Callable[[A], T]) -> None:
        """Регистрирует фабрику (функцию или класс) под `name`.

        Raises:
            ValueError: имя уже занято — два адаптера или плагина конфликтуют.

        """
        if name in self._factories:
            msg = f"{self._kind} '{name}' уже зарегистрирован — переименуйте один из адаптеров"
            raise ValueError(msg)
        self._factories[name] = factory

    def create(self, name: str, arg: A) -> T:
        """Создаёт объект фабрикой `name`.

        Raises:
            ConfigError: имя не зарегистрировано; сообщение перечисляет доступные.

        """
        try:
            factory = self._factories[name]
        except KeyError:
            known = ", ".join(sorted(self._factories))
            msg = f"Неизвестный {self._kind} '{name}' в конфиге. Доступны: {known}"
            raise ConfigError(msg) from None
        return factory(arg)
