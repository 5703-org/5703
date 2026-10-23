param(
    [switch]$Plan,
    [switch]$Install
)

# Default execution validates source files and prints a plan. It never invokes
# Python/npm, creates an environment, downloads dependencies or starts services.
$ErrorActionPreference = 'Stop'
if ($Plan -and $Install) { throw 'Choose either -Plan or -Install.' }
$dependencyInstallRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$dependencyInstallPrefix = $dependencyInstallRoot.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
$requirementRows = [Collections.Generic.List[object]]::new()
$requirementVisited = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$requirementActive = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

function Get-SourceFile([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($dependencyInstallPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'A dependency input escaped this source installation.'
    }
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "Required source file is missing: $full" }
    $current = Get-Item -LiteralPath $full -Force
    while ($current) {
        if (($current.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Dependency inputs must be regular source files/directories: $full"
        }
        if ($current.FullName -eq $dependencyInstallRoot) { break }
        $current = if ($current -is [IO.FileInfo]) { $current.Directory } else { $current.Parent }
    }
    return Get-Item -LiteralPath $full -Force
}

function Get-InputRow([string]$Path) {
    $file = Get-SourceFile $Path
    $algorithm = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($file.FullName)
    try { $hash = ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $algorithm.Dispose() }
    return [ordered]@{
        path = $file.FullName.Substring($dependencyInstallPrefix.Length).Replace('\', '/')
        bytes = $file.Length
        sha256 = $hash
    }
}

function Add-RequirementFile([string]$Path) {
    $file = Get-SourceFile $Path
    if ($requirementActive.Contains($file.FullName)) { throw 'A requirements include cycle was found.' }
    if ($requirementVisited.Contains($file.FullName)) { return }
    [void]$requirementActive.Add($file.FullName)
    $includes = [Collections.Generic.List[string]]::new()
    foreach ($raw in [IO.File]::ReadAllLines($file.FullName)) {
        $line = ($raw -split '#', 2)[0].Trim()
        $reference = $null
        if ($line -match '^--(?:requirement|constraint)(?:=|\s+)(.+)$') { $reference = $Matches[1].Trim() }
        elseif ($line -match '^-[rc]\s*(.+)$') { $reference = $Matches[1].Trim() }
        if ($null -eq $reference) { continue }
        if (($reference.StartsWith('"') -and $reference.EndsWith('"')) -or
            ($reference.StartsWith("'") -and $reference.EndsWith("'"))) {
            $reference = $reference.Substring(1, $reference.Length - 2)
        }
        if (-not $reference -or [IO.Path]::IsPathRooted($reference) -or $reference -match '^[A-Za-z][A-Za-z0-9+.-]*:') {
            throw 'Requirements includes must be confined relative source paths.'
        }
        $included = [IO.Path]::GetFullPath((Join-Path $file.DirectoryName $reference))
        [void]$includes.Add((Get-InputRow $included).path)
        Add-RequirementFile $included
    }
    [void]$requirementActive.Remove($file.FullName)
    [void]$requirementVisited.Add($file.FullName)
    $row = Get-InputRow $file.FullName
    $row['includes'] = @($includes.ToArray())
    [void]$requirementRows.Add($row)
}

foreach ($name in @('requirements.lock', 'requirements-embeddings-cpu.lock', 'requirements-embeddings.lock', 'requirements-embeddings-linux.lock')) {
    Add-RequirementFile (Join-Path $dependencyInstallRoot $name)
}
$frontendRoot = Join-Path $dependencyInstallRoot 'frontend'
$frontendFiles = @('package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.ts', 'index.html', 'playwright.config.ts', 'src/main.tsx', 'src/App.tsx', 'src/generated/api.ts')
$frontendRows = @($frontendFiles | ForEach-Object { Get-InputRow (Join-Path $frontendRoot $_) })
$nativePreflightRow = Get-InputRow (Join-Path $dependencyInstallRoot 'scripts/release/native_preflight.py')
$package = [IO.File]::ReadAllText((Join-Path $frontendRoot 'package.json')) | ConvertFrom-Json
$lockRaw = [IO.File]::ReadAllText((Join-Path $frontendRoot 'package-lock.json'))
# Windows PowerShell 5.1 rejects npm's legitimate empty root-package JSON key.
# Rename that one key in the parser view only; npm reads the unchanged lockfile.
$rootPackagePattern = '("packages"\s*:\s*\{\s*)""\s*:'
if ([regex]::Matches($lockRaw, $rootPackagePattern).Count -ne 1 -or $lockRaw.Contains('"__source_install_root_package__"')) {
    throw 'The npm lock root-package structure changed; review the input.'
}
$lockForPlan = [regex]::Replace($lockRaw, $rootPackagePattern, '$1"__source_install_root_package__":')
$lock = $lockForPlan | ConvertFrom-Json
if ($lock.lockfileVersion -ne 3 -or $package.name -ne $lock.name) { throw 'The frontend package and lockfile identities disagree.' }
foreach ($kind in @('dependencies', 'devDependencies')) {
    $declared = @($package.$kind.PSObject.Properties)
    $locked = $lock.packages.__source_install_root_package__.$kind
    if ($declared.Count -ne @($locked.PSObject.Properties).Count) { throw 'The frontend package and lock dependency sets disagree.' }
    foreach ($entry in $declared) {
        if ($entry.Value -ne $locked.($entry.Name)) { throw 'The frontend package and lock dependency versions disagree.' }
    }
}
if ($package.scripts.build -ne 'tsc --noEmit && vite build') { throw 'The frontend build command changed; review the install plan before executing it.' }
$frontendSourceFiles = @(Get-ChildItem -LiteralPath (Join-Path $frontendRoot 'src') -Recurse -File)
if ($frontendSourceFiles.Count -lt 1 -or $frontendSourceFiles.Count -gt 2000) { throw 'The frontend source inventory is missing or unexpectedly large.' }
foreach ($file in $frontendSourceFiles) { [void](Get-SourceFile $file.FullName) }
$report = [ordered]@{
    schema = 'windows_source_dependency_install_v1'
    mode = $(if ($Install) { 'Install' } else { 'Plan' })
    source_root = $dependencyInstallRoot
    requirements = @($requirementRows.ToArray())
    frontend_inputs = $frontendRows
    native_import_preflight_input = $nativePreflightRow
    frontend_source_files = $frontendSourceFiles.Count
    python_required = '3.13.x'
    node_required_by_current_locked_tooling = '22.12.x or later in 22.x; 24.x; or >=26.0.0'
    commands_for_future_explicit_install = @(
        'py -3.13 -m venv .venv (or a version-checked Python 3.13 executable)',
        '.venv/Scripts/python.exe -m pip install -r requirements.lock -r requirements-embeddings-cpu.lock',
        '.venv/Scripts/python.exe -B scripts/release/native_preflight.py (bounded torch and pymupdf imports)',
        'npm ci --include=dev (working directory: frontend)',
        'npm run build (working directory: frontend)'
    )
    existing_venv = (Test-Path -LiteralPath (Join-Path $dependencyInstallRoot '.venv'))
    existing_node_modules = (Test-Path -LiteralPath (Join-Path $frontendRoot 'node_modules'))
    assets_checked_or_installed = $false
    configuration_or_credentials_read_or_written = $false
    services_started = 0
    dependency_downloads_executed = 0
}
if (-not $Install) {
    $report['status'] = 'PLAN_VALIDATED_NO_INSTALL'
    $report | ConvertTo-Json -Depth 8
    return
}

# Installation is an explicit, network-using action for a fresh source tree.
# Never let npm ci erase a borrowed or previously installed dependency tree.
if ($report.existing_venv -or $report.existing_node_modules) {
    throw 'Explicit installation requires a fresh tree without .venv or frontend/node_modules. Preserve an earlier partial installation and inspect it separately.'
}
$nodeCommand = Get-Command node -CommandType Application -ErrorAction Stop
$npmCommand = Get-Command npm.cmd -CommandType Application -ErrorAction Stop
$nodeText = & $nodeCommand.Source -p 'process.versions.node'
if ($LASTEXITCODE -ne 0) { throw 'Node version detection failed.' }
$nodeVersion = [version]($nodeText | Select-Object -Last 1)
if (-not (($nodeVersion.Major -eq 22 -and $nodeVersion.Minor -ge 12) -or $nodeVersion.Major -eq 24 -or $nodeVersion.Major -ge 26)) {
    throw 'Node does not satisfy the current locked Vite/Vitest/jsdom requirements. See WINDOWS_SOURCE_INSTALL.md.'
}
$pythonLauncher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue
$pythonArguments = @()
if ($pythonLauncher) { $pythonArguments = @('-3.13') }
else { $pythonLauncher = Get-Command python -CommandType Application -ErrorAction Stop }
& $pythonLauncher.Source @pythonArguments -c 'import sys; assert sys.version_info[:2] == (3, 13)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.13 preflight failed.' }
Push-Location -LiteralPath $dependencyInstallRoot
try {
    & $pythonLauncher.Source @pythonArguments -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    $venvPython = Join-Path $dependencyInstallRoot '.venv/Scripts/python.exe'
    & $venvPython -m pip install -r requirements.lock -r requirements-embeddings-cpu.lock
    if ($LASTEXITCODE -ne 0) { throw 'Locked Python/CPU dependency installation failed.' }
    & $venvPython -B (Join-Path $PSScriptRoot 'native_preflight.py')
    if ($LASTEXITCODE -ne 0) { throw 'Installed native dependency imports failed. Follow the reported module/runtime guidance; no database or service was started.' }
    Push-Location -LiteralPath $frontendRoot
    try {
        & $npmCommand.Source ci --include=dev
        if ($LASTEXITCODE -ne 0) { throw 'Locked frontend dependency installation failed.' }
        & $npmCommand.Source run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend typecheck/build failed.' }
    } finally { Pop-Location }
} finally { Pop-Location }
Write-Output 'Dependencies installed, native imports and frontend build passed. No database, configuration, corpus import or server was started. Follow WINDOWS_SOURCE_INSTALL.md for the separate runtime prerequisites.'
