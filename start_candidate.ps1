param(
    [ValidateSet('start','stop','verify','snapshot','pause')]
    [string]$Mode = 'start',
    [switch]$VerifyOnly,
    [string]$Python,
    [string]$Node,
    [string]$PowerShell
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath($PSScriptRoot)
if (((Get-Item -LiteralPath $projectRoot -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'Use an ordinary project directory.'
}
$pins = @{
    'scripts/release/upgrade_main201.py' = '8f885b16cf8b7b582375e21202452186720cf0272711dbd45cfca0a3b76b1a76'
    'scripts/release/main201_source.py' = '01c137a2afc38b0e5e3f4178e85c919adb25c8d7fa015ea5daadca60d12f0505'
    'scripts/release/main201_metadata.py' = 'affe619a9c0b81c50aa2467f252d63489ebc044d1111d08f685f9fdf69f045c8'
}
foreach ($relative in $pins.Keys) {
    $path = Join-Path $projectRoot $relative
    $item = Get-Item -LiteralPath $path -Force
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
        (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pins[$relative]) {
        throw 'The reviewed native coordinator differs; preserve the upgrade journal and use the exact delivery copy.'
    }
}
if ($VerifyOnly) { $Mode = 'verify' }
if (-not $Python) { $Python = Join-Path $projectRoot '.venv/Scripts/python.exe' }
$arguments = @('-B', (Join-Path $projectRoot 'scripts/release/upgrade_main201.py'), $Mode, '--project', $projectRoot, '--python', $Python)
if ($Node) { $arguments += @('--node', $Node) }
if ($PowerShell) { $arguments += @('--powershell', $PowerShell) }
& $Python @arguments
if ($LASTEXITCODE -ne 0) { throw 'Native lifecycle action stopped; inspect its preserved journal and private logs.' }
