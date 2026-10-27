# ADR-0005: kernel может импортировать domain
- Статус: принято
- Дата: 2026-10-27
- Изменяет: таблицу слоёв ADR-0001 / `docs/architecture.md`

## Контекст
По исходной таблице слоёв kernel «не зависит ни от одного слоя проекта». Но kernel-механизмам
нужны доменные типы: `kernel/config` бросает `ConfigError`, `kernel/logging` привязывает
`TurnId`, `kernel/telemetry` (S-1.3) публикует `MetricRecorded`. Держать копии этих типов
в kernel — значит иметь два источника истины для ошибок и событий.

## Рассмотренные варианты
1. **Разрешить kernel → domain.** domain по контракту `domain-pure` не импортирует ничего из
   проекта, поэтому цикла нет. Ошибки и события остаются в одном месте.
2. **Типы в kernel** (ConfigError, MetricRecorded). Минусы: ошибка конфига вне иерархии
   `VtuberError`, события шины размазаны по двум пакетам.
3. **Колбэки/инъекция** (span() получает функцию публикации). Решает только телеметрию,
   не ConfigError; лишняя проводка.

## Решение
Вариант 1. kernel может импортировать domain, stdlib и свои внешние библиотеки (pydantic,
structlog). Запрещено по-прежнему: kernel → ports, application, adapters, gateway, bootstrap;
domain → kernel; ports → kernel.

## Последствия
- `.importlinter`: контракт `kernel-independent` больше не запрещает `vtuber.domain`.
- `ConfigError` и (в S-1.3) `MetricRecorded` живут в domain рядом с остальными ошибками/событиями.
- Граф слоёв: domain — общий словарь для всех, включая kernel.
