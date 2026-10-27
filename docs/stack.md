# Технологический стек

Источник: мастер-план v1, разделы 4.2–4.3. Новая зависимость — только через ADR.
Лицензии компонентов — `docs/licenses.md`.

| Область | Основной выбор | Альтернативы | Обоснование |
|---|---|---|---|
| Язык ядра | Python 3.12 | — | Экосистема ИИ; TaskGroup, современные дженерики |
| Менеджер пакетов | uv | poetry | Быстрый, lock-файл, управление версиями Python |
| Асинхронность | asyncio | trio | Стандарт, совместим со всеми библиотеками |
| HTTP-клиент к LLM | httpx (async, stream) | aiohttp | Чистый API стриминга, тайм-ауты, пул соединений |
| WebSocket-сервер | websockets | Starlette | Минимум накладных расходов |
| Валидация/конфиг | pydantic v2 + свой загрузчик TOML/env (ADR-0006) | pydantic-settings, msgspec | Валидация на границах, JSON Schema, ошибка с источником значения |
| Сериализация | orjson | stdlib json | В разы быстрее stdlib ⏱ |
| Логи | structlog (JSON, ADR-0006) | stdlib logging | Структурированные логи с turn_id |
| LLM-рантайм | llama.cpp (llama-server) | Ollama, LM Studio, vLLM, TabbyAPI | Контроль KV-кэша, speculative decoding, flash attention, слоты |
| Формат модели | GGUF Q4_K_M / Q5_K_M | EXL2 (TabbyAPI) | Баланс скорость/качество; выбор — бенчмарком |
| Размер модели | 7–14B instruct с сильным русским | 3–4B для слабого железа | Отбор на Этапе 2 по «скорость × качество» |
| TTS (быстрый) | Silero TTS (ru) или Piper (ru, ONNX) | — | CPU, реальное время, русские голоса ⏱ — **см. лицензии** |
| TTS (качественный) | XTTS-v2 / F5-TTS (опция) | CosyVoice и др. | Клонирование голоса, выше качество; GPU, медленнее |
| STT | faster-whisper + Silero VAD | Vosk, GigaAM | Качество + скорость на GPU/CPU |
| Эмбеддинги | multilingual-e5-small | bge-m3 | Быстро на CPU, русский |
| Векторное хранилище | SQLite + sqlite-vec | hnswlib, FAISS | Один файл, транзакции, факты и векторы вместе |
| UI-оболочка | Tauri 2 | Electron | Лёгкий, sidecar для ядра |
| UI-фреймворк | Svelte 5 + TypeScript + Vite | React, Solid | Минимум шаблонного кода, быстрый DOM |
| Аватар | Live2D Cubism: PixiJS + pixi-live2d-display | VRM: three.js + @pixiv/three-vrm | Самый распространённый формат витюберов — **см. лицензии** |
| Звук в UI | WebAudio (AudioWorklet, AnalyserNode) | — | Точное воспроизведение и анализ громкости |
| Качество Python | ruff, mypy --strict, import-linter, pytest, pytest-asyncio, hypothesis | pyright | Линт + типы + архитектурные контракты |
| Качество TS | eslint (strict), prettier, svelte-check, vitest | biome | Строгий TS без any |
| Хуки и CI | pre-commit, GitHub Actions | — | Нарушения ловятся до коммита |

## Версии

Все версии фиксируются в lock-файлах (`uv.lock`, `pnpm-lock.yaml`). У pixi-live2d-display есть
ограничения совместимости с мажорными версиями PixiJS — связка выбирается и фиксируется на
Этапе 6 после проверки (ADR), а не берётся «последняя». Сборка llama-server для RTX 5070 Ti
(Blackwell) — с CUDA 12.8+.

## Альтернатива: всё на Python

UI на PySide6 (Qt) с моделью в QWebEngineView или через нативные биндинги Live2D. Плюс — один
язык. Минусы — сложнее и медленнее UI, хуже инструменты веб-рендера аватара, тяжёлый Qt WebEngine.
Выбран Tauri; ядро от выбора UI не зависит — протокол WebSocket одинаков для любого клиента.
