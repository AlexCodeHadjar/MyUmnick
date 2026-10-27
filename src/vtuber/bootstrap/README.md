# bootstrap — корень композиции: конфиг и персона (далее — сборка графа и точка входа)

## Ответственность
Единственное место, где создаются и связываются объекты приложения (ADR-0001), и граница
чтения файлов настроек. Сейчас: `AppConfig` — корень конфигурации; загрузка персоны из TOML.
Далее: `container.py` (S-3.5), `main.py`, загрузка плагинов (Этап 12). Бизнес-логики не
содержит.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `AppConfig` | Корень конфига: секции `logging`, `llm`, `persona`, `context` |
| `load_app_config(root, env)` | Читает `<root>/config/default.toml` и `user.toml` поверх `env` |
| `PersonaConfig` | Секция `[persona]`: `file` — путь к персоне относительно корня проекта |
| `load_persona(path)` | TOML персоны → доменная `Persona`; ошибки — `ConfigError` с путём |

## Зависимости
- kernel: `ConfigSection`, `ConfigFiles`, `load_config`, `LoggingConfig`
- adapters/llm: `LLMConfig`; application/prompting: `ContextConfig`
- domain: `Persona`, `Message`, `ConfigError`

## События
- Публикует: —
- Слушает: —

## Инварианты
- В `AppConfig` нет умолчаний: всё приходит из `config/default.toml`.
- `config/default.toml` и `personas/default.toml` всегда валидны (`tests/unit/bootstrap/`).
- Файл персоны: все ключи обязательны, кроме `[[examples]]`; лишний ключ — ошибка; `rules` не
  пуст. Примеры → пары `Message(user)`, `Message(assistant)`.

## Как расширять
- Новый модуль со своей секцией → поле в `AppConfig` + секция в `config/default.toml`.
- Новая персона — файл в `personas/` и путь в `[persona].file` (код не меняется, FR-11).

## Связанные документы
ADR-0001, ADR-0006, `docs/templates/persona.toml`
