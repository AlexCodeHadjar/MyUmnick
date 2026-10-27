<#
.SYNOPSIS
    Запускает llama-server для ядра витюбера (docs/performance.md: T-03, T-08, T-10).

.DESCRIPTION
    Все слои модели на GPU, flash attention, два слота: 0 — диалог (его KV-кэш живёт между
    ходами), 1 — фоновые задачи (Этап 10). Reasoning-режим выключен глобально (T-08).
    Адрес и порт должны совпадать с [llm].base_url в config/default.toml или config/user.toml.

    Флаги сверены с README llama-server (ggml-org/llama.cpp, tools/server) на 2026-10-27.
    После обновления llama.cpp сверьте их с `llama-server --help`; контекст на слот смотрите
    в GET /slots (поле n_ctx).

    Для RTX 5070 Ti (Blackwell, sm_120) нужна сборка llama.cpp с CUDA 12.8 или новее.

.EXAMPLE
    scripts/start_llm.ps1 -Model models/llm/model-Q4_K_M.gguf

.EXAMPLE
    scripts/start_llm.ps1 -Model models/llm/model-Q5_K_M.gguf -ContextSize 8192 -Server C:/llama/llama-server.exe
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Model,

    [string] $Server = "llama-server",

    [string] $ListenHost = "127.0.0.1",

    [int] $Port = 8080,

    # Общий контекст на все слоты; больше, чем нужно, — лишняя VRAM и медленный prefill (T-10).
    [int] $ContextSize = 16384,

    [int] $Slots = 2
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Model)) {
    throw "Не найден файл модели '$Model' — положите GGUF в models/llm/ (каталог не в git)."
}
if (-not (Get-Command $Server -ErrorAction SilentlyContinue)) {
    throw "Не найден '$Server' — установите llama.cpp (CUDA 12.8+) или укажите путь: -Server <путь к llama-server.exe>."
}

& $Server --version

$arguments = @(
    "--model", $Model,
    "--n-gpu-layers", "99",        # T-10: все слои на GPU
    "--ctx-size", $ContextSize,
    "--parallel", $Slots,
    "--flash-attn", "on",          # T-10
    "--jinja",                     # шаблон чата модели (нужен /apply-template и chat_template_kwargs)
    "--reasoning-budget", "0",     # T-08: без скрытых рассуждений перед ответом
    "--metrics",                   # /metrics для бенчмарков (S-2.4, Этап 9)
    "--no-webui",
    "--host", $ListenHost,
    "--port", $Port
)

Write-Host "llama-server $($arguments -join ' ')"
& $Server @arguments
exit $LASTEXITCODE
