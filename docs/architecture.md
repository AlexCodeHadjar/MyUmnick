# Архитектура

Источник: мастер-план v1, разделы 2.1, 2.4, 2.5, 4.1, 5, 6. Изменения — только через ADR
(`docs/adr/`). Код в этом документе — **эскизы**: контракт и идея, окончательная реализация
делается в сессии своего этапа по правилам `docs/rules/code-rules.md`.

## Подсистемы

«Витюбер с чатом» — пять подсистем и дирижёр между ними:

```text
┌──────────────────────────────────────────────────────────────────┐
│                       ДИРИЖЁР (оркестратор)                       │
│  принимает реплику → строит промпт → запускает конвейер ответа     │
│  → раздаёт текст, эмоции, звук → следит за отменой и метриками     │
└───────┬───────────┬────────────┬────────────┬────────────┬───────┘
   ┌────▼───┐  ┌────▼────┐  ┌────▼────┐  ┌────▼────┐  ┌────▼─────┐
   │  LLM   │  │  Голос  │  │  Аватар │  │   UI    │  │  Память  │
   │ (мозг) │  │TTS / STT│  │ Live2D  │  │  чат    │  │ кратк./  │
   │        │  │         │  │ липсинк │  │         │  │ долгоср. │
   └────────┘  └─────────┘  └─────────┘  └─────────┘  └──────────┘
```

Каждая подсистема — решённая задача (есть готовые движки). Сложность — в дирижёре: соединить их
так, чтобы задержки перекрывались, а не складывались (`docs/performance.md`).

## Ключевые решения

| Решение | ADR |
|---|---|
| Гексагональная архитектура ядра (порты и адаптеры), корень композиции | ADR-0001 |
| Три процесса: UI (Tauri), Ядро (Python asyncio), LLM-сервер (llama.cpp) | ADR-0002 |
| Звук воспроизводит UI, он же считает липсинк | ADR-0003 |
| Горячий путь — очереди; управляющие события — шина | этот документ |
| Стабильный префикс промпта для KV-кэша (T-03) | `docs/performance.md` |
| Единый источник схемы протокола: pydantic → JSON Schema → TypeScript | этот документ |
| Плагины через реестр и точки расширения, без правки ядра | этот документ |
| kernel может импортировать domain | ADR-0005 |
| Конфиг: pydantic + свой загрузчик TOML/env; логи: structlog | ADR-0006 |

Сознательно **не** делаем:

- тяжёлые LLM-фреймворки (цепочки, агенты «из коробки») в горячем пути — свой тонкий слой через
  порты, 200–300 строк, полностью под контролем;
- микросервисы — каждый лишний межпроцессный переход это сериализация и задержка;
- свой рендерер Live2D/VRM;
- дообучение модели, пока бенчмарки не покажут, что промпт + RAG исчерпаны;
- оптимизацию «на глаз» — только после замера и с замером после.

## Процессы

```text
┌─────────────────────────────┐   WebSocket (localhost)   ┌──────────────────────────────┐
│  UI-процесс (Tauri 2)       │ ◄──── JSON + бинарь ────► │  Ядро (Python 3.12, asyncio) │
│  ─ окно, чат (Svelte 5)     │                           │  ─ оркестратор, конвейер     │
│  ─ рендер Live2D (PixiJS)   │                           │  ─ память, промпты           │
│  ─ воспроизведение звука    │                           │  ─ TTS / STT (в потоках/     │
│  ─ липсинк (WebAudio)       │                           │    отдельных процессах)      │
└─────────────────────────────┘                           └──────────────┬───────────────┘
                                                                         │ HTTP + SSE
                                                                         │ (OpenAI-совместимый
                                                                         │  API, localhost)
                                                          ┌──────────────▼───────────────┐
                                                          │  LLM-сервер (llama.cpp       │
                                                          │  llama-server, CUDA)         │
                                                          └──────────────────────────────┘
```

Обоснование — ADR-0002.

## Принципы ядра

1. **Порты и адаптеры.** Ядро (домен + сценарии) определяет интерфейсы-порты, внешний мир
   подключается адаптерами.
2. **Правило зависимостей.** Только внутрь: adapters → application → ports → domain. Домен не
   импортирует ничего из проекта.
3. **Корень композиции.** Все объекты создаются и связываются в `bootstrap/container.py`.
   Нигде больше нет `SomeAdapter()` внутри бизнес-логики.
4. **Данные — очередями, управление — событиями.** Токены и аудио — `asyncio.Queue` (горячий
   путь ⏱). «Ход начался», «эмоция сменилась», «метрика записана» — шина событий.
5. **Всё асинхронно, отменяемо, измеряемо.** Блокирующее — только в `asyncio.to_thread`/процессах.
   Каждый ход — отменяемая задача, каждая стадия — спан телеметрии.
6. **Валидация на границах.** Конфиг, сообщения UI, ответы LLM валидируются один раз на входе;
   внутри домена данные уже корректны и не перепроверяются.

## Слои

```text
              ┌──────────────────────────────────────────────┐
              │ bootstrap   (сборка приложения, точка входа) │
              └──────────────────────┬───────────────────────┘
                 ┌───────────────────┴────────────────────┐
     ┌───────────▼───────────┐               ┌────────────▼───────────┐
     │ gateway               │               │ adapters               │
     │ WebSocket, протокол   │               │ llm / tts / stt / store│
     └───────────┬───────────┘               └────────────┬───────────┘
                 └───────────────────┬────────────────────┘
                         ┌───────────▼───────────┐
                         │ application           │
                         └───────────┬───────────┘
                         ┌───────────▼───────────┐
                         │ ports (Protocol-ы)    │
                         └───────────┬───────────┘
                         ┌───────────▼───────────┐
                         │ domain                │
                         └───────────────────────┘
   kernel (шина, реестр, телеметрия, конфиг-база) — доступен application, adapters, gateway,
   bootstrap; сам зависит только от domain (ADR-0005)
```

| Слой | Содержит | Может импортировать | Не может |
|---|---|---|---|
| domain | Неизменяемые сущности и значения: Message, Turn, Persona, Emotion, AudioChunk, доменные ошибки | stdlib | всё остальное |
| ports | Protocol-интерфейсы: LLMPort, TTSPort, STTPort, EmbedderPort, MemoryStorePort, ReplySink, ClockPort | domain | application, adapters, gateway, kernel |
| application | ConversationService, ReplyPipeline, PromptBuilder, SentenceChunker, StreamParser, MemoryService, IdleScheduler | ports, domain, kernel | adapters, gateway, внешние SDK |
| adapters | LlamaCppLLM, OpenAICompatLLM, SileroTTS, PiperTTS, FasterWhisperSTT, SqliteVecStore | ports, domain, kernel, внешние SDK | application, gateway, другие адаптеры |
| gateway | WebSocket-сервер, схема протокола, кодеки, WsReplySink | application, ports, domain, kernel | adapters |
| kernel | EventBus, Registry, telemetry, базовые классы конфига, логирование | stdlib, structlog, pydantic, domain (ADR-0005) | ports, application, adapters, gateway, bootstrap |
| bootstrap | container.py, main.py, AppConfig, загрузка плагинов | всё | — |

Проверяется `lint-imports` по контрактам в `.importlinter`; нарушение — красный CI.

## Карта модулей ядра

```text
vtuber/
├── domain/
│   ├── dialogue.py      Role, Message, Turn, Persona
│   ├── emotion.py       Emotion (Enum) и правила разбора тегов
│   ├── speech.py        AudioChunk, AudioFormat, Phrase
│   ├── events.py        TurnStarted, TurnFinished, TurnCancelled, EmotionChanged, ...
│   └── errors.py        VtuberError → LLMUnavailable, TTSFailed, ...
├── ports/
│   ├── llm.py           LLMPort, GenerationParams
│   ├── tts.py           TTSPort
│   ├── stt.py           STTPort
│   ├── memory.py        EmbedderPort, MemoryStorePort
│   └── sink.py          ReplySink (куда конвейер отдаёт результат)
├── application/
│   ├── conversation/    ConversationService — точка входа сценария «ход диалога»
│   ├── pipeline/        ReplyPipeline, SentenceChunker, StreamParser
│   ├── prompting/       PromptBuilder, ContextBudget
│   ├── memory/          ShortTermMemory, MemoryService, RetrievalGate
│   ├── speech/          нормализация текста для TTS
│   └── scheduler/       IdleScheduler — фоновые задачи в простое
├── adapters/
│   ├── llm/             llamacpp.py, openai_compat.py
│   ├── tts/             silero.py, piper.py
│   ├── stt/             faster_whisper.py
│   └── memory/          sqlite_vec.py, e5_embedder.py
├── gateway/
│   ├── protocol.py      pydantic-модели сообщений (источник истины протокола)
│   ├── codec.py         кодирование JSON/бинарных кадров
│   ├── sink.py          WsReplySink: ReplySink → WebSocket
│   ├── server.py        WebSocket-сервер, маршрутизация входящих
│   └── terminal.py      терминальный чат для вехи M1 (`python -m vtuber`)
├── kernel/
│   ├── bus.py           EventBus
│   ├── registry.py      Registry[A, T] — реестр адаптеров/плагинов
│   ├── context.py       turn_context, current_turn — текущий ход для логов и метрик
│   ├── telemetry.py     Telemetry.span(), TraceWriter
│   ├── config.py        ConfigSection, load_config (TOML + env)
│   └── logging.py       настройка structlog
└── bootstrap/
    ├── config.py        AppConfig — агрегирует секции модулей
    ├── container.py     сборка графа объектов
    ├── plugins.py       загрузка плагинов (entry points)
    └── main.py          точка входа
```

Актуальное состояние — в `docs/ai/PROJECT_MAP.md` (автогенерация).

## Поток данных одного хода

```text
UI: chat.send ──► gateway.server ──► ConversationService.handle(user_text)
                                         │
                                         ├─ отменить предыдущий ход (если идёт)
                                         ├─ bus.publish(TurnStarted)  ──► UI: аватар «думаю»
                                         ├─ RetrievalGate: нужен ли поиск? ──► MemoryService.recall()
                                         ├─ PromptBuilder.build(persona, history, facts, user_text)
                                         └─ ReplyPipeline.run(prompt, sink)
                                                │
             ┌──────────────────────────────────┼─────────────────────────────────┐
             ▼                                  ▼                                 ▼
   LLMPort.stream(prompt)            StreamParser                        SentenceChunker
   токены ─────────────────────────► текст / теги эмоций ──────────────► фразы
                                       │            │                        │
                                       ▼            ▼                        ▼
                               sink.text(delta)  sink.emotion(e)     очередь фраз
                                                                            │
                                                                            ▼
                                                                    TTSPort.synthesize(фраза)
                                                                            │
                                                                            ▼
                                                                    sink.audio(chunk) ──► UI
                                         │
                                         └─ по завершении: ShortTermMemory.append(turn),
                                            bus.publish(TurnFinished), IdleScheduler.touch()
```

## Порты (эскиз)

```python
# vtuber/ports/llm.py
"""Порт языковой модели: потоковая генерация и прогрев кэша."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from vtuber.domain.dialogue import Message


@dataclass(frozen=True, slots=True)
class GenerationParams:
    max_tokens: int = 256
    temperature: float = 0.7
    stop: tuple[str, ...] = ()


class LLMPort(Protocol):
    def stream(self, messages: list[Message], params: GenerationParams) -> AsyncIterator[str]:
        """Отдаёт текстовые дельты. Отмена задачи обязана закрыть поток генерации."""
        ...

    async def prefill(self, messages: list[Message]) -> None:
        """Прогревает KV-кэш без генерации (speculative prefill, T-05)."""
        ...
```

```python
# vtuber/ports/tts.py
"""Порт синтеза речи."""

from collections.abc import AsyncIterator
from typing import Protocol

from vtuber.domain.speech import AudioChunk, AudioFormat


class TTSPort(Protocol):
    @property
    def audio_format(self) -> AudioFormat: ...

    def synthesize(self, phrase: str) -> AsyncIterator[AudioChunk]:
        """Синтезирует фразу; движки со стримингом отдают несколько чанков."""
        ...
```

```python
# vtuber/ports/sink.py
"""Куда конвейер отдаёт результаты хода: WebSocket, файл или тест — конвейеру всё равно."""

from typing import Protocol

from vtuber.domain.emotion import Emotion
from vtuber.domain.speech import AudioChunk


class ReplySink(Protocol):
    async def text(self, delta: str) -> None: ...
    async def emotion(self, emotion: Emotion) -> None: ...
    async def audio(self, chunk: AudioChunk) -> None: ...
    async def done(self) -> None: ...
```

**Protocol, а не ABC:** структурная типизация — адаптеру не нужно наследоваться от класса ядра;
тестовые заглушки пишутся в три строки; `mypy --strict` проверяет совместимость.

## Конвейер ответа (эскиз)

```python
# vtuber/application/pipeline/reply_pipeline.py
"""Конвейер хода: LLM → разбор тегов → нарезка фраз → TTS. Стадии работают параллельно."""

import asyncio

from vtuber.application.pipeline.chunker import SentenceChunker
from vtuber.application.pipeline.stream_parser import StreamParser
from vtuber.domain import Message
from vtuber.kernel import Telemetry
from vtuber.ports import GenerationParams, LLMPort, ReplySink, TTSPort

_END = None  # маркер конца очереди фраз


class ReplyPipeline:
    def __init__(
        self, llm: LLMPort, tts: TTSPort, params: GenerationParams, telemetry: Telemetry
    ) -> None:
        self._llm = llm
        self._tts = tts
        self._params = params
        self._telemetry = telemetry

    async def run(self, messages: list[Message], sink: ReplySink) -> str:
        phrases: asyncio.Queue[str | None] = asyncio.Queue()
        async with asyncio.TaskGroup() as tg:
            text_task = tg.create_task(self._write(messages, sink, phrases))
            tg.create_task(self._speak(sink, phrases))
        await sink.done()
        return text_task.result()

    async def _write(
        self, messages: list[Message], sink: ReplySink, out: asyncio.Queue[str | None]
    ) -> str:
        parser, chunker = StreamParser(), SentenceChunker()
        with self._telemetry.span("llm.stream"):
            async for delta in self._llm.stream(messages, self._params):
                for event in parser.feed(delta):
                    await event.deliver(sink)
                    for phrase in chunker.feed(event.spoken_text):
                        out.put_nowait(phrase)
        if tail := chunker.flush():
            out.put_nowait(tail)
        out.put_nowait(_END)
        return parser.full_text

    async def _speak(self, sink: ReplySink, phrases: asyncio.Queue[str | None]) -> None:
        while (phrase := await phrases.get()) is not _END:
            with self._telemetry.span("tts.phrase"):
                async for chunk in self._tts.synthesize(phrase):
                    await sink.audio(chunk)
```

- `TaskGroup`: падение или отмена любой стадии отменяет все (T-14).
- TTS фразы N идёт параллельно с генерацией фразы N+1.
- Конвейер зависит только от портов — тестируется фейками без GPU.

## Нарезка фраз — SentenceChunker (эскиз)

```python
# vtuber/application/pipeline/chunker.py
"""Режет поток текста на фразы для TTS. Первая фраза отрезается раньше (T-02)."""

from collections.abc import Iterator
from dataclasses import dataclass

HARD_STOPS = frozenset(".!?…")
SOFT_STOPS = frozenset(",;:—")


@dataclass(slots=True)
class SentenceChunker:
    first_min_words: int = 4
    next_min_words: int = 10
    _buf: str = ""
    _emitted: int = 0

    def feed(self, text: str) -> Iterator[str]:
        self._buf += text
        while (cut := self._find_cut()) is not None:
            phrase, self._buf = self._buf[:cut].strip(), self._buf[cut:]
            if phrase:
                self._emitted += 1
                yield phrase

    def flush(self) -> str | None:
        phrase, self._buf = self._buf.strip(), ""
        return phrase or None

    def _find_cut(self) -> int | None:
        min_words = self.first_min_words if self._emitted == 0 else self.next_min_words
        for i, ch in enumerate(self._buf):
            followed_by_space = self._buf[i + 1 : i + 2].isspace()
            if ch == "\n" or (ch in HARD_STOPS and followed_by_space):
                return i + 1
            if ch in SOFT_STOPS and followed_by_space and len(self._buf[:i].split()) >= min_words:
                return i + 1
        return None
```

Требование «знак + пробел» не даёт резать `3.5`, `т.е.` и многоточие по частям (ценой ожидания
одного токена). Граничные случаи (сокращения, числа, кавычки, эмодзи) — тестами, в т.ч.
property-based (hypothesis): склейка всех фраз == исходный текст без лишних пробелов.

## Разбор эмоций в потоке — StreamParser

LLM вставляет теги эмоций прямо в текст: `<happy>Привет! Рада тебя видеть.` Отдельный
классификатор эмоций не нужен — экономия времени и VRAM ⏱.

Реализация — `application/pipeline/stream_parser.py`, один экземпляр на ход.

- Тег — только `<слово>` из латинских букв (`_` и пробелы у скобок допустимы); прочие `<` —
  обычный текст («3 < 5»). Тег может прийти разрезанным (`<ha` + `ppy>`): буфер держится, только
  пока видно незакрытое `<`, похожее на начало тега, и не дольше `HOLD_LIMIT` (32) символов.
- `feed(delta)` → события: `TextDelta(text, spoken_text)` и `EmotionCue(emotion)`; известные
  теги → `EmotionCue`, неизвестные выбрасываются (не показываются и не озвучиваются).
- `text` — для чата; `spoken_text` — для TTS: без тегов, эмодзи и знаков разметки.
- `flush()` в конце ответа: недописанный известный тег (`<hap`) выбрасывается, прочее — текст.
- `full_text` — для истории: текст и известные теги в нормализованном виде (`<happy>`), чтобы
  модель видела свои прошлые ответы с тегами и продолжала их ставить.
- У событий есть `spoken_text`; `deliver(sink)` появится вместе с портом `ReplySink` (S-3.4) —
  конвейер не ветвится по типам событий (полиморфизм вместо if/elif).

Формат тегов и список эмоций — только в `domain/emotion.py`; промпт персоны строится из того же
списка.

## Шина событий

Реализация — `kernel/bus.py` (`EventBus`). Не для горячего пути: токены и аудио идут очередями
(T-15).

- `subscribe(EventType, handler)`; `publish(event)` доставляет событие подписчикам его **точного**
  типа (не подклассов), параллельно, и ждёт всех.
- Ошибка подписчика логируется (`bus.handler_failed`) и не мешает ни остальным, ни издателю —
  плагин не уронит ход. Отмена `publish` отменяет подписчиков и пролетает дальше (R-38).

События — `dataclass(frozen=True, slots=True)` в `domain/events.py`: `TurnStarted`,
`TurnFinished`, `TurnCancelled`, `EmotionChanged`, `MetricRecorded`, `BackendStatusChanged`.
Подписчики — UI-шлюз, планировщик фона, запись трасс, плагины. Главный механизм расширения:
плагин реагирует на любое событие, не меняя ядро (OCP).

## Реестр адаптеров и плагинов

Реализация — `kernel/registry.py` (`Registry[A, T]`: имя → фабрика `A → T`, где `A` — то, что
передаёт bootstrap, обычно секция конфига).

- Реестр собирает bootstrap — строка на адаптер: `backends.add("llamacpp", LlamaCppLLM)`
  (`bootstrap.llm_backends`). Модульный изменяемый реестр нарушал бы R-04; декоратор mypy не
  типизирует без `Any` (R-18).
- Выбор по конфигу: `llm_backends().create(cfg.llm.backend, cfg.llm)`.
- Занятое имя → `ValueError`; неизвестное имя из конфига → `ConfigError` со списком доступных.

Сторонние плагины — через entry points (`[project.entry-points."vtuber.plugins"]`), их загружает
`bootstrap/plugins.py`.

## Телеметрия

Реализация — `kernel/telemetry.py`.

- `Telemetry(bus, clock)`: `span(name)` замеряет блок `with`, `record(name, ns)` — готовый замер
  (например, TTFT от начала хода). `turn_id` берётся из `kernel.context.current_turn()`.
- Запись — только `put_nowait` в ограниченную очередь (~1.3 мкс на span, R-08); при переполнении
  метрика теряется, ход продолжается. Блок, прерванный исключением или отменой, не пишется.
- `Telemetry.run()` — фоновая задача (владелец — TaskGroup в bootstrap): публикует
  `MetricRecorded` в шину. `TraceWriter(stream)` — подписчик, пишет `logs/traces.jsonl`.

## Корень композиции (эскиз)

```python
# vtuber/bootstrap/container.py
"""Единственное место, где создаются и связываются объекты приложения."""

from vtuber.adapters import LLM_REGISTRY, TTS_REGISTRY
from vtuber.application.conversation import ConversationService
from vtuber.application.pipeline import ReplyPipeline
from vtuber.application.prompting import PromptBuilder
from vtuber.bootstrap.config import AppConfig
from vtuber.kernel.bus import EventBus


def build_conversation(cfg: AppConfig, bus: EventBus) -> ConversationService:
    llm = LLM_REGISTRY.create(cfg.llm.backend, cfg.llm)
    tts = TTS_REGISTRY.create(cfg.tts.backend, cfg.tts)
    pipeline = ReplyPipeline(llm, tts, cfg.llm.generation)
    prompts = PromptBuilder(cfg.persona, cfg.context)
    return ConversationService(pipeline, prompts, bus)
```

Нигде, кроме bootstrap, адаптеры не создаются. Тесты собирают тот же граф из фейков.

## Конфигурация

`config/default.toml` (в репозитории) + `config/user.toml` (локальный, в `.gitignore`) +
переменные `VTUBER_<СЕКЦИЯ>__<ПОЛЕ>`. Приоритет: env > user > default (ADR-0006).

Целевой вид конфига (эскиз; секции появляются в `config/default.toml` вместе со своими модулями —
лишний ключ — ошибка старта):

```toml
[llm]
backend = "llamacpp"                 # llamacpp | openai_compat
base_url = "http://127.0.0.1:8080"
request_timeout_s = 30

[llm.generation]
max_tokens = 256
temperature = 0.7

[context]
max_history_tokens = 6000
trim_ratio = 0.5                     # T-04: отрезать половину истории за раз

[tts]
backend = "silero"                   # silero | piper | xtts
voice = "xenia"
device = "cpu"                       # T-11
sample_rate = 24000

[persona]
file = "personas/default.toml"

[gateway]
host = "127.0.0.1"
port = 8765

[telemetry]
traces_file = "logs/traces.jsonl"
```

Каждая секция — наследник `kernel.ConfigSection` в модуле, которому она нужна (адаптер Silero
сам описывает `SileroConfig`); `bootstrap.AppConfig` их только агрегирует. Умолчаний в коде нет —
только в `config/default.toml`. Ошибка в конфиге — `ConfigError` при старте с полем, значением
и источником, где исправить, а не падение посреди диалога.

## Протокол UI ↔ Ядро

Конверт JSON-сообщения:

```json
{ "v": 1, "type": "chat.delta", "turn": "t-000042", "data": { "text": "Привет" } }
```

UI → Ядро:

| type | data | Назначение |
|---|---|---|
| chat.send | `{ text }` | Новая реплика (отменяет текущий ход) |
| chat.cancel | `{}` | Остановить ответ |
| input.typing | `{ text }` | Черновик для speculative prefill (T-05), с дебаунсом |
| audio.played | `{ turn, seq }` | Подтверждение воспроизведения (метрика TTFA) |
| settings.get / settings.set | `{ … }` | Настройки |
| mic.frame | бинарный кадр | Аудио с микрофона (Этап 11) |

Ядро → UI:

| type | data | Назначение |
|---|---|---|
| turn.started | `{ turn }` | Аватар: «думаю» (T-17) |
| chat.delta | `{ text }` | Порция текста ответа |
| avatar.emotion | `{ emotion, intensity }` | Сменить выражение |
| audio.chunk | бинарный кадр | Звук |
| turn.finished / turn.cancelled | `{ turn, reason? }` | Конец хода |
| metrics.span | `{ name, ms }` | Панель метрик |
| status | `{ component, state }` | Состояние бэкендов |
| error | `{ code, message }` | Ошибка для пользователя |

Бинарный аудиокадр (без base64 — экономия ~33 % трафика и CPU ⏱):

```text
offset  size  поле
0       1     тип кадра (0x01 = audio)
1       1     версия
2       2     seq (uint16, LE)
4       4     sample_rate (uint32, LE)
8       8     turn_id (uint64, LE)
16      …     PCM s16le, mono
```

**Единый источник схемы.** Сообщения — pydantic-модели в `gateway/protocol.py`; полный
сгенерированный перечень — `docs/protocol.md`.
`tools/gen_protocol.py` генерирует JSON Schema → `ui/src/core/protocol.gen.ts` и
`docs/protocol.md`. Сгенерированное руками не правится; CI проверяет актуальность.

## Жизненный цикл хода и отмена

```text
          chat.send
 IDLE ─────────────────► THINKING ──первый токен──► SPEAKING ──звук закончился──► IDLE
  ▲                         │                          │
  │                         │ chat.cancel / chat.send  │ chat.cancel / chat.send / barge-in
  │                         ▼                          ▼
  └──────────────────── CANCELLED ◄────────────────────┘
```

- `ConversationService` хранит задачу текущего хода. Новый `chat.send` → `task.cancel()` →
  `TaskGroup` конвейера отменяет LLM-стрим (адаптер закрывает HTTP-соединение в `async with` —
  llama.cpp прекращает генерацию) и TTS → UI получает `turn.cancelled` и сбрасывает аудиобуфер.
- В историю попадает только произнесённая часть прерванного ответа (с пометкой), чтобы модель
  «знала», что её перебили.
- Состояние хода — явный Enum + таблица переходов; недопустимый переход — исключение.

## Фронтенд

```text
ui/src/
├── core/
│   ├── transport.ts         WebSocket-клиент: переподключение, очередь, разбор кадров
│   ├── protocol.gen.ts      сгенерированные типы протокола (не править)
│   └── store.ts             состояние приложения (Svelte runes)
├── features/
│   ├── chat/                список сообщений, ввод, батчинг токенов по кадрам (T-16)
│   ├── avatar/
│   │   ├── AvatarRenderer.ts    интерфейс рендера (load, setEmotion, setMouth, lookAt, update)
│   │   ├── live2d/              реализация для Live2D
│   │   └── vrm/                 реализация для VRM (позже)
│   ├── audio/               AudioWorklet-плеер, AnalyserNode → громкость → рот
│   ├── metrics/             панель задержек
│   └── settings/            окно настроек
└── app/
    ├── App.svelte           раскладка: чат слева, сцена справа
    └── main.ts
```

Фичи общаются через store и transport, а не импортируют друг друга. Аватар знает только
`AvatarRenderer` — смена Live2D на VRM не трогает чат и звук.

**Липсинк** (ADR-0003): плеер воспроизводит PCM через AudioWorklet, AnalyserNode раз в кадр
отдаёт RMS-громкость → сглаживание (attack/release) → `ParamMouthOpenY`. Позже — визем-липсинк
по фонемам (опция Этапа 8).

## Ошибки

- Иерархия: `VtuberError` → `BackendUnavailable` (`LLMUnavailable`, `TTSUnavailable`),
  `GenerationFailed`, `ConfigError`, `ProtocolError`.
- Адаптер переводит чужие исключения (`httpx.ConnectError`, ошибки torch) в доменные. Код выше
  адаптеров никогда не ловит `httpx.*`.
- Повторы — только в адаптерах и только для идемпотентных операций; в горячем пути — максимум
  1 быстрый повтор.
- Ошибка хода не роняет приложение: `ConversationService` превращает её в
  `turn.cancelled(reason)` + `error` в UI.
- `except Exception` — только на верхних границах (обработчик хода, WebSocket-сессия, фоновая
  задача), с логом и `turn_id`.

## Телеметрия и логи

- structlog → JSON в `logs/app.jsonl`; каждый лог несёт `turn_id` (contextvars).
- Метрики — `Telemetry` (раздел «Телеметрия»): `MetricRecorded` в шину, `TraceWriter` →
  `logs/traces.jsonl`.
- ERROR — сломалось; WARNING — деградация (TTFA выше бюджета, повтор); INFO — жизненный цикл;
  DEBUG — потоковые детали (выключено по умолчанию).

## Структура репозитория

```text
├── AGENTS.md / CLAUDE.md         инструкции для ИИ-ассистентов
├── README.md, CHANGELOG.md
├── pyproject.toml, uv.lock, .importlinter, .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── config/                       default.toml, user.example.toml (Этап 1)
├── personas/                     default.toml (Этап 3)
├── avatar/<model>/mapping.json   маппинг эмоций под модель (Этап 6)
├── models/                       веса моделей (в .gitignore, ИИ не читает)
├── scripts/                      запуск llama-server, загрузка моделей
├── tools/                        gen_map, check_file_length, gen_protocol, bench_latency, eval_quality
├── bench/                        prompts_ru.jsonl, baseline.json
├── eval/                         qa_ru.jsonl
├── src/vtuber/                   ядро; <пакет>/README.md — карточка модуля
├── tests/
│   ├── unit/                     зеркалит src/vtuber
│   ├── contract/                 общие тесты портов (LSP)
│   ├── integration/              с реальными бэкендами (@gpu, @slow)
│   ├── fakes/                    FakeLLM, FakeTTS, RecordingSink, FakeClock
│   └── tools/                    тесты скриптов tools/
├── ui/                           Tauri + Svelte (Этап 5)
└── docs/                         см. docs/README.md
```
