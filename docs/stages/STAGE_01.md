# Этап 1 — Ядро (kernel + domain)

## Цель
Базовые кирпичи, от которых зависят все: доменные типы, конфиг, логи, телеметрия, шина событий,
реестр.

## Зависимости
Этап 0.

## Критерии приёмки этапа
- [ ] Все доменные типы неизменяемы (`frozen=True`), mypy strict зелёный, покрытие domain и
      kernel — 100 %.
- [ ] Ошибка в `config/user.toml` даёт сообщение с путём к полю и ожидаемым типом.
- [ ] `span()` замеряет с точностью до микросекунд и добавляет ≤ 5 мкс накладных расходов
      (микробенчмарк).

## Подводные камни
- Не тащить pydantic в domain (контракт `domain-pure`): доменные типы — чистые dataclass,
  pydantic только на границах (kernel/config, gateway).
- Telemetry публикует метрику, но kernel не может импортировать domain — решить в S-1.3 (ADR).

## Сессии

### S-1.1 — Доменные типы и ошибки
- **Цель:** `domain/` с Role, Message, Turn, Persona, Emotion, AudioFormat, AudioChunk,
  событиями (TurnStarted, TurnFinished, TurnCancelled, EmotionChanged, BackendStatusChanged)
  и иерархией ошибок.
- **Scope:** `src/vtuber/domain/`, `tests/unit/domain/`, карточка `domain/README.md`
- **Читать:** `docs/architecture.md` (слои, ошибки, StreamParser — про формат тегов эмоций)
- **Готово, когда:**
  - [x] Типы frozen+slots; Emotion — единственный источник списка эмоций и формата тега.
  - [x] Иерархия: VtuberError → BackendUnavailable (LLMUnavailable, TTSUnavailable),
        GenerationFailed, ProtocolError. ConfigError перенесён в S-1.2: kernel не может
        импортировать domain.
  - [x] Тесты: неизменяемость, разбор имени тега в Emotion.
- **Статус:** готова (журнал: `docs/ai/sessions/2026-10-27_S-1.1.md`)

### S-1.2 — Конфиг и логирование
- **Цель:** `AppConfig` из `config/default.toml` + `config/user.toml` + `VTUBER_*`
  (env > user > default) с понятными ошибками; structlog JSON с turn_id через contextvars.
- **Scope:** `src/vtuber/kernel/config.py`, `src/vtuber/kernel/logging.py`, `config/`,
  `tests/unit/kernel/`, ADR на зависимости (pydantic, pydantic-settings, structlog)
- **Читать:** `docs/architecture.md` (Конфигурация, Телеметрия и логи)
- **Готово, когда:**
  - [ ] Решено, где живёт ConfigError (kernel не импортирует domain): в kernel/config, либо
        ADR, разрешающий kernel → domain (тогда и MetricRecorded из S-1.3 — в domain).
  - [ ] Неверный тип в user.toml → ConfigError с путём к полю и ожидаемым типом.
  - [ ] `config/user.example.toml` в репозитории.
  - [ ] Лог содержит turn_id, выставленный в contextvar.
- **Статус:** не начата

### S-1.3 — Телеметрия, шина, реестр, фейки
- **Цель:** `span()`, `EventBus`, `Registry[T]`; фейки `RecordingSink`, `FakeClock`.
- **Scope:** `src/vtuber/kernel/telemetry.py`, `kernel/bus.py`, `kernel/registry.py`,
  `tests/fakes/`, `tests/unit/kernel/`, ADR по публикации метрик из kernel
- **Читать:** `docs/architecture.md` (Шина событий, Реестр, Телеметрия; открытый вопрос в «Слоях»)
- **Готово, когда:**
  - [ ] Решение «как span() публикует метрику без импорта domain» оформлено ADR.
  - [ ] Микробенчмарк: накладные расходы span() ≤ 5 мкс.
  - [ ] Registry: повторная регистрация и неизвестное имя — ошибки со списком доступных.
- **Статус:** не начата
