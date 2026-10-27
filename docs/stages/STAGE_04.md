# Этап 4 — Шлюз: WebSocket и протокол

## Цель
Ядро доступно UI через типизированный протокол.

## Зависимости
Этап 3.

## Критерии приёмки этапа
- [x] Задержка «сообщение от FakeLLM → кадр у клиента» ≤ 3 мс p95 (localhost) — тест.
- [x] Неверное сообщение клиента → `error` с кодом, соединение не рвётся.
- [ ] Сгенерированные TS-типы компилируются в `ui/` — проверить `tsc` на Этапе 5 (Node.js ещё не
      установлен); сейчас — тесты генератора и ручной просмотр файла.

## Сессии

### S-4.1 — Протокол и кодек
- **Цель:** pydantic-модели сообщений с версией протокола; кодек JSON и бинарных аудиокадров.
- **Scope:** `src/vtuber/gateway/protocol.py`, `gateway/codec.py`
- **Читать:** `docs/architecture.md` (Протокол UI ↔ Ядро)
- **Готово, когда:**
  - [x] Тесты: круговое кодирование всех типов; бинарный кадр по таблице смещений.
  - [x] Сообщения — те, что нужны сейчас; `input.typing`, `audio.played`, `settings.*`,
        `mic.frame` добавляются вместе с кодом, который их использует (Этапы 7, 9, 11).
  - [x] orjson не нужен: JSON сериализует и разбирает pydantic-core (нативный код).
- **Статус:** готова (журнал: `docs/ai/sessions/2026-10-27_S-4.1.md`)

### S-4.2 — Сервер и WsReplySink, e2e-тест
- **Цель:** WebSocket-сервер (один клиент; второй отклоняется или заменяет первого),
  маршрутизация в ConversationService, подписка на шину для `turn.*`, `status`, `metrics.span`;
  `WsReplySink`.
- **Scope:** `gateway/server.py`, `gateway/sink.py`, `tests/integration/`, ADR на websockets,
  режим сервера в `bootstrap/main.py`
- **Читать:** карточки `gateway`, `application/conversation`
- **Готово, когда:**
  - [x] e2e с FakeLLM: `chat.send` → `turn.started` → `chat.delta`… → `turn.finished`.
  - [x] Замер p95 ≤ 3 мс.
  - [x] Режим `python -m vtuber serve`: статус LLM, выход по концу stdin (sidecar Tauri).
- **Статус:** готова (журнал: `docs/ai/sessions/2026-10-27_S-4.2.md`)

### S-4.3 — Генератор TS-типов и docs/protocol.md
- **Цель:** `tools/gen_protocol.py`: JSON Schema → `ui/src/core/protocol.gen.ts` +
  `docs/protocol.md`; хук `--check` в pre-commit и CI.
- **Scope:** `tools/gen_protocol.py`, `docs/protocol.md`, `.pre-commit-config.yaml`, CI
- **Готово, когда:**
  - [x] Изменение модели без перегенерации роняет `--check` (проверено пробой и тестом).
  - [x] Хук `gen-protocol` в pre-commit и шаг CI.
- **Статус:** готова, кроме проверки `tsc` (журнал: `docs/ai/sessions/2026-10-27_S-4.3.md`)
