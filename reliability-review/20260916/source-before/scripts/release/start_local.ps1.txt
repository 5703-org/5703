param(
    [switch]$Install,
    [int]$DatabasePort = 15532,
    [int]$ApiPort = 18000,
    [int]$FrontendPort = 15173
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
Set-Location -LiteralPath $projectRoot
# This launcher owns a fresh process environment. Configuration comes from this
# installation's .env, never an inherited development database or provider key.
Get-ChildItem Env: | Where-Object { $_.Name -match '^(DATABASE_URL|POSTGRES_.*|APP_ENV|SECRET_KEY|STORAGE_ROOT|ALLOWED_ORIGINS|LLM_.*|MODEL_.*|CHAT_RETRIEVAL_CONFIG|TIKTOKEN_CACHE_DIR)$' } | ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
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
    & $python -m pip install -r requirements.lock -r requirements-embeddings.lock
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
& $python -c "import sys,torch; assert sys.version_info[:2] == (3,13), 'Python 3.13 is required'; assert torch.cuda.is_available(), 'The bundled immutable E5 release requires an NVIDIA CUDA device. No model/device substitution was made.'"
if ($LASTEXITCODE -ne 0) { throw 'Runtime preflight failed. Check Python 3.13 and the NVIDIA driver.' }
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
TIKTOKEN_CACHE_DIR=./artifacts/tiktoken
"@ | Set-Content -LiteralPath '.env' -Encoding utf8
}
& $python -c "from dotenv import dotenv_values; from sqlalchemy.engine import make_url; import sys; e=dotenv_values('.env',encoding='utf-8-sig'); u=make_url(e.get('DATABASE_URL','')); assert u.drivername=='postgresql+psycopg' and u.host=='127.0.0.1' and u.port==int(sys.argv[1]) and u.database=='learning' and u.username=='learning', 'Portable database must match the selected local port and learning database'; assert e.get('POSTGRES_PORT')==sys.argv[1] and u.password==e.get('POSTGRES_PASSWORD') and bool(u.password), 'Portable database credentials/port disagree with Compose'; assert e.get('STORAGE_ROOT')=='./artifacts/storage', 'Portable source storage must remain inside this installation'" "$DatabasePort"
if ($LASTEXITCODE -ne 0) { throw 'Portable configuration validation failed before any database change.' }
$ownedDatabase = docker ps --filter "label=com.docker.compose.project=$composeProject" --filter 'label=com.docker.compose.service=db' --format '{{.ID}}'
if ((Get-NetTCPConnection -LocalPort $DatabasePort -State Listen -ErrorAction SilentlyContinue) -and -not $ownedDatabase) {
    throw "Database port $DatabasePort is occupied by another installation. Select a free -DatabasePort for a new installation."
}
docker compose --env-file .env -p $composeProject -f compose.yaml up -d db --wait
if ($LASTEXITCODE -ne 0) { throw 'The isolated PostgreSQL service did not start.' }
& $python -m app.cli migrate
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
& $python -m scripts.release.install_corpus --path resources/official-corpus
if ($LASTEXITCODE -ne 0) { throw 'Corpus installation or integrity verification failed.' }
$runtimeDir = Join-Path $projectRoot 'artifacts/runtime'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
foreach ($port in @($ApiPort, $FrontendPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Existing services have been left running."
    }
}
$apiProcess = Start-Process -FilePath $python -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$ApiPort" -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'api.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'api.stderr.log') -PassThru
$workerProcess = Start-Process -FilePath $python -ArgumentList '-m','app.worker' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'worker.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'worker.stderr.log') -PassThru
$env:API_PROXY_URL = "http://127.0.0.1:$ApiPort"
$node = (Get-Command node).Source
$frontendRoot = Join-Path $projectRoot 'frontend'
$webProcess = Start-Process -FilePath $node -ArgumentList 'node_modules/vite/bin/vite.js','--configLoader','runner','--host','127.0.0.1','--port',"$FrontendPort" -WorkingDirectory $frontendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'frontend.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'frontend.stderr.log') -PassThru
[PSCustomObject]@{ApiPid=$apiProcess.Id;WorkerPid=$workerProcess.Id;FrontendPid=$webProcess.Id;ApiPort=$ApiPort;FrontendPort=$FrontendPort;DatabasePort=$DatabasePort;ComposeProject=$composeProject;ProjectRoot=$projectRoot} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeDir 'processes.json') -Encoding utf8
$deadline = [DateTime]::UtcNow.AddSeconds(30)
$ready = $false
while ([DateTime]::UtcNow -lt $deadline) {
    try {
        $health = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$ApiPort/ready" -TimeoutSec 2
        $frontendHealth = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$FrontendPort" -TimeoutSec 2
        $workerAlive = Get-Process -Id $workerProcess.Id -ErrorAction SilentlyContinue
        if ($health.StatusCode -eq 200 -and $frontendHealth.StatusCode -eq 200 -and $workerAlive) { $ready = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 500
}
if (-not $ready) { throw "Startup did not pass health checks. Inspect $runtimeDir and the recorded process IDs; existing services were not stopped." }
Write-Output "Open http://127.0.0.1:$FrontendPort. Local administrator: admin@example.com / Passw0rd!. Change your password in Your account; manage other users in Administration > Accounts."
Write-Output 'The bundled corpus uses real E5 vectors. Configure and test a provider in Administration > Models to enable live answers.'
