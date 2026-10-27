# Прогон на арендованной RTX 5070 Ti (gpu.nz)

Зачем: S-2.4 (бенчмарк и eval против настоящего llama-server), S-2.5 (выбор модели, ADR-0004),
`pytest -m gpu` и ручная проверка M1 — всё, что ждёт целевую машину. Аренда — на 3–4 часа,
около 150 ₽. Ядро проекта не меняется: llama-server на сервере слушает `127.0.0.1:8080`,
у нас туда ведёт SSH-туннель, `[llm].base_url` прежний.

Что **не** проверяется: TTS/STT, Live2D, 60 FPS, Windows-сборка llama-server, общий бюджет VRAM
с TTS. Процессор и RAM у хоста другие — NFR потом перепроверить на своей машине.

## Файлы

| Файл | Где запускается | Что делает |
|---|---|---|
| `models.tsv` | — | Кандидаты: репозиторий, закреплённая ревизия, размер, sha256, лицензия |
| `setup.sh` | сервер | Пакеты, сборка `llama-server` и `llama-bench` под sm_120, `uv sync` |
| `download_models.sh` | сервер | Скачивание моделей с докачкой и проверкой размера |
| `start_llm.sh` | сервер | Двойник `scripts/start_llm.ps1` с теми же флагами |
| `run_candidates.sh` | сервер | Все кандидаты по очереди: бенчмарк, eval, llama-bench, журнал GPU |

Результаты на сервере — `bench/results/remote/<модель>/<квант>/`: `bench.json`, `eval.json`,
`llama-bench.json`, `gpu.csv` (частоты, температура, VRAM по секундам), `server.log`,
`load_s.txt` (секунд до готовности), `props.json`, `slots.json`; общее — `host.txt`.

## Выбор сервера

Фильтр: RTX 5070 Ti, 1 GPU, память GPU ≥ 700 ГБ/с (дешёвые хосты с ~535 ГБ/с занижают TPS),
≥ 12 ядер, ≥ 30 ГБ RAM, надёжность ≥ 98 %, «По требованию» (не прерываемый).
Сетка на 2026-10-27: Румыния 40 ₽/ч (Core Ultra 7, PCIe 5, трафик почти бесплатный, хост не
проверен); запасной — США, Вашингтон 35 ₽/ч (проверен).

Запуск сервера в консоли gpu.nz:
- шаблон «Свой Docker-образ», образ `nvidia/cuda:12.9.1-devel-ubuntu24.04` (Docker Hub, есть
  `nvcc`); порты не нужны — всё через SSH;
- диск **120 ГБ** (модели ≈ 73 ГБ + сборка + окружение); размер после запуска не меняется;
- SSH-ключ `gpunz_ed25519.pub` добавлен в «Ключи» **до** запуска.

## Порядок действий

Обозначения: **[П]** — пользователь, **[И]** — ИИ-ассистент (команды с ПК пользователя).
`USER`, `HOST`, `PORT` — из команды подключения на странице сервера.

1. **[П]** Пополнить баланс через СБП на 300 ₽ (при нуле сервер удаляется вместе с диском).
2. **[П]** «Ключи» → добавить содержимое `~/.ssh/gpunz_ed25519.pub`; запустить сервер (выше);
   прислать команду подключения. Поставить себе напоминание: через 4 часа проверить, что
   сервер удалён.
3. **[И]** Проверка за первые 5 минут — плохой хост удаляем сразу (потеря — пара рублей):
   ```bash
   ssh -i ~/.ssh/gpunz_ed25519 -p PORT USER@HOST 'nvidia-smi; nproc; free -g; df -h /workspace'
   ```
   Стоп-сигналы: SSH не держится, не та карта, диск меньше заказанного.
4. **[И]** Код на сервер (только закоммиченное — `git archive`; незакоммиченное не уедет):
   ```bash
   git archive --format=tar HEAD | ssh -i ~/.ssh/gpunz_ed25519 -p PORT USER@HOST \
     'mkdir -p /workspace/vruber && tar -x -C /workspace/vruber'
   ```
5. **[И]** В `tmux` на сервере — загрузка и сборка параллельно (обрыв SSH их не останавливает):
   ```bash
   tmux new -d -s dl 'bash /workspace/vruber/scripts/remote/download_models.sh 2>&1 | tee /workspace/dl.log'
   tmux new -d -s setup 'bash /workspace/vruber/scripts/remote/setup.sh 2>&1 | tee /workspace/setup.log'
   ```
   Стоп-сигнал: загрузка медленнее 5 МБ/с — меняем хост.
6. **[И]** Прогон всех кандидатов (≈ 5–8 минут на строку, 10 строк):
   ```bash
   tmux new -d -s run 'bash /workspace/vruber/scripts/remote/run_candidates.sh 2>&1 | tee /workspace/run.log'
   ```
   Результаты забирать после каждой модели — сервер может пропасть:
   ```bash
   ssh -i ~/.ssh/gpunz_ed25519 -p PORT USER@HOST 'tar -C /workspace/vruber/bench/results -c remote' \
     | tar -x -C bench/results
   ```
7. **[И]** `pytest -m gpu` и прогон через туннель (видно задержку сети отдельно):
   ```bash
   ssh -i ~/.ssh/gpunz_ed25519 -p PORT -N -L 8080:127.0.0.1:8080 USER@HOST   # фоном
   uv run pytest -m gpu
   uv run python -m tools.bench_latency --runs 1 --out bench/results/remote/tunnel.json
   ```
   На сервере перед этим — лучшая модель: `bash scripts/remote/start_llm.sh <путь>` в `tmux`.
8. **[П]** Ручная проверка M1 через туннель: `uv run python -m vtuber` или UI (`pnpm tauri dev`).
9. **[И]** Забрать результаты (шаг 6), **[П]** удалить сервер (удалить, не остановить:
   остановленный диск продолжает стоить денег).
10. **[И]** S-2.5: таблица в ADR-0004, модель в `config/default.toml`, `docs/licenses.md`,
    галочки S-2.4/S-2.5, STATE, коммит.

## Если что-то пошло не так

- **Обрыв SSH** — задачи в `tmux` продолжают работать; переподключиться, `tmux ls`,
  `tail /workspace/*.log`. Для устойчивости: `-o ServerAliveInterval=15 -o ServerAliveCountMax=4`.
- **Обрыв загрузки** — запустить `download_models.sh` снова: докачает.
- **Обрыв прогона / хост пропал** — `run_candidates.sh` пропускает готовое (файл `done`); на
  новом хосте шаги 4–6, затем `ONLY='<оставшиеся>'`.
- **llama.cpp не знает архитектуру модели** — свежий master обычно знает; иначе строка из
  `models.tsv` убирается, в ADR — пометка.
- **Карта сбрасывает частоты** — видно в `gpu.csv` (clocks.sm, temperature.gpu, power.draw);
  отметить в ADR, при сильном троттлинге — сменить хост.
