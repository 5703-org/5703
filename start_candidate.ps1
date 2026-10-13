param(
    [switch]$Install,
    [switch]$UseExistingDatabase,
    [int]$DatabasePort = 15532,
    [int]$ApiPort = 18000,
    [int]$FrontendPort = 15173,
    [ValidateSet('auto','cpu','cuda','cuda:0','mps')]
    [string]$Device = 'auto',
    [switch]$IncludeOptionalModelAssets
)
$ErrorActionPreference = 'Stop'
$candidateRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$rootItem = Get-Item -LiteralPath $candidateRoot -Force
if (($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'Use a normal fresh extraction directory; reparse roots are refused.'
}
$hydrator = Join-Path $candidateRoot 'scripts/release/hydrate_public_model_assets.py'
$mainLauncher = Join-Path $candidateRoot 'scripts/release/start_local.ps1'
foreach ($publicFile in @($hydrator, $mainLauncher)) {
    $item = Get-Item -LiteralPath $publicFile -Force
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'The candidate startup requires ordinary public script files.'
    }
}
if ((Get-FileHash -LiteralPath $mainLauncher -Algorithm SHA256).Hash.ToLowerInvariant() -ne '34e37bf9aa78da6ad30d566a5ab49d12103d706348719154934e9fd680c27e3e') {
    throw 'Original Main startup source differs; no startup action was taken.'
}
if ((Get-FileHash -LiteralPath $hydrator -Algorithm SHA256).Hash.ToLowerInvariant() -ne '8cda4a9ea0e6561d75c0fbb6f3cb363e713a17a5b0b0a4532ef3e290d7dbe86a') {
    throw 'Public model hydration helper differs; no startup action was taken.'
}
# System Python is available before -Install creates the package virtualenv.
$pythonApplication = Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1
$systemPython = $pythonApplication.Source
& $systemPython -I -B -S -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Install host Python 3.13 before launching this candidate.' }
$hydrateArguments = @('-I','-B','-S',$hydrator,'--project-root',$candidateRoot)
if ($IncludeOptionalModelAssets) { $hydrateArguments += '--include-optional' }
& $systemPython @hydrateArguments
if ($LASTEXITCODE -ne 0) { throw 'Public model assets could not be hydrated; original startup was not invoked.' }
$mainArguments = @{DatabasePort=$DatabasePort; ApiPort=$ApiPort; FrontendPort=$FrontendPort; Device=$Device}
if ($Install) { $mainArguments.Install = $true }
if ($UseExistingDatabase) { $mainArguments.UseExistingDatabase = $true }
# This wrapper changes no Main source or scientific configuration. The original
# launcher performs its documented fresh-install dependency/DB/service actions.
& $mainLauncher @mainArguments
