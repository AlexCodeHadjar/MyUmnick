# application/language — языковые пакеты изданий: что в ядре зависит от языка

## Ответственность
Собирает в один неизменяемый `LanguagePack` тексты и правила, которые зависят от языка издания
(Этап 20, ADR-0032): рамку промпта и служебные реплики, тексты фоновой памяти и гейт поиска, дикцию
голоса. Сами тексты живут рядом со своими модулями (`prompting/texts.py`, `memory/texts.py`,
`speech/diction.py`); пакет их только связывает. Пакет выбирает bootstrap (`language_pack`).

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `LanguagePack(language, prompt, memory, diction)` | Пакет одного языка |
| `RU_PACK`, `EN_PACK` | Русский (байт в байт прежние тексты, `tests/golden/ru_texts.json`) и английский |

## Зависимости
- application: `prompting`, `memory`, `speech`

## События
- Публикует: —
- Слушает: —

## Инварианты
- Русский пакет совпадает с эталоном `tests/golden/ru_texts.json` (`test_golden_ru.py`).
- Пакет выбирается один раз при сборке объектов: в горячем пути проверок языка нет.

## Как расширять
- Новый язык: тексты в `texts.py` модулей, дикция в `speech/`, пакет здесь, строка в
  `bootstrap.edition.language_pack`, тесты как `tests/unit/application/language/test_english_pack.py`.

## Связанные документы
ADR-0032, `docs/stages/STAGE_20.md`
