# kernel — общие механизмы ядра: конфиг, логи (далее — шина, реестр, телеметрия)

## Ответственность
Механизмы, нужные всем слоям выше domain. Сейчас: загрузка и проверка конфигурации, настройка
структурных логов. В S-1.3: шина событий, реестр адаптеров, телеметрия. НЕ знает конкретных
секций конфига (их описывают модули, собирает `bootstrap.AppConfig`), не открывает файлы логов
(поток передаёт bootstrap), не импортирует ports/application/adapters/gateway/bootstrap.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `ConfigSection` | База секции: frozen, лишний ключ — ошибка; умолчаний в коде нет |
| `ConfigFiles` | Пути `default` (обязателен) и `user` (если есть) |
| `load_config(model, files, env)` | default < user < `VTUBER_<СЕКЦИЯ>__<ПОЛЕ>`; бросает `ConfigError` |
| `LoggingConfig` | Секция `[logging]`: `level` |
| `configure_logging(cfg, stream)` | JSON-строка на событие; вызывается один раз в bootstrap |
| `get_logger(name)` | Логгер с полем `logger` |
| `turn_context(turn_id)` | Все события в блоке (и созданных в нём задачах) несут `turn_id` |

## Зависимости
- domain: `ConfigError`, `TurnId` (ADR-0005)
- Внешние: pydantic, structlog (ADR-0006)

## События
- Публикует: — (MetricRecorded — S-1.3)
- Слушает: —

## Инварианты
- Сообщение `ConfigError` называет поле, полученное значение и источник: файл
  (`default.toml`/`user.toml`) или переменные `VTUBER_*`; для отсутствующего поля — default.toml.
- Имена переменных окружения без учёта регистра; значения приводятся pydantic (lax).
- Загруженный конфиг неизменяем.
- Событие лога ниже `level` отсекается до форматирования.

## Производительность
- Конфиг — только при старте. Лог — синхронная запись в поток: в горячем пути только DEBUG,
  выключенный по умолчанию (T-15).

## Как расширять
- Новая секция: класс-наследник `ConfigSection` в модуле-владельце, поле в `bootstrap.AppConfig`,
  значения — в `config/default.toml`, пример — в `config/user.example.toml`.
- Тесты: `tests/unit/kernel/`; валидность `default.toml` — `tests/unit/bootstrap/test_config.py`.

## Связанные документы
ADR-0005, ADR-0006, `docs/architecture.md` (Конфигурация, Телеметрия и логи), T-15
