# Общее для скриптов арендованного GPU-сервера (scripts/remote/README.md). Подключается через
# `source`, сам не запускается.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
WORK=${WORK:-/workspace}
MODELS_DIR=${MODELS_DIR:-$WORK/models}
LLAMA_DIR=${LLAMA_DIR:-$WORK/llama.cpp}
LLAMA_BIN=$LLAMA_DIR/build/bin
RESULTS_DIR=${RESULTS_DIR:-$ROOT/bench/results/remote}
MODELS_TSV=$ROOT/scripts/remote/models.tsv
export PATH=$HOME/.local/bin:$PATH # uv ставится сюда (setup.sh)

log() { printf '[%(%H:%M:%S)T] %s\n' -1 "$*"; }

# Строки models.tsv без комментариев; ONLY — регулярка по «имя квант» (например, 'gemma|Q4_K_M').
model_rows() {
    grep -v '^#' "$MODELS_TSV" | grep -v '^[[:space:]]*$' |
        while IFS=$'\t' read -r name quant rest; do
            if [[ -z ${ONLY:-} || "$name $quant" =~ $ONLY ]]; then
                printf '%s\t%s\t%s\n' "$name" "$quant" "$rest"
            fi
        done
}

model_path() { printf '%s/%s/%s' "$MODELS_DIR" "$1" "$2"; }
