#!/usr/bin/env bash
# Добивающий прогон выбранной модели на запущенном llama-server (ADR-0004): gpu-тесты, голос,
# базовая задержка (S-9.1) и эффект прогрева черновиком на длинных репликах (T-05, S-9.2).
# Запуск на сервере, в tmux: OUT=bench/results/remote/<модель>/<квант> bash scripts/remote/finish_chosen.sh
set -u
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
cd "$ROOT" || exit 1
OUT=${OUT:?каталог результатов}
mkdir -p "$OUT"
PY=.venv/bin/python

log "pytest -m gpu"
.venv/bin/pytest -m gpu -q 2>&1 | tail -40 >"$OUT/pytest_gpu.txt"

log "голос: TTFA с настоящей LLM"
$PY -W ignore -m tools.bench_voice --tts silero --runs 1 --out "$OUT/voice.json" >"$OUT/voice.txt" 2>&1

log "базовая задержка, все реплики"
$PY -m tools.bench_latency --runs 3 --out "$OUT/baseline.json" >"$OUT/baseline.txt" 2>&1

# Длинные реплики (> 15 слов) — по критерию S-9.2.
$PY - <<'PYEOF'
import json
from pathlib import Path
rows = [line for line in Path("bench/prompts_ru.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
long = [row for row in rows if len(json.loads(row)["text"].split()) > 15]
Path("/tmp/prompts_long.jsonl").write_text("\n".join(long) + "\n", encoding="utf-8")
print(len(long), "длинных реплик")
PYEOF
log "прогрев черновиком: без и с ним"
for round in 1 2; do
    $PY -m tools.bench_latency --prompts /tmp/prompts_long.jsonl --runs 3 \
        --out "$OUT/prefill_off_$round.json" >"$OUT/prefill_off_$round.txt" 2>&1
    $PY -m tools.bench_latency --prompts /tmp/prompts_long.jsonl --runs 3 --speculative \
        --out "$OUT/prefill_on_$round.json" >"$OUT/prefill_on_$round.txt" 2>&1
done
log "память: цена в TTFT и сквозной сценарий (Этап 10)"
$PY -W ignore -m tools.bench_memory --out "$OUT/memory_ttft.json" >"$OUT/memory_ttft.txt" 2>&1
$PY -W ignore -m tools.eval_memory --out "$OUT/memory_e2e.json" >"$OUT/memory_e2e.txt" 2>&1
log "качество: eval на 150 кейсах (S-10.6)"
$PY -m tools.eval_quality --out "$OUT/eval150.json" >"$OUT/eval150.txt" 2>&1
log "FINISH-DONE"
