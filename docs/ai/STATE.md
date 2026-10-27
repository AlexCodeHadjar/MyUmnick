# STATE — снимок проекта
_Обновлено: 2026-10-27, сессия S-1.2_

## Сейчас
- Этап: 1 — Ядро: kernel + domain (docs/stages/STAGE_01.md)
- Следующая сессия: **S-1.3 — телеметрия, шина, реестр, фейки**
- Ветка: `main` (удалённого репозитория нет)

## Готово на этапе
- [x] S-1.1 Доменные типы и ошибки
- [x] S-1.2 Конфиг и логирование
- [ ] S-1.3 Телеметрия, шина, реестр, фейки

## Последние метрики
Нет (горячего пути ещё нет).

## Открытые проблемы
- [P1] Лицензия Live2D: приложение, загружающее любые модели, — «Expandable Application»,
  публикация требует соглашения с Live2D даже для частных лиц (docs/licenses.md). ADR в S-6.1.
- [P2] Голоса: Silero — CC BY-NC; коммерчески чистые русские — Piper `denis`/`dmitri` (CC0).
- [P3] Никто ещё не вызывает `configure_logging` и не открывает `logs/app.jsonl` — это
  `bootstrap/main.py` (S-3.5); поле `logging.file` добавить тогда же.
- [P3] Текст ошибок pydantic в `ConfigError` — на английском («Input should be…»), обвязка — на
  русском. Перевод — только если будет мешать.
- [P3] `tools/gen_map.py` не показывает модульные константы и `TurnId = NewType(...)`.
- [P3] R-06 (импорт в обход `__init__`) не автоматизирован — только ревью.
- [P3] uv через `pip --user`: `C:\Users\Alast\AppData\Roaming\Python\Python312\Scripts` не в PATH.
- [P3] Node.js/pnpm не установлены — нужны с Этапа 5.

## Важно помнить
- Целевое железо: RTX 5070 Ti 16 ГБ VRAM, 32 ГБ RAM (Blackwell → llama.cpp с CUDA 12.8+).
- kernel → domain разрешён (ADR-0005); `MetricRecorded` — в `domain/events.py`.
- Умолчаний конфига в коде нет: новая секция = класс `ConfigSection` в модуле + поле в
  `bootstrap.AppConfig` + значения в `config/default.toml` (ADR-0006).
- Импорт — `from vtuber.<пакет> import X` (R-06); новые публичные имена — в `__all__`.
- ADR-0004 зарезервирован за выбором LLM (S-2.5); следующий свободный — ADR-0007.

## Последний журнал
docs/ai/sessions/2026-10-27_S-1.2.md
