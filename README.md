# AI VTuber

Настольное приложение: справа — Live2D-модель витюбера, слева — чат. «Мозг» — локальная LLM
(llama.cpp), голос — локальный TTS. Работает офлайн. Главный приоритет — скорость ответа.

Статус: **Этап 0 — фундамент репозитория** (см. `docs/ai/STATE.md`). Документация —
`docs/README.md`; лицензионные ограничения (Live2D, голоса) — `docs/licenses.md`.

## Требования

- Windows 10/11, Python 3.12, [uv](https://docs.astral.sh/uv/)
- Видеокарта NVIDIA с 8+ ГБ VRAM; эталон — RTX 5070 Ti 16 ГБ, 32 ГБ RAM

## Разработка

```bash
uv sync --all-extras
```

Голос Silero (ADR-0012): модель `v5_6_ru.pt` (148 МБ) — в `models/tts/silero/`:

```bash
curl -L -o models/tts/silero/v5_6_ru.pt --create-dirs https://models.silero.ai/models/tts/ru/v5_6_ru.pt
```

```bash
uv run pre-commit install
```

```bash
uv run pytest
```

```bash
uv run pre-commit run --all-files
```
