# kernel — общие механизмы ядра: конфиг, логи, контекст хода, шина, реестр, телеметрия

## Ответственность
Механизмы, нужные всем слоям выше domain. НЕ знает конкретных секций конфига (их описывают
модули, собирает `bootstrap.AppConfig`), не открывает файлы (потоки логов и трасс передаёт
bootstrap), не создаёт фоновых задач сам (`Telemetry.run` запускает владелец), не импортирует
ports/application/adapters/gateway/bootstrap.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `ConfigSection`, `ConfigFiles`, `load_config` | default < user < `VTUBER_<СЕКЦИЯ>__<ПОЛЕ>`; бросает `ConfigError` |
| `LoggingConfig`, `configure_logging`, `get_logger` | JSON-строка на событие; настройка один раз в bootstrap |
| `turn_context`, `current_turn` | Текущий ход для логов (`turn_id`) и метрик; наследуется задачами |
| `EventBus`, `Handler` | Шина управляющих событий: точный тип, параллельно, ошибки изолированы |
| `Registry[A, T]` | Имя → фабрика `A → T`; `add`, `create`; неизвестное имя → `ConfigError` |
| `Telemetry`, `Span`, `MAX_PENDING_METRICS` | `span(name)` / `record(name, ns)` → очередь → `run()` → шина |
| `TraceWriter` | Подписчик `MetricRecorded`: JSON-строка `{name, ns, turn_id}` в поток |

## Зависимости
- domain: `ConfigError`, `TurnId`, `MetricRecorded` (ADR-0005)
- Внешние: pydantic, structlog (ADR-0006)

## События
- Публикует: `MetricRecorded` (через `Telemetry.run`)
- Слушает: — (`TraceWriter` подписывает bootstrap)

## Инварианты
- `ConfigError` называет поле, значение и источник; загруженный конфиг неизменяем.
- `EventBus.publish`: ошибка подписчика логируется (`bus.handler_failed`) и не выходит наружу;
  `CancelledError` и прочие `BaseException` пролетают (R-38).
- `Span` пишет метрику только при нормальном выходе; прерванный исключением/отменой — нет.
- Очередь метрик ограничена `MAX_PENDING_METRICS`; при переполнении метрика теряется, ход — нет.
- `Telemetry` — только из потока event loop (asyncio.Queue не потокобезопасна).

## Производительность
- `span()` ≈ 1.2–1.5 мкс на замер (предел 5 мкс, `pytest -m slow`), `current_turn()` — чтение
  ContextVar. Публикация и запись трасс — вне горячего пути.
- Логи пишутся синхронно; в горячем пути — только DEBUG, выключенный по умолчанию (T-15).

## Как расширять
- Новая секция конфига: наследник `ConfigSection` в модуле-владельце + поле в `AppConfig` +
  значения в `config/default.toml`.
- Новый реестр бэкендов: `Registry[ConfigСекции, Порт]("kind")` рядом с портом/адаптерами;
  адаптер вызывает `add` в своём модуле.
- Тесты: `tests/unit/kernel/`; фейковые часы — `tests/fakes.FakeClock`.

## Связанные документы
ADR-0005, ADR-0006, `docs/architecture.md` (Шина, Реестр, Телеметрия, Конфигурация), T-15, R-08
