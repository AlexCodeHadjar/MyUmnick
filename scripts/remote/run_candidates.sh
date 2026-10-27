#!/usr/bin/env bash
# Прогон кандидатов S-2.5 на сервере: для каждой строки models.tsv — запуск llama-server,
# бенчмарк задержки, eval качества, llama-bench, журнал GPU (частоты, температура, VRAM).
# Готовые прогоны (файл done) пропускаются — после обрыва просто запустить снова.
# Бенчмарк идёт на самом сервере: сеть до нас в TTFT не попадает.
# Запуск (лучше в tmux): bash scripts/remote/run_candidates.sh;  ONLY='gemma' — часть строк.
set -uo pipefail
source "$(dirname "$0")/common.sh"

PORT=${PORT:-8080}
RUNS=${RUNS:-3}
HEALTH_TIMEOUT_S=${HEALTH_TIMEOUT_S:-300}

wait_health() {
    local pid=$1 started=$SECONDS
    until curl -sf "http://127.0.0.1:$PORT/health" >/dev/null; do
        kill -0 "$pid" 2>/dev/null || return 1
        ((SECONDS - started < HEALTH_TIMEOUT_S)) || return 1
        sleep 1
    done
    echo $((SECONDS - started))
}

start_gpu_log() {
    nvidia-smi --query-gpu=timestamp,temperature.gpu,clocks.sm,clocks.mem,power.draw,memory.used,utilization.gpu \
        --format=csv,nounits -l 1 >"$1/gpu.csv" &
    echo $!
}

run_tools() {
    local out=$1 status=0
    curl -s "http://127.0.0.1:$PORT/props" >"$out/props.json"
    curl -s "http://127.0.0.1:$PORT/slots" >"$out/slots.json"
    (cd "$ROOT" && uv run python -m tools.bench_latency --runs "$RUNS" --out "$out/bench.json") \
        >"$out/bench.txt" 2>&1 || status=1
    (cd "$ROOT" && uv run python -m tools.eval_quality --out "$out/eval.json") \
        >"$out/eval.txt" 2>&1 || status=1
    return "$status"
}

run_one() {
    local name=$1 quant=$2 file=$3 out=$RESULTS_DIR/$1/$2
    local model server gpu
    model=$(model_path "$name" "$file")
    [[ -f $out/done ]] && { log "пропуск $name $quant: уже есть"; return 0; }
    [[ -f $model ]] || { log "нет файла $model — сначала download_models.sh"; return 1; }
    mkdir -p "$out"
    log "старт $name $quant"
    bash "$ROOT/scripts/remote/start_llm.sh" "$model" >"$out/server.log" 2>&1 &
    server=$!
    gpu=$(start_gpu_log "$out")
    if wait_health "$server" >"$out/load_s.txt"; then
        run_tools "$out" || log "ошибка инструментов $name $quant — см. $out/*.txt"
    else
        log "сервер не поднялся: $out/server.log"
    fi
    kill "$server" "$gpu" 2>/dev/null
    wait "$server" "$gpu" 2>/dev/null
    "$LLAMA_BIN/llama-bench" -m "$model" -ngl 99 -fa 1 -p 512 -n 128 -r 3 -o json \
        >"$out/llama-bench.json" 2>"$out/llama-bench.log"
    [[ -s $out/bench.json && -s $out/eval.json ]] && touch "$out/done"
    log "конец $name $quant"
}

# Список — через fd 3: llama-server и uv не должны съесть строки из stdin цикла.
while IFS=$'\t' read -r -u 3 name quant _repo _rev file _rest; do
    run_one "$name" "$quant" "$file" </dev/null
done 3< <(model_rows)
log "итоги: $RESULTS_DIR"
