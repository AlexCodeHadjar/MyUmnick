# PROJECT MAP

> Автогенерация: `python tools/gen_map.py`. Не редактировать.

## src/vtuber
Ядро локального ИИ-витюбера.

## src/vtuber/adapters
Адаптеры: реализации портов для конкретных движков.

## src/vtuber/adapters/llm
Адаптеры языковых моделей (LLMPort).

## src/vtuber/adapters/memory
Адаптеры долговременной памяти: эмбеддеры и хранилища.

## src/vtuber/adapters/stt
Адаптеры распознавания речи (STTPort).

## src/vtuber/adapters/tts
Адаптеры синтеза речи (TTSPort).

## src/vtuber/application
Прикладной слой: сценарии диалога и конвейер ответа поверх портов.

## src/vtuber/bootstrap
Корень композиции: сборка графа объектов и точка входа.

- `AppConfig` — `src/vtuber/bootstrap/config.py:9` — Корень конфига. Только агрегирует: каждую секцию описывает модуль, которому она нужна.
- `load_app_config` — `src/vtuber/bootstrap/config.py:15` — Читает `config/default.toml` и `config/user.toml` из корня проекта `root` поверх `env`.

## src/vtuber/domain
Доменный слой: неизменяемые сущности и значения диалога, речи и эмоций.

- `Role` — `src/vtuber/domain/dialogue.py:11` — Автор сообщения; значения совпадают с ролями OpenAI-совместимого API.
- `Message` — `src/vtuber/domain/dialogue.py:20` — Одно сообщение контекста LLM.
- `Turn` — `src/vtuber/domain/dialogue.py:28` — Завершённый ход: реплика пользователя и ответ витюбера.
- `Persona` — `src/vtuber/domain/dialogue.py:42` — Характер витюбера, задаётся файлом `personas/*.toml` без правки кода (FR-11).
- `Emotion` — `src/vtuber/domain/emotion.py:10` — Единственный источник списка эмоций: из него строятся промпт персоны и разбор ответа.
- `parse_tag` — `src/vtuber/domain/emotion.py:31` — Возвращает эмоцию по тегу вида `<happy>` или None, если тег неизвестен или искажён.
- `VtuberError` — `src/vtuber/domain/errors.py:4` — Базовая ошибка приложения; сообщение говорит, что делать (R-45).
- `BackendUnavailable` — `src/vtuber/domain/errors.py:8` — Бэкенд не отвечает или не загружен.
- `LLMUnavailable` — `src/vtuber/domain/errors.py:12` — LLM-сервер недоступен.
- `TTSUnavailable` — `src/vtuber/domain/errors.py:16` — Движок синтеза речи недоступен.
- `GenerationFailed` — `src/vtuber/domain/errors.py:20` — Бэкенд ответил, но генерация сорвалась посреди хода.
- `ProtocolError` — `src/vtuber/domain/errors.py:24` — Сообщение от UI не соответствует протоколу.
- `ConfigError` — `src/vtuber/domain/errors.py:28` — Конфигурация не читается или не проходит проверку; приложение не стартует.
- `CancelReason` — `src/vtuber/domain/events.py:10` — Почему ход прерван.
- `Component` — `src/vtuber/domain/events.py:18` — Бэкенд, о состоянии которого сообщается в UI.
- `BackendState` — `src/vtuber/domain/events.py:25` — Состояние бэкенда для статус-бара UI.
- `TurnStarted` — `src/vtuber/domain/events.py:34` — Ход начат: аватар сразу показывает «думаю» (T-17).
- `TurnFinished` — `src/vtuber/domain/events.py:41` — Ход завершён полностью.
- `TurnCancelled` — `src/vtuber/domain/events.py:48` — Ход прерван; UI сбрасывает аудиобуфер.
- `EmotionChanged` — `src/vtuber/domain/events.py:56` — В ответе встретился тег эмоции.
- `BackendStatusChanged` — `src/vtuber/domain/events.py:64` — Бэкенд загрузился, упал или восстановился.
- `AudioFormat` — `src/vtuber/domain/speech.py:11` — Формат звука: PCM s16le, моно — так звук передаётся в UI (ADR-0003).
- `AudioChunk` — `src/vtuber/domain/speech.py:23` — Непрерывный фрагмент PCM в формате `format`.

## src/vtuber/gateway
Шлюз: WebSocket-сервер и протокол обмена с UI.

## src/vtuber/kernel
Общие механизмы ядра: шина событий, реестр, телеметрия, конфиг, логи.

- `ConfigSection` — `src/vtuber/kernel/config.py:21` — База секции конфига: неизменяема, лишний ключ — ошибка (опечатка не пройдёт молча).
- `ConfigFiles` — `src/vtuber/kernel/config.py:32` — Файлы конфигурации: `default` обязателен, `user` — если существует.
- `load_config` — `src/vtuber/kernel/config.py:45` — Собирает конфиг из файлов и окружения и проверяет его моделью `model`.
- `LoggingConfig` — `src/vtuber/kernel/logging.py:16` — Секция `[logging]`.
- `configure_logging` — `src/vtuber/kernel/logging.py:22` — Настраивает structlog: одна JSON-строка на событие в `stream`.
- `get_logger` — `src/vtuber/kernel/logging.py:42` — Логгер модуля; имя попадает в поле `logger` каждого события.
- `turn_context` — `src/vtuber/kernel/logging.py:48` — Все события внутри блока несут `turn_id`, включая задачи asyncio, созданные в нём.

## src/vtuber/ports
Порты: Protocol-интерфейсы, через которые ядро обращается к внешнему миру.
