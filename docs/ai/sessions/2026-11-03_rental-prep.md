# Подготовка к аренде: S-9.1, S-9.3, S-12.5, S-12.6, S-18.1 · 2026-11-03

## Сделано
- `scripts/remote/models_extra.tsv`: пять кандидатов кода, `mmproj` и черновик MTP, с закреплёнными ревизиями, размером и sha256 из API Hugging Face.
- `scripts/remote/run_my_set.sh`: шаги `profile`, `speed`, `vision`, `code`, `assistant`, с возобновлением.
- `tools/bench_vision.py`, `tools/check_assistant.py`, скорость и `--out` в `tools/eval_code.py`.

## Решения
- S-9.3: черновик MTP из репозитория основной модели (253 МБ), а не отдельная модель семейства (Gemma 4 E2B — 3 ГБ видеопамяти). `n-max 2`: при 3 в llama.cpp замечен другой вывод.
- S-12.5: Qwen2.5-Coder 7B и Granite 4.2 8B могут встать рядом с основной; Qwen2.5-Coder 14B, gpt-oss 20B и Devstral Small 2 24B — только вместо неё. Все Q4_K_M, веса под Apache 2.0.
- Отдельный список: `run_candidates.sh` идёт по всем строкам `models.tsv`.

## Не проверено
- Скрипт прогона целиком не запускался: нет GPU и Linux. Проверен синтаксис `bash -n`, ссылки — запросом HEAD, инструменты — на заглушках.
- Флаги MTP взяты из описаний, сверить с `--help` собранной версии.

## Коммиты
- `feat(remote): prepare the rental run for speed, code and vision (S-9.1, S-9.3, S-12.5)`
