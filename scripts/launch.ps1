<#
.SYNOPSIS
    Запуск витюбера одним кликом (ярлык на рабочем столе): ядро, LLM-сервер и окно.

.DESCRIPTION
    Пока нет собранной поставки (S-13.3 — только по команде), окно идёт из Tauri CLI через node, а ядро — из
    `.venv`. Окно в режиме разработки само ядро не запускает, поэтому это делает скрипт: издание берётся из
    `launcher.json` окна (последний выбор на экране выбора), а когда выбор меняется — ядро перезапускается
    в новом издании, и окно переподключается само (ADR-0032).

    LLM: если llama-server уже отвечает на 8080 — используется он; иначе, если в models/llm/ есть GGUF и
    найден llama-server.exe, ядро поднимает его само (`[llama_server].autostart`, ADR-0019).
    Закрыли окно — скрипт закрывает ядро (конец stdin) и выходит. Журнал — logs/launcher.log.

    Первый запуск долгий: окно собирается (Rust) несколько минут, дальше — секунды.

    -Background (ADR-0041): окно стартует скрытым в трее и открывается, когда витюбера зовут по имени.
    Так его запускает Windows при входе, если в меню значка включено «Запускать вместе с Windows».
    Повторный клик по ярлыку при запущенном витюбере открывает его окно.
#>
param([switch] $Background)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Log = if ($env:VTUBER_LAUNCHER_LOG) { $env:VTUBER_LAUNCHER_LOG } else { Join-Path $Root "logs\launcher.log" }
$LauncherFile = Join-Path ([Environment]::GetFolderPath("ApplicationData")) "local.vtuber.ui\launcher.json"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
# PATH — из реестра, а не от Проводника: он мог запуститься до установки Node.js и не знать новых путей.
$registryPath = @(
    [Environment]::GetEnvironmentVariable("PATH", "Machine"),
    [Environment]::GetEnvironmentVariable("PATH", "User")
) -join ";"
$UserData = [Environment]::GetFolderPath("ApplicationData")
$env:PATH = "C:\Program Files\nodejs;$UserData\npm;$env:USERPROFILE\.cargo\bin;$registryPath;$env:PATH"

# Окно запускается без pnpm: CLI Tauri и Vite — из ui/node_modules через node. pnpm, поставленный из
# изолированного приложения, обычный Проводник не видит (проверено), а node — системный.
$Node = @("C:\Program Files\nodejs\node.exe") + @((Get-Command node.exe -ErrorAction SilentlyContinue).Source) |
    Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
$TauriCli = Join-Path $Root "ui\node_modules\@tauri-apps\cli\tauri.js"
$TauriConfig = Join-Path $PSScriptRoot "tauri.launch.json"

New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null

function Write-Log([string] $Text) {
    # Запись журнала не должна ронять запуск: файл может быть занят (антивирус, просмотр).
    try {
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Text" | Out-File -FilePath $Log -Append -Encoding utf8
    } catch { }
}

# Вывод окна (Vite, cargo) — в свой файл: cmd держит его открытым, пока окно живо.
$WindowLog = [System.IO.Path]::ChangeExtension($Log, ".window.log")

function Show-Error([string] $Text) {
    Write-Log "ОШИБКА: $Text"
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($Text, "AI VTuber", "OK", "Error") | Out-Null
}

function Get-Edition {
    # Выбор на экране окна; файла нет или он битый — русское издание.
    try {
        $last = (Get-Content -LiteralPath $LauncherFile -Raw -Encoding utf8 | ConvertFrom-Json).last
        if ($last -in @("ru", "en")) { return $last }
    } catch { }
    return "ru"
}

function Test-Llm {
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 "http://127.0.0.1:8080/health" | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Set-LlmAutostart {
    if (Test-Llm) {
        Write-Log "llama-server уже запущен на 8080"
        return
    }
    $model = Get-ChildItem -LiteralPath (Join-Path $Root "models\llm") -Filter *.gguf -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notlike "mmproj*" } | Select-Object -First 1
    $server = @(
        (Join-Path $Root "llama\llama-server.exe"),
        (Join-Path $Root "packaging\dist\llama\llama-server.exe")
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($null -eq $server) {
        $found = Get-Command llama-server -ErrorAction SilentlyContinue
        if ($found) { $server = $found.Source }
    }
    if ($null -eq $model -or $null -eq $server) {
        Write-Log "LLM не запущена: нет модели в models/llm или llama-server.exe — окно покажет «LLM недоступна»"
        return
    }
    $env:VTUBER_LLAMA_SERVER__AUTOSTART = "true"
    $env:VTUBER_LLAMA_SERVER__EXECUTABLE = $server
    $env:VTUBER_LLAMA_SERVER__MODEL = $model.FullName
    Write-Log "LLM поднимет ядро: $($model.Name) через $server"
}

function Start-Core([string] $Edition) {
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $Python
    $info.Arguments = "-m vtuber serve --edition $Edition --root `"$Root`""
    $info.WorkingDirectory = $Root
    $info.UseShellExecute = $false
    $info.RedirectStandardInput = $true    # ядро живёт, пока открыт stdin
    $info.CreateNoWindow = $true
    Write-Log "ядро: издание $Edition"
    return [System.Diagnostics.Process]::Start($info)
}

function Stop-Core($Core) {
    if ($null -eq $Core -or $Core.HasExited) { return }
    $Core.StandardInput.Close()            # штатный выход: память дописывается
    if (-not $Core.WaitForExit(15000)) {
        Write-Log "ядро не вышло за 15 с — останавливаю"
        $Core.Kill()
    }
}

function Show-RunningWindow {
    # Окно уже живёт (часто — скрытым в трее): показать его вместо второго запуска.
    Add-Type -Namespace Vtuber -Name User32 -MemberDefinition @'
[DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern IntPtr FindWindow(string c, string t);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
'@
    # Класс — обязательно: `$null` PowerShell передаёт строкой "", и поиск без класса ничего не находит.
    $handle = [Vtuber.User32]::FindWindow("Tauri Window", "AI VTuber")
    if ($handle -eq [IntPtr]::Zero) { return $false }
    [Vtuber.User32]::ShowWindow($handle, 9) | Out-Null    # SW_RESTORE: и скрытое, и свёрнутое
    [Vtuber.User32]::SetForegroundWindow($handle) | Out-Null
    return $true
}

function Start-Window {
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = "cmd.exe"
    $info.Arguments = "/c `"`"$Node`" `"$TauriCli`" dev --config `"$TauriConfig`" > `"$WindowLog`" 2>&1`""
    $info.WorkingDirectory = Join-Path $Root "ui"
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    # Строку автозапуска окно пишет в реестр само (меню значка): в разработке запускать надо этот скрипт.
    $self = $PSCommandPath
    $info.EnvironmentVariables["VTUBER_AUTOSTART_COMMAND"] =
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$self`" -Background"
    $info.EnvironmentVariables["VTUBER_BACKGROUND"] = if ($Background) { "1" } else { "0" }
    Write-Log "окно: tauri dev через node$(if ($Background) { ', в фоне' })"
    return [System.Diagnostics.Process]::Start($info)
}

# Второй клик по ярлыку не запускает второе ядро на том же порту.
$mutex = New-Object System.Threading.Mutex($false, "Local\vtuber-launcher")
if (-not $mutex.WaitOne(0)) {
    if ($Background) { exit 0 }            # автозапуск, а витюбер уже работает — ничего не делать
    if (-not (Show-RunningWindow)) { Show-Error "Витюбер уже запускается — окно появится через минуту." }
    exit 0
}

try {
    if (-not (Test-Path -LiteralPath $Python)) {
        Show-Error "Нет окружения Python (.venv). Выполните в папке проекта: uv sync --all-extras"
        exit 1
    }
    if ($null -eq $Node) {
        Show-Error "Не найден Node.js. Установите его с nodejs.org."
        exit 1
    }
    if (-not (Test-Path -LiteralPath $TauriCli)) {
        Show-Error "Нет зависимостей окна (ui\node_modules). В папке ui выполните: npm install"
        exit 1
    }
    Write-Log "запуск из $Root; node: $Node"
    Set-LlmAutostart
    $edition = Get-Edition
    $core = Start-Core $edition
    $window = Start-Window
    while (-not $window.HasExited) {
        Start-Sleep -Milliseconds 1000
        $chosen = Get-Edition
        if ($chosen -ne $edition -or $core.HasExited) {
            # Выбор на экране сменился (или ядро упало): ядро — в выбранном издании, окно переподключится.
            Stop-Core $core
            $edition = $chosen
            $core = Start-Core $edition
        }
    }
    Write-Log "окно закрыто"
} catch {
    Show-Error "Запуск не удался: $($_.Exception.Message). Подробности — logs\launcher.log"
} finally {
    Stop-Core $core
    if ($window -and -not $window.HasExited) {
        & taskkill.exe /PID $window.Id /T /F | Out-Null
    }
    $mutex.ReleaseMutex()
}
