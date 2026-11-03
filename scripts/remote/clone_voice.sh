#!/usr/bin/env bash
# Клонирование голоса на сервере: окружения движков и прогон (scripts/remote/README.md).
# Образцы в git не лежат: data/voice_refs/silv/prepared/ копируется на сервер отдельно.
# Выбор движков: ENGINES='qwen0.6 omni'. Повторный запуск пропускает готовые файлы.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

PREPARED=${PREPARED:-$ROOT/data/voice_refs/silv/prepared}
OUT=${OUT:-$ROOT/bench/results/tts_samples/clone}
ENV_DIR=${ENV_DIR:-$WORK/tts_clone_env}
ENGINES=${ENGINES:-qwen0.6 qwen1.7 omni chatterbox}
SCRIPT=$ROOT/scripts/remote/clone_voice.py

venv_for() {
    local dir=$ENV_DIR/$1 python=$2
    shift 2
    [[ -d $dir ]] && return 0
    uv venv -q --python "$python" "$dir" && VIRTUAL_ENV=$dir uv pip install -q "$@" soundfile
}

setup_engine() {
    case $1 in
    qwen*) venv_for q 3.12 qwen-tts && echo "$ENV_DIR/q" ;;
    omni) venv_for o 3.12 omnivoice && echo "$ENV_DIR/o" ;;
    chatterbox)
        # Сборка torch из зависимостей не знает sm_120 (RTX 5070 Ti), нужен именно cu128.
        if [[ ! -d $ENV_DIR/c ]]; then
            venv_for c 3.11 chatterbox-tts &&
                VIRTUAL_ENV=$ENV_DIR/c uv pip install -q --reinstall torch==2.7.1 torchaudio==2.7.1 \
                    --index-url https://download.pytorch.org/whl/cu128
        fi
        echo "$ENV_DIR/c"
        ;;
    esac
}

mkdir -p "$ENV_DIR" "$OUT"
for engine in $ENGINES; do
    log "движок $engine"
    env_path=$(setup_engine "$engine") || {
        log "ОШИБКА установки $engine"
        continue
    }
    "$env_path/bin/python" "$SCRIPT" synth "$engine" "$PREPARED" "$OUT" || log "ОШИБКА прогона $engine"
done
python3 "$SCRIPT" index "$OUT"
log "готово: $OUT/index.html"
