# ADR-0009: инструменты UI — Tauri 2, Svelte 5, Vite 8, TypeScript 6.0, pnpm; sidecar — позже
- Статус: принято
- Дата: 2026-10-27

## Контекст
Стек окна выбран в ADR-0002 и `docs/stack.md`: Tauri 2 + Svelte 5 + TypeScript + Vite. В S-5.1
нужно зафиксировать конкретные версии, менеджер пакетов, линтеры и то, как окно получает ядро.
Строгость TS — R-61/R-62. Хуки и CI должны проверять `ui/` так же, как Python-часть.

## Рассмотренные варианты
Менеджер пакетов: **pnpm** (строгие `node_modules`, общий стор, политика `minimumReleaseAge`) против
npm (плоские `node_modules`: импорт непрямой зависимости проходит молча).

TypeScript: **6.0** против 5.9. typescript-eslint 8 поддерживает TS < 6.1, svelte-check 4 — 6.0.

Ядро в окне: **sidecar сейчас** (сборка ядра в exe, `tauri-plugin-shell`) против **отдельного
запуска в разработке** (`uv run python -m vtuber serve` в своём терминале).

## Решение
- Tauri 2.12 (`tauri`, `tauri-build`, `@tauri-apps/cli`, `@tauri-apps/api`), Svelte 5, Vite 8,
  `@sveltejs/vite-plugin-svelte` 7, TypeScript `~6.0`, svelte-check 4.
- eslint 10 (flat config) + typescript-eslint 8 `strictTypeChecked` + eslint-plugin-svelte;
  prettier 3 + prettier-plugin-svelte. `no-explicit-any` и запрет `as` — ошибки (R-62).
- pnpm 12, версия закреплена полем `packageManager`; Node ≥ 24. Политика pnpm
  `minimumReleaseAge` не отключается: свежие (< суток) релизы не ставятся — защита от
  отравленных публикаций.
- Ядро в разработке запускается отдельно; окно подключается к `ws://127.0.0.1:8765`. Sidecar
  (ядро как exe + `tauri-plugin-shell`) — в S-13.1 вместе с упаковкой: до неё собирать ядро в
  exe не из чего. Ядро уже готово к роли sidecar: `serve` завершается по EOF в stdin.
- CSP окна: `connect-src 'self' ws://127.0.0.1:*` — только локальное ядро.

## Последствия
- Хуки pre-commit `ui-eslint`, `ui-prettier`, `ui-svelte-check`, `ui-cargo-fmt`; в CI — job `ui`
  (pnpm `--frozen-lockfile`, сборка фронтенда, `cargo fmt`, `cargo clippy -D warnings`).
- Для сборки окна на машине нужны Rust (MSVC) и Visual C++ Build Tools; WebView2 есть в Windows 11.
- svelte-check 4.7 не выдаёт типы компонента без блока `<script>` (TS7016 у импортирующего
  модуля) — у каждого компонента есть `<script lang="ts">`, хоть и пустой.
- Обновление TypeScript до 6.1+ — после поддержки в typescript-eslint.
