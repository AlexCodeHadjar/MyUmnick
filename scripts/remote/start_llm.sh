#!/usr/bin/env bash
# Linux-двойник scripts/start_llm.ps1 для арендованного сервера: те же флаги (T-03, T-08, T-10).
# Меняете флаги там — меняйте и здесь, иначе замеры не про то приложение.
# Запуск: bash scripts/remote/start_llm.sh /workspace/models/<имя>/<файл>.gguf
set -euo pipefail
source "$(dirname "$0")/common.sh"

MODEL=${1:?путь к .gguf}
PORT=${PORT:-8080}
CTX=${CTX:-16384}
SLOTS=${SLOTS:-2}
EXTRA_ARGS=${EXTRA_ARGS:-} # по словам: --mmproj, --model-draft и другие флаги замеров

exec "$LLAMA_BIN/llama-server" \
    --model "$MODEL" \
    --n-gpu-layers 99 \
    --ctx-size "$CTX" \
    --parallel "$SLOTS" \
    --flash-attn on \
    --jinja \
    --reasoning-budget 0 \
    --metrics \
    --no-webui \
    --host 127.0.0.1 \
    --port "$PORT" \
    $EXTRA_ARGS
