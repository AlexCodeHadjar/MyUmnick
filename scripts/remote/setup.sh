#!/usr/bin/env bash
# Подготовка арендованного сервера: пакеты, сборка llama-server под Blackwell, uv и зависимости
# проекта. Образ — nvidia/cuda:12.9.1-devel-ubuntu24.04 (нужен nvcc; для sm_120 — CUDA 12.8+).
# Повторный запуск безопасен: готовое пропускается.
# Запуск из корня репозитория на сервере: bash scripts/remote/setup.sh
set -euo pipefail
source "$(dirname "$0")/common.sh"

LLAMA_REF=${LLAMA_REF:-} # тег llama.cpp (например, b7000); пусто — последний коммит master
SUDO=$([[ $(id -u) -eq 0 ]] && echo "" || echo sudo)

install_packages() {
    log "пакеты"
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq --no-install-recommends \
        git cmake ninja-build build-essential curl ca-certificates tmux jq >/dev/null
}

check_cuda() {
    nvidia-smi --query-gpu=name,driver_version,memory.total,clocks.max.sm,power.limit --format=csv
    local version
    version=$(nvcc --version | sed -n 's/.*release \([0-9]*\.[0-9]*\).*/\1/p')
    log "nvcc $version"
    if ! printf '%s\n12.8\n' "$version" | sort -V -C -r; then
        echo "Нужна CUDA 12.8+ для sm_120 (RTX 50xx), в образе $version — смените образ." >&2
        exit 1
    fi
}

build_llama() {
    if [[ -x $LLAMA_BIN/llama-server ]]; then
        log "llama-server уже собран"
        return
    fi
    log "сборка llama.cpp ${LLAMA_REF:-master}"
    [[ -d $LLAMA_DIR ]] || git clone --depth 1 ${LLAMA_REF:+--branch "$LLAMA_REF"} \
        https://github.com/ggml-org/llama.cpp "$LLAMA_DIR"
    cmake -S "$LLAMA_DIR" -B "$LLAMA_DIR/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
        -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=120 -DLLAMA_CURL=OFF
    cmake --build "$LLAMA_DIR/build" --target llama-server llama-bench -j "$(nproc)"
}

install_project() {
    command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
    log "uv sync"
    (cd "$ROOT" && uv sync --frozen)
}

install_packages
check_cuda
build_llama
install_project
mkdir -p "$RESULTS_DIR"
{
    git -C "$LLAMA_DIR" rev-parse HEAD
    "$LLAMA_BIN/llama-server" --version 2>&1
    nvidia-smi --query-gpu=name,driver_version,memory.total,clocks.max.sm,clocks.max.mem,power.limit,pcie.link.gen.max,pcie.link.width.max --format=csv
    nproc
    free -g
} >"$RESULTS_DIR/host.txt" 2>&1
log "готово: $RESULTS_DIR/host.txt"
