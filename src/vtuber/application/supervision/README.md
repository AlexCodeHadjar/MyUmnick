# application/supervision — самовосстановление

## Ответственность
Замечает падение и зависание компонентов и поднимает их заново с паузой и пределом попыток; сообщает пользователю.
Не знает, как устроен компонент: это `Supervised` из bootstrap. Ход не трогает: он сам заканчивается ошибкой.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `Supervisor(items, cfg, bus, sleep)`, `SupervisorConfig` | `run()`: задача на компонент; `[supervisor]` |
| `Supervised` | `component`, `healthy()`, `restart()` |
| `FailureFlag`, `WatchedTTS`, `WatchedSTT` | Обёртки голоса и слуха: `*Unavailable` или срок ожидания поднимают флаг |

## События
- Публикует: `BackendStatusChanged`, `BackendNotice`.

## Инварианты (`tests/unit/application/supervision/`)
- Одна неудачная проверка — ещё не сбой (`failures_to_restart`). Зависшая проверка — неудача.
- Попытки ограничены и не обнуляются успешным перезапуском: только `stable_s` без сбоев.
- После предела — `failed` и сообщение; вернулся сам — `ready`. Сбой перезапуска не роняет наблюдателя.

## Связанные документы
ADR-0021, `tests/integration/test_self_healing.py` (`-m slow`)
