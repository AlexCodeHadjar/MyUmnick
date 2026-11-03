#!/usr/bin/env bash
# Прогон на сервере: S-9.1 (профиль), S-9.3 (черновик MTP, контекст), S-18.1 (картинка), S-12.5 (модели кода),
# S-12.6 (настоящий плагин и TTFT рядом с работающей моделью). Шаги по очереди: замеры не должны мешать друг другу.
# Готовые шаги (файл done) пропускаются — после обрыва просто запустить снова.
# Сначала: bash scripts/remote/download_models.sh с ONLY='gemma4-12b-hauhau Q4_K_M' и с MODELS_TSV=…/models_extra.tsv.
# Запуск (в tmux): bash scripts/remote/run_my_set.sh;  STEPS='speed code' — только эти шаги.
# Запускает код, написанный моделью (tools.eval_code): на сервере не должно быть токенов и ключей.
set -uo pipefail
source "$(dirname "$0")/common.sh"
cd "$ROOT" || exit 1

STEPS=${STEPS:-profile speed vision code assistant}
OUT=$RESULTS_DIR/my_set
MAIN_DIR=$MODELS_DIR/gemma4-12b-hauhau
MAIN=$MAIN_DIR/Gemma4-12B-QAT-Uncensored-HauhauCS-Balanced-Q4_K_M.gguf
EXTRA_TSV=$ROOT/scripts/remote/models_extra.tsv
HEALTH_TIMEOUT_S=${HEALTH_TIMEOUT_S:-300}
CODE_PORT=8081
# Кандидат для проверки настоящего плагина: должен помещаться рядом с основной моделью.
ASSIST=${ASSIST:-code-qwen25-7b}
PY=.venv/bin/python
export PYTHONPATH=plugins/code_assistant/src

SERVERS=()

# serve <порт> <журнал> <модель> [контекст] [слоты] [доп. флаги]
serve() {
    PORT=$1 CTX=${4:-16384} SLOTS=${5:-2} EXTRA_ARGS=${6:-} \
        bash scripts/remote/start_llm.sh "$3" >"$2" 2>&1 &
    local pid=$! started=$SECONDS
    SERVERS+=("$pid")
    until curl -sf "http://127.0.0.1:$1/health" >/dev/null; do
        kill -0 "$pid" 2>/dev/null || return 1
        ((SECONDS - started < HEALTH_TIMEOUT_S)) || return 1
        sleep 1
    done
    echo $((SECONDS - started)) >"$2.load_s"
}

stop_all() {
    ((${#SERVERS[@]})) && kill "${SERVERS[@]}" 2>/dev/null
    wait 2>/dev/null
    SERVERS=()
    sleep 3 # видеопамять освобождается не мгновенно, а замер VRAM идёт сразу после
}

vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits >"$1"; }

step_profile() {
    local dir=$1
    uv pip install py-spy >"$dir/py-spy-install.txt" 2>&1 # только на сервере, в проект не входит
    serve 8080 "$dir/server.log" "$MAIN" || return 1
    .venv/bin/py-spy record -o "$dir/flame.svg" -- \
        $PY -m tools.bench_latency --runs 3 --out "$dir/bench.json" >"$dir/py-spy.txt" 2>&1
    $PY -m tools.bench_core --out "$dir/core.json" >"$dir/core.txt" 2>&1
    stop_all
    [[ -s $dir/core.json ]]
}

# Вариант основной модели: имя, контекст, флаги.
speed_variant() {
    local dir=$1/$2
    mkdir -p "$dir"
    if serve 8080 "$dir/server.log" "$MAIN" "$3" 2 "${4:-}"; then
        vram "$dir/vram_mb.txt"
        $PY -m tools.bench_latency --runs 3 --out "$dir/bench.json" >"$dir/bench.txt" 2>&1
        curl -s http://127.0.0.1:8080/metrics >"$dir/metrics.txt"
    else
        log "вариант $2 не поднялся: $dir/server.log"
    fi
    stop_all
}

step_speed() {
    local dir=$1 mtp=$MAIN_DIR/mtp-gemma-4-12B-it.gguf
    "$LLAMA_BIN/llama-server" --help >"$dir/help.txt" 2>&1
    speed_variant "$dir" base 16384
    speed_variant "$dir" ctx8k 8192
    # n-max 2: при 3 в llama.cpp замечен другой вывод, чем без черновика (issue 23302).
    speed_variant "$dir" mtp2 16384 "--model-draft $mtp --spec-type draft-mtp --spec-draft-n-max 2"
    [[ -s $dir/base/bench.json ]]
}

step_vision() {
    local dir=$1 proj=$MAIN_DIR/mmproj-Gemma4-12B-QAT-Uncensored-HauhauCS-Balanced-BF16.gguf
    serve 8080 "$dir/server.log" "$MAIN" 16384 2 "--mmproj $proj" || return 1
    vram "$dir/vram_mb.txt"
    $PY -m tools.bench_vision --out "$dir/vision.json" >"$dir/vision.txt" 2>&1
    $PY -m tools.bench_latency --runs 3 --out "$dir/bench_text.json" >"$dir/bench_text.txt" 2>&1
    stop_all
    [[ -s $dir/vision.json ]]
}

# Кандидат один: VRAM, задачи с автопроверкой, скорость. Рядом с основной: помещается ли и что с её TTFT.
code_candidate() {
    local name=$1 model=$2 dir=$3/$1 eval_pid
    mkdir -p "$dir"
    if serve "$CODE_PORT" "$dir/alone.log" "$model" 8192 1; then
        vram "$dir/vram_alone_mb.txt"
        $PY -m tools.eval_code --url "http://127.0.0.1:$CODE_PORT" --out "$dir/eval.json" >"$dir/eval.txt" 2>&1
        curl -s "http://127.0.0.1:$CODE_PORT/metrics" >"$dir/metrics.txt"
    else
        log "$name один не поднялся: $dir/alone.log"
    fi
    stop_all
    if serve 8080 "$dir/main.log" "$MAIN" && serve "$CODE_PORT" "$dir/beside.log" "$model" 8192 1; then
        vram "$dir/vram_beside_mb.txt"
        $PY -m tools.bench_latency --runs 1 --out "$dir/ttft_idle.json" >"$dir/ttft_idle.txt" 2>&1
        $PY -m tools.eval_code --url "http://127.0.0.1:$CODE_PORT" --out "$dir/eval_load.json" >"$dir/eval_load.txt" 2>&1 &
        eval_pid=$!
        $PY -m tools.bench_latency --runs 1 --out "$dir/ttft_load.json" >"$dir/ttft_load.txt" 2>&1
        wait "$eval_pid"
    else
        log "$name рядом с основной не помещается"
        echo "не помещается" >"$dir/beside_no_fit.txt"
    fi
    stop_all
    [[ -s $dir/eval.json ]]
}

step_code() {
    local dir=$1 status=0
    while IFS=$'\t' read -r -u 3 name _quant _repo _rev file _rest; do
        code_candidate "$name" "$MODELS_DIR/$name/$file" "$dir" </dev/null || status=1
    done 3< <(MODELS_TSV=$EXTRA_TSV ONLY='^code-' model_rows)
    return "$status"
}

step_assistant() {
    local dir=$1 row file
    row=$(MODELS_TSV=$EXTRA_TSV ONLY="^$ASSIST " model_rows | head -1)
    file=$(cut -f5 <<<"$row")
    serve 8080 "$dir/main.log" "$MAIN" || return 1
    serve "$CODE_PORT" "$dir/code.log" "$MODELS_DIR/$ASSIST/$file" 8192 1 || return 1
    $PY -m tools.check_assistant >"$dir/plugin.txt" 2>&1
    local status=$?
    $PY -W ignore -m tools.bench_voice --tts silero --runs 1 --out "$dir/voice.json" >"$dir/voice.txt" 2>&1
    stop_all
    return "$status"
}

trap stop_all EXIT
for step in $STEPS; do
    dir=$OUT/$step
    [[ -f $dir/done ]] && { log "пропуск $step: уже есть"; continue; }
    mkdir -p "$dir"
    log "шаг $step"
    if "step_$step" "$dir"; then
        touch "$dir/done"
    else
        log "шаг $step не удался: см. $dir"
    fi
    stop_all
done
log "итоги: $OUT"
