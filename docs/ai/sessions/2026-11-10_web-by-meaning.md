# Плагин web_search: погода, новости и поиск по смыслу реплики · 2026-11-10

## Сделано
- `intent.py`: `classify(text, auto)` → `Weather` / `News` / `Search` / None; ru и en; `auto=false` — только явная
  просьба (как в ADR-0022).
- `weather.py`: Open-Meteo (геокодер + прогноз), варианты падежа города («Москве» → «Москва»), текст ru/en; источник
  «Open-Meteo» в чате.
- `news.py`: SearXNG `categories=news`, `time_range=day`, язык издания; текст первой статьи через trafilatura в
  потоке; атаки отбрасываются, текст обрезается.
- `__init__.py`: настройки `auto`, `weather`, `home_city`, `geocoding_url`, `forecast_url`, `read_pages`,
  `max_article_chars`; `languages = ("ru", "en")`; два HTTP-клиента (localhost без проверки TLS, внешние — с ней);
  срок инструмента `2 × timeout_s + 1`.
- Группа `web` (`trafilatura>=2.3,<3`), ADR-0036, `docs/licenses.md`, README плагина.

## Проверки
- `tests/plugins/test_web_search_auto.py` на локальной заглушке Open-Meteo, SearXNG и сайта: «Какая сегодня погода
  в Москве?» → цифры прогноза и источник; «What's the news about AI?» → выдача и текст статьи; обычная реплика — ни
  одного запроса. Старые тесты — с `auto=False`.
- pre-commit зелёный, pytest — 1281 (один разовый сбой при параллельной работе другой сессии не повторился).
- Не проверено: настоящие Open-Meteo, SearXNG и новостные сайты.
