#!/usr/bin/env bash
# Прогон кандидатов английского издания S-20.9 (STAGE_20, раздел 5.4): для каждой строки models_en.tsv —
# llama-server, затем по порядку фильтров: скорость (bench_latency), жёсткий минимум и отказы (eval_profile),
# качество (eval_quality на qa_en). Издание — через VTUBER_EDITION__ID=en: персона, рамка и grammar английские.
# Скачать модели: MODELS_TSV=scripts/remote/models_en.tsv bash scripts/remote/download_models.sh
# Запуск (лучше в tmux): bash scripts/remote/run_english.sh;  ONLY='rocinante' — часть строк.
set -uo pipefail
export MODELS_TSV=${MODELS_TSV:-$(dirname "$0")/models_en.tsv}
export VTUBER_EDITION__ID=en
source "$(dirname "$0")/common.sh"

PORT=${PORT:-8080}
RUNS=${RUNS:-3}
HEALTH_TIMEOUT_S=${HEALTH_TIMEOUT_S:-300}
RESULTS_EN=${RESULTS_EN:-$RESULTS_DIR/english}

wait_health() {
    local pid=$1 started=$SECONDS
    until curl -sf "http://127.0.0.1:$PORT/health" >/dev/null; do
        kill -0 "$pid" 2>/dev/null || return 1
        ((SECONDS - started < HEALTH_TIMEOUT_S)) || return 1
        sleep 1
    done
}

run_tools() {
    local out=$1 py="uv run python -m"
    curl -s "http://127.0.0.1:$PORT/props" >"$out/props.json"
    (cd "$ROOT" && $py tools.bench_latency --runs "$RUNS" --out "$out/bench.json") >"$out/bench.txt" 2>&1
    (cd "$ROOT" && $py tools.eval_profile --edition en --cases eval/floor_en.jsonl) >"$out/floor.txt" 2>&1
    (cd "$ROOT" && $py tools.eval_profile --edition en --cases eval/uncomfortable_en.jsonl) \
        >"$out/uncomfortable.txt" 2>&1
    (cd "$ROOT" && $py tools.eval_quality --cases eval/qa_en.jsonl --out "$out/eval.json") \
        >"$out/eval.txt" 2>&1
}

run_one() {
    local name=$1 quant=$2 file=$3 out=$RESULTS_EN/$1/$2 model server
    model=$(model_path "$name" "$file")
    [[ -f $out/done ]] && { log "пропуск $name: уже есть"; return 0; }
    [[ -f $model ]] || { log "нет файла $model — сначала download_models.sh"; return 1; }
    mkdir -p "$out"
    log "старт $name $quant"
    bash "$ROOT/scripts/remote/start_llm.sh" "$model" >"$out/server.log" 2>&1 &
    server=$!
    if wait_health "$server"; then
        run_tools "$out"
        nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits >"$out/vram_mb.txt"
    else
        log "сервер не поднялся: $out/server.log"
    fi
    kill "$server" 2>/dev/null
    wait "$server" 2>/dev/null
    [[ -s $out/eval.json ]] && touch "$out/done"
    log "конец $name"
}

while IFS=$'\t' read -r -u 3 name quant _repo _rev file _rest; do
    run_one "$name" "$quant" "$file" </dev/null
done 3< <(model_rows)
log "итоги: $RESULTS_EN; слепую оценку пользователя — по 20 диалогам у 2–3 лучших (STAGE_20, 5.4)"
