# bootstrap — корень композиции: конфиг приложения (далее — сборка графа и точка входа)

## Ответственность
Единственное место, где создаются и связываются объекты приложения (ADR-0001). Сейчас:
`AppConfig` — корень конфигурации, агрегирующий секции модулей. Далее: `container.py` (S-3.5),
`main.py`, загрузка плагинов (Этап 12). Бизнес-логики не содержит.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `AppConfig` | Корень конфига: поле на каждую секцию модуля (сейчас `logging`) |
| `load_app_config(root, env)` | Читает `<root>/config/default.toml` и `user.toml` поверх `env` |

## Зависимости
- kernel: `ConfigSection`, `ConfigFiles`, `load_config`, `LoggingConfig`

## События
- Публикует: —
- Слушает: —

## Инварианты
- В `AppConfig` нет умолчаний: всё приходит из `config/default.toml`.
- `config/default.toml` всегда валиден (`tests/unit/bootstrap/test_config.py`).

## Как расширять
- Новый модуль со своей секцией → поле в `AppConfig` + секция в `config/default.toml`.

## Связанные документы
ADR-0001, ADR-0006
