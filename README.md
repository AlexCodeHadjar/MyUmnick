# AI VTuber

Настольное приложение: справа — Live2D-модель витюбера, слева — чат. «Мозг» — локальная LLM
(llama.cpp), голос — локальный TTS. Работает офлайн. Главный приоритет — скорость ответа.

Статус: **Этап 0 — фундамент репозитория** (см. `docs/ai/STATE.md`).

## Требования

- Windows 10/11, Python 3.12, [uv](https://docs.astral.sh/uv/)
- Видеокарта NVIDIA с 8+ ГБ VRAM (рекомендуется 12–16 ГБ)

## Разработка

```bash
uv sync
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
