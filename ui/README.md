# ui — окно приложения: чат слева, сцена справа (Tauri 2 + Svelte 5)

## Ответственность
Показывает чат и сцену с моделью, говорит с ядром по WebSocket (`ws://127.0.0.1:8765`,
протокол — `docs/protocol.md`). Логики диалога и LLM здесь нет: всё решает ядро. Оболочка Rust
(`src-tauri/`) только открывает окно; ядро как sidecar — S-13.1 (ADR-0009).

## Структура
| Путь | Назначение |
|---|---|
| `src/app/` | `main.ts` (монтирование), `App.svelte` (раскладка) |
| `src/core/protocol.gen.ts` | типы протокола — генерирует `tools/gen_protocol.py`, не править |
| `src/core/` | transport и store — S-5.2 |
| `src/features/` | chat (S-5.3), metrics (S-5.4), avatar (Этап 6), audio (Этап 8) |
| `src-tauri/` | оболочка Tauri: `tauri.conf.json`, права окна в `capabilities/` |

## Команды (из `ui/`)
- `pnpm install` — зависимости; `pnpm tauri dev` — окно с горячей перезагрузкой.
- `pnpm lint`, `pnpm check` (svelte-check), `pnpm format:check`, `pnpm build`.
- Ядро в разработке — отдельно: `uv run python -m vtuber serve` из корня.

## Инварианты
- tsconfig строгий (R-61); `any` и `as` — ошибки eslint (R-62); фичи не импортируют друг
  друга (R-63); типы сообщений — только из `protocol.gen.ts` (R-64).
- У каждого компонента есть `<script lang="ts">`, хоть и пустой: иначе svelte-check 4.7 не
  выдаёт типы модуля (ADR-0009).
- CSP окна пускает сеть только на `ws://127.0.0.1:*`.

## Производительность
- Токены в DOM — батчем раз в кадр (T-16, R-65); бюджет «ядро → экран» — ≤ 20 мс сверх TTFT.

## Связанные документы
ADR-0002, ADR-0003, ADR-0009; `docs/architecture.md` (Фронтенд); правила J (R-61…R-67)
