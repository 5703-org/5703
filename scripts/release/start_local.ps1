param(
    [switch]$Install,
    [switch]$UseExistingDatabase,
    [int]$DatabasePort = 15532,
    [int]$ApiPort = 18000,
    [int]$FrontendPort = 15173,
    [ValidateSet('auto','cpu','cuda','cuda:0','mps')]
    [string]$Device = 'auto'
)
function Set-PortableOwnerOnlyAclWithIcacls([string]$Path, [Security.Principal.SecurityIdentifier]$Identity, [switch]$Directory) {
    # Some user-owned install directories grant Modify without WRITE_DAC. The
    # owner can use the Windows ACL utility to add their rule before removing
    # inherited rules; no credential file is created until this succeeds.
    $icacls = Join-Path ([Environment]::SystemDirectory) 'icacls.exe'
    $grant = '*' + $Identity.Value + $(if ($Directory) { ':(OI)(CI)F' } else { ':F' })
    & $icacls $Path '/grant:r' $grant | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not grant owner-only credential access.' }
    & $icacls $Path '/inheritance:r' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not remove inherited credential access.' }
}

function Protect-PortableCredentialPath([string]$Path, [switch]$Directory) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
    if ($Directory) {
        $acl = New-Object Security.AccessControl.DirectorySecurity
        $inheritance = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
        $rule = New-Object Security.AccessControl.FileSystemAccessRule($identity, 'FullControl', $inheritance, 'None', 'Allow')
    } else {
        $acl = New-Object Security.AccessControl.FileSecurity
        $rule = New-Object Security.AccessControl.FileSystemAccessRule($identity, 'FullControl', 'Allow')
    }
    $acl.SetAccessRuleProtection($true, $false)
    $acl.SetOwner($identity)
    $acl.AddAccessRule($rule)
    $item = if ($Directory) { New-Object IO.DirectoryInfo($Path) } else { New-Object IO.FileInfo($Path) }
    try {
        if ($PSVersionTable.PSEdition -eq 'Core') {
            [IO.FileSystemAclExtensions]::SetAccessControl($item, $acl)
        } else {
            $item.SetAccessControl($acl)
        }
    } catch {
        $denied = $_.Exception -is [UnauthorizedAccessException] -or
            $_.Exception -is [Security.SecurityException] -or
            $_.Exception.InnerException -is [UnauthorizedAccessException] -or
            $_.Exception.InnerException -is [Security.SecurityException]
        if (-not $denied) { throw }
        Set-PortableOwnerOnlyAclWithIcacls -Path $Path -Identity $identity -Directory:$Directory
    }
    $verified = if ($PSVersionTable.PSEdition -eq 'Core') {
        [IO.FileSystemAclExtensions]::GetAccessControl($item)
    } else {
        $item.GetAccessControl()
    }
    $rules = @($verified.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
    $full = [int][Security.AccessControl.FileSystemRights]::FullControl
    if (-not $verified.AreAccessRulesProtected -or
        $verified.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $identity.Value -or
        $rules.Count -ne 1 -or $rules[0].IdentityReference.Value -ne $identity.Value -or
        $rules[0].AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
        (($rules[0].FileSystemRights -band $full) -ne $full)) {
        throw 'The private credential path cannot be limited to the current Windows user.'
    }
}

function Read-PortableInitialPassword([string]$Path) {
    $value = $null
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        try {
            Protect-PortableCredentialPath -Path $Path
            $value = [IO.File]::ReadAllText($Path).Trim()
            break
        } catch [IO.IOException] { Start-Sleep -Milliseconds 50 }
    }
    if ($null -eq $value) { throw 'The private initial credential file is busy. Retry this launch.' }
    if ($value -notmatch '^[0-9a-f]{48}$') { throw 'The private initial credential file is invalid.' }
    return $value
}

function Get-PortableInitialPassword([string]$Path) {
    $directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    # Set inheritance before creating a plaintext file, including on Windows PowerShell 5.1.
    Protect-PortableCredentialPath -Path $directory -Directory
    if (Test-Path -LiteralPath $Path) { return Read-PortableInitialPassword -Path $Path }
    $random = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $bytes = New-Object byte[] 24
        $random.GetBytes($bytes)
        $candidate = ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
    } finally { $random.Dispose() }
    try {
        # CreateNew prevents a concurrent launcher from replacing the winning credential.
        $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    } catch [IO.IOException] {
        if (-not (Test-Path -LiteralPath $Path)) { throw }
        # The other launcher may still hold its short exclusive write handle.
        return Read-PortableInitialPassword -Path $Path
    }
    try {
        $content = [Text.Encoding]::UTF8.GetBytes($candidate + [Environment]::NewLine)
        $stream.Write($content, 0, $content.Length)
        $stream.Flush()
    } finally { $stream.Dispose() }
    return Read-PortableInitialPassword -Path $Path
}

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
Set-Location -LiteralPath $projectRoot
# This launcher owns a fresh process environment. Configuration comes from this
# installation's .env, never an inherited development database or provider key.
Get-ChildItem Env: | Where-Object { $_.Name -match '^(DATABASE_URL|POSTGRES_.*|APP_ENV|SECRET_KEY|STORAGE_ROOT|ALLOWED_ORIGINS|LLM_.*|MODEL_.*|CHAT_RETRIEVAL_CONFIG|TIKTOKEN_CACHE_DIR)$' } | ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
Remove-Item Env:CS30_PORTABLE_INITIAL_PASSWORD -ErrorAction SilentlyContinue
$env:PYTHONPATH = '.;backend'
$env:PYTHONUTF8 = '1'
$env:HF_HUB_OFFLINE = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
$env:TIKTOKEN_CACHE_DIR = './artifacts/tiktoken'
$python = Join-Path $projectRoot '.venv/Scripts/python.exe'
$resourceManifest = Join-Path $projectRoot 'resources/official-corpus/MANIFEST.json'
$pathDigest = [Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($projectRoot.ToLowerInvariant()))
$installationId = ([BitConverter]::ToString($pathDigest)).Replace('-','').Substring(0,12).ToLowerInvariant()
$composeProject = 'cs30-portable-' + $installationId
if (-not (Test-Path -LiteralPath $resourceManifest)) {
    throw 'The full package resources are missing. Use the complete runnable package.'
}
if ($Install) {
    if (-not (Test-Path -LiteralPath $python)) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.13 is required.' }
    }
    $embeddingLock = if ($Device -like 'cuda*') { 'requirements-embeddings.lock' } else { 'requirements-embeddings-cpu.lock' }
    & $python -m pip install -r requirements.lock -r $embeddingLock
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    Push-Location frontend
    try {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed.' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
}
if (-not (Test-Path -LiteralPath $python)) { throw 'Run this script with -Install first.' }
$settingsNames = & $python -c "from app.core.config import Settings; from pydantic import AliasChoices; names=set(Settings.model_fields); [names.update(f.validation_alias.choices if isinstance(f.validation_alias,AliasChoices) else [f.validation_alias]) for f in Settings.model_fields.values() if f.validation_alias]; print('\n'.join(sorted(names)))"
if ($LASTEXITCODE -ne 0) { throw 'Settings preflight failed.' }
foreach ($settingName in $settingsNames) { Remove-Item -LiteralPath ('Env:' + $settingName) -ErrorAction SilentlyContinue }
$env:LOCAL_MODEL_DEVICE = $Device
& $python -c "import sys,json; from retrieval.runtime import resolve_device; assert sys.version_info[:2] == (3,13), 'Python 3.13 is required'; print(json.dumps({'local_model_policy':sys.argv[1],'resolved_device':resolve_device(sys.argv[1])}))" "$Device"
if ($LASTEXITCODE -ne 0) { throw 'Local model preflight failed. Check the dependencies or select -Device cpu.' }
if ($UseExistingDatabase -and -not (Test-Path -LiteralPath '.env')) {
    throw 'Create this installation''s .env with the intended local PostgreSQL URL before using -UseExistingDatabase.'
}
if (-not (Test-Path -LiteralPath '.env')) {
    $jwtSecret = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    $databasePassword = [guid]::NewGuid().ToString('N')
    @"
APP_ENV=dev
MODEL_MODE=mock
DATABASE_URL=postgresql+psycopg://learning:$databasePassword@127.0.0.1:$DatabasePort/learning
POSTGRES_PASSWORD=$databasePassword
POSTGRES_PORT=$DatabasePort
SECRET_KEY=$jwtSecret
STORAGE_ROOT=./artifacts/storage
ALLOWED_ORIGINS=http://127.0.0.1:$FrontendPort,http://localhost:$FrontendPort
LLM_PROVIDER=mock
LLM_MODEL=authored-extractive-v1
LLM_API_KEY=
MODEL_CONFIG_KEY_FILE=./.secrets/model-config.key
CHAT_RETRIEVAL_CONFIG=./configs/retrieval/chat_hybrid_minilm.json
LOCAL_MODEL_DEVICE=$Device
TIKTOKEN_CACHE_DIR=./artifacts/tiktoken
"@ | Set-Content -LiteralPath '.env' -Encoding utf8
}
& $python -c "from dotenv import dotenv_values; from sqlalchemy.engine import make_url; import sys; e=dotenv_values('.env',encoding='utf-8-sig'); u=make_url(e.get('DATABASE_URL','')); external=sys.argv[2]=='True'; assert u.drivername=='postgresql+psycopg' and u.host=='127.0.0.1' and u.port==int(sys.argv[1]) and bool(u.database) and bool(u.username), 'Portable database must match the selected explicit local port'; assert external or (u.database=='learning' and u.username=='learning' and e.get('POSTGRES_PORT')==sys.argv[1] and u.password==e.get('POSTGRES_PASSWORD') and bool(u.password)), 'Portable database credentials/port disagree with Compose'; assert e.get('STORAGE_ROOT')=='./artifacts/storage', 'Portable source storage must remain inside this installation'" "$DatabasePort" "$UseExistingDatabase"
if ($LASTEXITCODE -ne 0) { throw 'Portable configuration validation failed before any database change.' }
if (-not $UseExistingDatabase) {
    $ownedDatabase = docker ps --filter "label=com.docker.compose.project=$composeProject" --filter 'label=com.docker.compose.service=db' --format '{{.ID}}'
    if ((Get-NetTCPConnection -LocalPort $DatabasePort -State Listen -ErrorAction SilentlyContinue) -and -not $ownedDatabase) {
        throw "Database port $DatabasePort is occupied by another installation. Select a free -DatabasePort for a new installation."
    }
    docker compose --env-file .env -p $composeProject -f compose.yaml up -d db --wait
    if ($LASTEXITCODE -ne 0) { throw 'The isolated PostgreSQL service did not start.' }
}
& $python -m app.cli migrate
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
$documentCount = & $python -c "from app.core.config import Settings; from sqlalchemy import create_engine,text; e=create_engine(Settings().database_url); c=e.connect(); print(c.scalar(text('SELECT count(*) FROM documents'))); c.close(); e.dispose()"
if ($LASTEXITCODE -ne 0 -or $documentCount -notmatch '^\d+$') { throw 'Corpus preflight failed.' }
$initialPasswordFile = Join-Path $projectRoot '.secrets/initial-admin-password.txt'
if ([int64]$documentCount -eq 0) {
    $portableInitialPassword = Get-PortableInitialPassword -Path $initialPasswordFile
    $env:CS30_PORTABLE_INITIAL_PASSWORD = $portableInitialPassword
}
try {
    $corpusOutput = & $python -m scripts.release.install_corpus --path resources/official-corpus
    if ($LASTEXITCODE -ne 0) { throw 'Corpus installation or integrity verification failed.' }
} finally {
    Remove-Item Env:CS30_PORTABLE_INITIAL_PASSWORD -ErrorAction SilentlyContinue
    $portableInitialPassword = $null
}
$corpusReceipt = ($corpusOutput | Out-String | ConvertFrom-Json)
# Import verified review candidates after source storage is installed. This command is
# idempotent; candidate regions remain unpublished and any integrity failure stops startup.
& $python -m scripts.verify.import_visual_regions --catalog-dir evidence/week09-continuation/20260930/visual-full-attempt2 --import
if ($LASTEXITCODE -ne 0) { throw 'Visual candidate installation or integrity verification failed.' }
$initialPasswordMatches = $false
if (Test-Path -LiteralPath $initialPasswordFile) {
    Protect-PortableCredentialPath -Path (Split-Path -Parent $initialPasswordFile) -Directory
    $privateCredential = Read-PortableInitialPassword -Path $initialPasswordFile
    $privateCredential = $null
    $credentialMatch = & $python -c "from pathlib import Path; import sys; from app.cli import initial_admin_password_matches; from app.core.config import Settings; from sqlalchemy import create_engine; from sqlalchemy.orm import Session; e=create_engine(Settings().database_url); db=Session(e); print(int(initial_admin_password_matches(db,Path(sys.argv[1]).read_text(encoding='utf-8').strip()))); db.close(); e.dispose()" "$initialPasswordFile"
    if ($LASTEXITCODE -ne 0 -or $credentialMatch -notmatch '^[01]$') { throw 'Initial administrator credential verification failed.' }
    $initialPasswordMatches = $credentialMatch -eq '1'
}
$runtimeDir = Join-Path $projectRoot 'artifacts/runtime'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
foreach ($port in @($ApiPort, $FrontendPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Existing services have been left running."
    }
}
$apiProcess = Start-Process -FilePath $python -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$ApiPort" -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'api.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'api.stderr.log') -PassThru
$workerProcess = Start-Process -FilePath $python -ArgumentList '-m','app.worker','--queue','interactive' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'worker.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'worker.stderr.log') -PassThru
$backgroundWorkerProcess = Start-Process -FilePath $python -ArgumentList '-m','app.worker','--queue','background' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'worker-background.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'worker-background.stderr.log') -PassThru
$env:API_PROXY_URL = "http://127.0.0.1:$ApiPort"
$node = (Get-Command node).Source
$frontendRoot = Join-Path $projectRoot 'frontend'
$webProcess = Start-Process -FilePath $node -ArgumentList 'node_modules/vite/bin/vite.js','--configLoader','runner','--host','127.0.0.1','--port',"$FrontendPort" -WorkingDirectory $frontendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'frontend.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'frontend.stderr.log') -PassThru
[PSCustomObject]@{ApiPid=$apiProcess.Id;WorkerPid=$workerProcess.Id;BackgroundWorkerPid=$backgroundWorkerProcess.Id;FrontendPid=$webProcess.Id;ApiPort=$ApiPort;FrontendPort=$FrontendPort;DatabasePort=$DatabasePort;ComposeProject=$composeProject;ProjectRoot=$projectRoot} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeDir 'processes.json') -Encoding utf8
$deadline = [DateTime]::UtcNow.AddSeconds(30)
$ready = $false
while ([DateTime]::UtcNow -lt $deadline) {
    try {
        $health = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$ApiPort/ready" -TimeoutSec 2
        $frontendHealth = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$FrontendPort" -TimeoutSec 2
        $workerAlive = Get-Process -Id $workerProcess.Id -ErrorAction SilentlyContinue
        $backgroundWorkerAlive = Get-Process -Id $backgroundWorkerProcess.Id -ErrorAction SilentlyContinue
        if ($health.StatusCode -eq 200 -and $frontendHealth.StatusCode -eq 200 -and $workerAlive -and $backgroundWorkerAlive) { $ready = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 500
}
if (-not $ready) { throw "Startup did not pass health checks. Inspect $runtimeDir and the recorded process IDs; existing services were not stopped." }
Write-Output "Open http://127.0.0.1:$FrontendPort. Local administrator: admin@example.com."
if ($initialPasswordMatches) { Write-Output "Initial local account password: $initialPasswordFile. Change the password in Your account after first login." }
Write-Output 'The bundled corpus uses real E5 vectors. Configure and test a provider in Administration > Models to enable live answers.'
