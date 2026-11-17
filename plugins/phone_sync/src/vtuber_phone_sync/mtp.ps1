# Доступ к папке Documents/UmNick телефона по MTP (S-24.7, ADR-0050) через Shell.Application.
# find — имя устройства; pull — notes.jsonl в $Temp; push — $Temp\from_pc.jsonl на телефон.
param([string]$Op, [string]$Temp)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$shell = New-Object -ComObject Shell.Application

function Find-UmNick {
    foreach ($dev in $shell.Namespace(17).Items()) {
        # Диски (C:\) пропускаем: у портативных устройств путь — объект оболочки «::{…}».
        if (-not $dev.IsFolder -or -not $dev.Path.StartsWith('::')) { continue }
        foreach ($store in $dev.GetFolder.Items()) {
            if (-not $store.IsFolder) { continue }
            $docs = $store.GetFolder.Items() | Where-Object { $_.Name -eq 'Documents' }
            if (-not $docs) { continue }
            $um = $docs.GetFolder.Items() | Where-Object { $_.Name -eq 'UmNick' }
            if ($um) { return @{ Device = $dev.Name; Folder = $um.GetFolder } }
        }
    }
    return $null
}

function Wait-File([string]$Path) {
    for ($i = 0; $i -lt 100 -and -not (Test-Path $Path); $i++) { Start-Sleep -Milliseconds 100 }
}

$found = Find-UmNick
if (-not $found) { exit 3 }
switch ($Op) {
    'find' { Write-Output $found.Device }
    'pull' {
        $item = $found.Folder.Items() | Where-Object { $_.Name -eq 'notes.jsonl' }
        if (-not $item) { exit 4 }
        $shell.Namespace($Temp).CopyHere($item, 4 + 16 + 1024)
        Wait-File (Join-Path $Temp 'notes.jsonl')
        Write-Output $found.Device
    }
    'push' {
        # Перезапись на MTP спрашивает пользователя — старый файл сначала уносим к себе.
        $old = $found.Folder.Items() | Where-Object { $_.Name -eq 'from_pc.jsonl' }
        if ($old) {
            $trash = Join-Path $Temp 'old'
            New-Item -ItemType Directory -Force $trash | Out-Null
            $shell.Namespace($trash).MoveHere($old, 4 + 16 + 1024)
            Start-Sleep -Milliseconds 500
        }
        $found.Folder.CopyHere((Join-Path $Temp 'from_pc.jsonl'), 4 + 16 + 1024)
        Write-Output $found.Device
    }
}
