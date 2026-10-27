# Этап 4 — Шлюз: WebSocket и протокол

## Цель
Ядро доступно UI через типизированный протокол.

## Зависимости
Этап 3.

## Критерии приёмки этапа
- [ ] Задержка «сообщение от FakeLLM → кадр у клиента» ≤ 3 мс p95 (localhost).
- [ ] Неверное сообщение клиента → `error` с кодом, соединение не рвётся.
- [ ] Сгенерированные TS-типы компилируются в `ui/`.

## Сессии

### S-4.1 — Протокол и кодек
- **Цель:** pydantic-модели всех сообщений с версией протокола; кодек JSON (orjson) и бинарных
  аудиокадров.
- **Scope:** `src/vtuber/gateway/protocol.py`, `gateway/codec.py`, ADR на orjson/websockets
- **Читать:** `docs/architecture.md` (Протокол UI ↔ Ядро)
- **Готово, когда:**
  - [ ] Тесты: круговое кодирование всех типов; бинарный кадр по таблице смещений.
- **Статус:** не начата

### S-4.2 — Сервер и WsReplySink, e2e-тест
- **Цель:** WebSocket-сервер (один клиент; второй отклоняется или заменяет первого),
  маршрутизация в ConversationService, подписка на шину для `turn.*`, `status`, `metrics.span`;
  `WsReplySink`.
- **Scope:** `gateway/server.py`, `gateway/sink.py`, `tests/integration/`
- **Читать:** карточки `gateway`, `application/conversation`
- **Готово, когда:**
  - [ ] e2e с FakeLLM: `chat.send` → `turn.started` → `chat.delta`… → `turn.finished`.
  - [ ] Замер p95 ≤ 3 мс.
- **Статус:** не начата

### S-4.3 — Генератор TS-типов и docs/protocol.md
- **Цель:** `tools/gen_protocol.py`: JSON Schema → `ui/src/core/protocol.gen.ts` +
  `docs/protocol.md`; хук `--check` в pre-commit и CI.
- **Scope:** `tools/gen_protocol.py`, `docs/protocol.md`, `.pre-commit-config.yaml`, CI
- **Готово, когда:**
  - [ ] Изменение модели без перегенерации роняет `--check`.
- **Статус:** не начата
