$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$dir = [Environment]::GetFolderPath('Recent')
$links = Get-ChildItem -LiteralPath $dir -File -Filter '*.lnk' | Sort-Object LastWriteTime -Descending | Select-Object -First 16
if (!$links) { exit }
$link = $links | Get-Random
$target = (New-Object -ComObject WScript.Shell).CreateShortcut($link.FullName).TargetPath
$name = [IO.Path]::GetFileName($target)
if (!$name -or ![IO.Path]::HasExtension($name)) { exit }
Add-Type -AssemblyName System.Drawing
$icon = [Drawing.Icon]::ExtractAssociatedIcon($link.FullName)
if (!$icon) { exit }
$bitmap = $icon.ToBitmap()
$stream = [IO.MemoryStream]::new()
try {
    $bitmap.Save($stream, [Drawing.Imaging.ImageFormat]::Png)
    [Console]::WriteLine($name)
    [Console]::Write([Convert]::ToBase64String($stream.ToArray()))
} finally { $stream.Dispose(); $bitmap.Dispose(); $icon.Dispose() }
