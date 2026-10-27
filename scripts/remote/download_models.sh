#!/usr/bin/env bash
# Скачивает кандидатов из models.tsv прямо на сервер. Обрыв не страшен: curl докачивает (-C -),
# скачанный целиком файл проверяется по размеру и пропускается при повторном запуске.
# Запуск: bash scripts/remote/download_models.sh
#   ONLY='Q4_K_M' …   — только часть строк (регулярка по «имя квант»)
#   DRY_RUN=1 …       — только показать ссылки и проверить, что они отвечают
#   VERIFY_SHA=1 …    — сверить sha256 (≈ 30 с на 8 ГБ)
set -euo pipefail
source "$(dirname "$0")/common.sh"

download() {
    local name=$1 repo=$2 rev=$3 file=$4 bytes=$5 sha=$6
    local url="https://huggingface.co/$repo/resolve/$rev/$file"
    local path
    path=$(model_path "$name" "$file")
    if [[ -n ${DRY_RUN:-} ]]; then
        printf '%s %s\n' "$(curl -sIL -o /dev/null -w '%{http_code}' "$url")" "$url"
        return
    fi
    mkdir -p "$(dirname "$path")"
    if [[ $(stat -c %s "$path" 2>/dev/null || echo 0) != "$bytes" ]]; then
        log "качаю $name/$file ($((bytes / 1000000)) МБ)"
        curl -fL --retry 10 --retry-all-errors --retry-delay 5 -C - -o "$path" "$url"
    fi
    [[ $(stat -c %s "$path") == "$bytes" ]] || { echo "размер не совпал: $path" >&2; return 1; }
    if [[ -n ${VERIFY_SHA:-} ]]; then
        echo "$sha  $path" | sha256sum -c --quiet
    fi
    log "ок $name/$file"
}

failed=0
while IFS=$'\t' read -r -u 3 name _quant repo rev file bytes sha _license; do
    download "$name" "$repo" "$rev" "$file" "$bytes" "$sha" </dev/null || failed=1
done 3< <(model_rows)
df -h "$MODELS_DIR" 2>/dev/null | tail -1 || true
exit "$failed"
