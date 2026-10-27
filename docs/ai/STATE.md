# STATE — снимок проекта
_Обновлено: 2026-10-27, сессия S-1.1_

## Сейчас
- Этап: 1 — Ядро: kernel + domain (docs/stages/STAGE_01.md)
- Следующая сессия: **S-1.2 — конфиг и логирование**
- Ветка: `main` (удалённого репозитория нет)

## Готово на этапе
- [x] S-1.1 Доменные типы и ошибки
- [ ] S-1.2 Конфиг и логирование
- [ ] S-1.3 Телеметрия, шина, реестр, фейки

## Последние метрики
Нет (горячего пути ещё нет).

## Открытые проблемы
- [P1] Лицензия Live2D: приложение, загружающее любые модели, — «Expandable Application»,
  публикация требует соглашения с Live2D даже для частных лиц (docs/licenses.md). ADR в S-6.1.
- [P2] Голоса: Silero — CC BY-NC; коммерчески чистые русские — Piper `denis`/`dmitri` (CC0).
- [P2] kernel не может импортировать domain, а ему нужны ConfigError (S-1.2) и MetricRecorded
  (S-1.3). Рекомендация: ADR-0005 «kernel → domain разрешён» — цикла нет, domain сам ничего не
  импортирует; правка `.importlinter` (`kernel-independent`) и таблицы слоёв. Альтернатива —
  держать эти типы в kernel.
- [P3] `tools/gen_map.py` не показывает модульные константы и `TurnId = NewType(...)` — только
  классы и функции.
- [P3] R-06 (импорт в обход `__init__`) не автоматизирован — только ревью.
- [P3] uv через `pip --user`: `C:\Users\Alast\AppData\Roaming\Python\Python312\Scripts` не в PATH.
- [P3] Node.js/pnpm не установлены — нужны с Этапа 5.

## Важно помнить
- Целевое железо: RTX 5070 Ti 16 ГБ VRAM, 32 ГБ RAM (Blackwell → llama.cpp с CUDA 12.8+).
- Импорт из domain — только `from vtuber.domain import X` (R-06); новые публичные имена — в
  `__all__`, иначе падает `tests/unit/domain/test_package.py`.
- Каждая новая зависимость — ADR (S-1.2: pydantic, pydantic-settings, structlog). ADR-0004
  зарезервирован за выбором LLM (S-2.5); следующий свободный — ADR-0005.
- Карточку модуля (`docs/templates/MODULE_CARD.md`) создавать вместе с первым кодом пакета.

## Последний журнал
docs/ai/sessions/2026-10-27_S-1.1.md
