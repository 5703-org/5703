"""Exercise the actual portable readiness statements with authored local probes.

The native PowerShell child only evaluates the extracted policy preflight and
readiness AST. It never evaluates provisioning or process-launch statements.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "scripts/release/start_local.ps1"
POLICY_MODULE = "scripts.release.startup_policy"
WINDOWS = pytest.mark.skipif(sys.platform != "win32", reason="Native Windows PowerShell 5.1")
POWERSHELL = Path(os.environ.get("SystemRoot", r"C:\Windows")) / (
    "System32/WindowsPowerShell/v1.0/powershell.exe"
)
PRIVATE_SENTINEL = "AUTHORED_PRIVATE_INPUT_MUST_NOT_APPEAR_180"

PS_RUNNER = r"""
param([string]$Source, [string]$Python, [string]$ScenarioPath)
$ErrorActionPreference = 'Stop'
$scenario = Get-Content -LiteralPath $ScenarioPath -Raw | ConvertFrom-Json
$tokens = $null; $parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($Source, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'The actual launcher failed PowerShell parsing.' }
$statements = @($ast.EndBlock.Statements)
$deadlineIndices = @()
$producerIndices = @()
for ($i = 0; $i -lt $statements.Count; $i++) {
    $statement = $statements[$i]
    if ($statement -is [Management.Automation.Language.AssignmentStatementAst]) {
        if ($statement.Left.VariablePath.UserPath -eq 'deadline') { $deadlineIndices += $i }
        if ($statement.Left.VariablePath.UserPath -eq 'startupTimeoutSeconds') {
            if ($statement.Extent.Text -match '&\s*\$python\s+-m\s+scripts\.release\.startup_policy') {
                $producerIndices += $i
            }
        }
    }
}
if ($deadlineIndices.Count -ne 1) { throw 'Expected exactly one actual deadline assignment.' }
$index = $deadlineIndices[0]
$selected = @($statements[$index..($index + 3)])
if ($selected[1] -isnot [Management.Automation.Language.AssignmentStatementAst] -or
    $selected[1].Left.VariablePath.UserPath -ne 'ready' -or
    $selected[2] -isnot [Management.Automation.Language.WhileStatementAst] -or
    $selected[3] -isnot [Management.Automation.Language.IfStatementAst] -or
    $selected[3].Extent.Text -notmatch 'Startup did not pass health checks') {
    throw 'The actual readiness statement shape changed; review the fixture.'
}
$sourceText = [IO.File]::ReadAllText($Source)
$tailStart = $selected[0].Extent.StartOffset
$tailEnd = $selected[3].Extent.EndOffset
$readinessText = $sourceText.Substring($tailStart, $tailEnd - $tailStart)
$clockCount = [regex]::Matches($readinessText, '\[DateTime\]::UtcNow').Count
if ($clockCount -ne 2) { throw 'Expected exactly two static UTC clock reads.' }
if ($readinessText -match 'Start-Process|docker|migrate|import_bundle') {
    throw 'Provisioning or launch statements must not enter the readiness fixture.'
}
$readinessText = $readinessText.Replace('[DateTime]::UtcNow', '(Get-StartupTestUtcNow)')
$producerText = $null
if ($producerIndices.Count -gt 1) { throw 'Unexpected duplicate startup policy producer.' }
if ($producerIndices.Count -eq 1) {
    $p = $producerIndices[0]
    if ($statements[$p + 1] -isnot [Management.Automation.Language.IfStatementAst] -or
        $statements[$p + 1].Extent.Text -notmatch '\$LASTEXITCODE' -or
        $statements[$p + 2] -isnot [Management.Automation.Language.AssignmentStatementAst] -or
        $statements[$p + 2].Left.VariablePath.UserPath -ne 'startupTimeoutSeconds' -or
        $statements[$p + 2].Extent.Text -notmatch '\[double\]') {
        throw 'Expected the actual policy exit guard and numeric conversion before provisioning.'
    }
    $producerText = $sourceText.Substring($statements[$p].Extent.StartOffset,
        $statements[$p + 2].Extent.EndOffset - $statements[$p].Extent.StartOffset)
    if ($p -ge $index) { throw 'Policy validation must precede readiness.' }
    $provisioning = @($ast.FindAll({param($node)
        $node -is [Management.Automation.Language.CommandAst] -and
        $node.Extent.Text -match 'docker compose .*up|\$python -m app\.cli migrate'
    }, $true))
    if ($provisioning.Count -lt 2) { throw 'Expected the actual database provisioning commands.' }
    foreach ($command in $provisioning) {
        if ($statements[$p + 2].Extent.EndOffset -ge $command.Extent.StartOffset) {
            throw 'Policy validation and numeric conversion must precede database provisioning.'
        }
    }
}

$script:epoch = [DateTime]::SpecifyKind([DateTime]'2026-01-01', [DateTimeKind]::Utc)
$script:logicalSeconds = 0.0
$script:probeCalls = New-Object 'Collections.Generic.List[object]'
$script:processCalls = New-Object 'Collections.Generic.List[int]'
$script:sleepCalls = 0
$ApiPort = 19081; $FrontendPort = 19082
$workerProcess = [pscustomobject]@{Id=111}
$backgroundWorkerProcess = [pscustomobject]@{Id=222}
$runtimeDir = 'AUTHORED-NO-SERVICE-RUNTIME'
$python = $Python
function Get-StartupTestUtcNow { return $script:epoch.AddSeconds($script:logicalSeconds) }
function Start-Sleep {
    param([int]$Milliseconds)
    if ($Milliseconds -ne 500) { throw 'Unexpected sleep in the actual readiness branch.' }
    $script:logicalSeconds += 0.5
    $script:sleepCalls += 1
    if ($script:sleepCalls -gt 1800) { throw 'Logical fixture finite guard exceeded.' }
}
function Invoke-WebRequest {
    param([switch]$UseBasicParsing, [string]$Uri, [int]$TimeoutSec)
    if (-not $UseBasicParsing -or $TimeoutSec -ne 2) { throw 'Unexpected actual probe arguments.' }
    if ($Uri -eq 'http://127.0.0.1:19081/ready') {
        [void]$script:probeCalls.Add([pscustomobject]@{kind='api'; at=$script:logicalSeconds})
        if ($scenario.api_mode -eq 'exception') { throw 'AUTHORED API probe exception' }
        $status = 503
        if ($scenario.api_mode -ne 'permanent503' -and
            $script:logicalSeconds -ge [double]$scenario.ready_after) { $status = 200 }
        return [pscustomobject]@{StatusCode=$status}
    }
    if ($Uri -eq 'http://127.0.0.1:19082') {
        [void]$script:probeCalls.Add([pscustomobject]@{kind='frontend'; at=$script:logicalSeconds})
        return [pscustomobject]@{StatusCode=[int]$scenario.frontend_status}
    }
    throw 'Unexpected URI; real HTTP is forbidden in this fixture.'
}
function Get-Process {
    param([int]$Id, [string]$ErrorAction)
    if ($Id -notin @(111,222)) { throw 'Unexpected PID; real process lookup is forbidden.' }
    [void]$script:processCalls.Add($Id)
    if ($Id -eq [int]$scenario.dead_pid) { return $null }
    return [pscustomobject]@{Id=$Id; Authored=$true}
}
function Start-Process { throw 'Process launch is forbidden in the extracted fixture.' }

$ready = $false; $loopEntered = $false; $failure = $null; $policyExit = $null
try {
    if ($producerText) {
        Invoke-Expression $producerText
        $policyExit = $LASTEXITCODE
    }
    $loopEntered = $true
    Invoke-Expression $readinessText
} catch { $failure = $_.Exception.Message }
$deadlineSeconds = $null
if ($null -ne $deadline) { $deadlineSeconds = ($deadline - $script:epoch).TotalSeconds }
@{
    powershell_version=$PSVersionTable.PSVersion.ToString(); clock_replacements=$clockCount;
    producer_present=($null -ne $producerText); policy_exit=$policyExit;
    policy_output=$startupTimeoutSeconds; ready=[bool]$ready; loop_entered=$loopEntered;
    logical_seconds=$script:logicalSeconds; deadline_seconds=$deadlineSeconds;
    sleep_calls=$script:sleepCalls; probes=@($script:probeCalls.ToArray());
    process_ids=@($script:processCalls.ToArray()); error=$failure
} | ConvertTo-Json -Depth 8 -Compress
"""


def isolated_environment():
    """Retain Windows runtime plumbing, never inherited application settings."""
    names = {
        "systemroot",
        "windir",
        "comspec",
        "path",
        "pathext",
        "temp",
        "tmp",
        "userprofile",
        "appdata",
        "localappdata",
        "programfiles",
        "programfiles(x86)",
        "programdata",
        "number_of_processors",
        "processor_architecture",
        "homedrive",
        "homepath",
        "os",
    }
    env = {key: value for key, value in os.environ.items() if key.lower() in names}
    env.update(
        {
            "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "backend"))),
            "PYTHONUTF8": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
        }
    )
    return env


def synthetic_settings(directory, overrides=None):
    values = {
        "APP_ENV": "test",
        "DATABASE_URL": "postgresql+psycopg://127.0.0.1:19999/authored_fixture180",
        "SECRET_KEY": "authored-startup-fixture-only-secret-180",
    }
    values.update(overrides or {})
    (directory / ".env").write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8"
    )


def run_readiness(tmp_path, *, overrides=None, **scenario_changes):
    synthetic_settings(tmp_path, overrides)
    scenario = {"ready_after": 0, "api_mode": "ready_after", "frontend_status": 200, "dead_pid": 0}
    scenario.update(scenario_changes)
    runner = tmp_path / "readiness.ps1"
    runner.write_text(PS_RUNNER, encoding="utf-8")
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")
    before = hashlib.sha256(LAUNCHER.read_bytes()).hexdigest()
    started = time.monotonic()
    result = subprocess.run(
        [
            str(POWERSHELL),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(runner),
            "-Source",
            str(LAUNCHER),
            "-Python",
            sys.executable,
            "-ScenarioPath",
            str(scenario_path),
        ],
        cwd=tmp_path,
        env=isolated_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        check=False,
    )
    assert hashlib.sha256(LAUNCHER.read_bytes()).hexdigest() == before, "Launcher changed mid-test"
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout.strip().splitlines()[-1])
    assert receipt["powershell_version"].startswith("5.1."), receipt
    assert receipt["clock_replacements"] == 2
    assert set(receipt["process_ids"]).issubset({111, 222})
    receipt["real_elapsed_seconds"] = time.monotonic() - started
    receipt["native_stderr"] = result.stderr
    receipt["launcher_sha256"] = before
    (tmp_path / "readiness-result.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


@WINDOWS
def test_default_late_ready_waits_for_valid_prewarm(tmp_path):
    result = run_readiness(tmp_path, ready_after=48.5)
    assert result["ready"], result
    assert result["producer_present"] and result["policy_exit"] == 0, result
    assert result["deadline_seconds"] == 90
    assert result["logical_seconds"] == 48.5
    assert result["real_elapsed_seconds"] < 20


@WINDOWS
@pytest.mark.parametrize(
    ("timeout", "ready_after", "budget"), [("180", 195, 210), ("1.5", 31, 31.5)]
)
def test_configured_prewarm_budget_includes_process_grace(tmp_path, timeout, ready_after, budget):
    result = run_readiness(
        tmp_path, overrides={"WORKER_PREWARM_TIMEOUT_SECONDS": timeout}, ready_after=ready_after
    )
    assert result["ready"], result
    assert result["deadline_seconds"] == budget
    assert result["logical_seconds"] == ready_after


@WINDOWS
@pytest.mark.parametrize("flag", ["WORKER_PREWARM_RETRIEVAL_CACHE", "CHAT_RETRIEVAL_CACHE"])
def test_each_disabled_cache_retains_only_process_grace(tmp_path, flag):
    result = run_readiness(tmp_path, overrides={flag: "false"}, ready_after=31)
    assert not result["ready"] and result["loop_entered"], result
    assert result["deadline_seconds"] == result["logical_seconds"] == 30
    assert "Startup did not pass health checks" in result["error"]


@WINDOWS
def test_sqlite_has_no_postgresql_worker_prewarm_budget(tmp_path):
    result = run_readiness(
        tmp_path, overrides={"DATABASE_URL": "sqlite:///:memory:"}, ready_after=31
    )
    assert not result["ready"] and result["loop_entered"], result
    assert result["deadline_seconds"] == result["logical_seconds"] == 30


@WINDOWS
@pytest.mark.parametrize(
    "scenario",
    [
        {"api_mode": "permanent503"},
        {"api_mode": "exception"},
        {"frontend_status": 503},
        {"dead_pid": 111},
        {"dead_pid": 222},
    ],
    ids=["api503", "api-exception", "frontend-unready", "interactive-dead", "background-dead"],
)
def test_unready_controls_retain_actual_probe_and_process_gates(tmp_path, scenario):
    result = run_readiness(tmp_path, overrides={"WORKER_PREWARM_TIMEOUT_SECONDS": "1"}, **scenario)
    assert not result["ready"] and result["loop_entered"], result
    assert result["logical_seconds"] == result["deadline_seconds"] == 31
    assert result["sleep_calls"] == 62
    assert "Startup did not pass health checks" in result["error"]
    assert result["probes"], result


@WINDOWS
@pytest.mark.parametrize("invalid", ["NaN", "181"])
def test_invalid_settings_reject_before_readiness_probes(tmp_path, invalid):
    result = run_readiness(tmp_path, overrides={"WORKER_PREWARM_TIMEOUT_SECONDS": invalid})
    assert result["producer_present"], result
    assert not result["loop_entered"] and not result["ready"], result
    assert result["logical_seconds"] == 0 and not result["probes"]
    assert not result["process_ids"]


def test_policy_cli_does_not_expose_invalid_settings_input(tmp_path):
    synthetic_settings(tmp_path, {"WORKER_PREWARM_TIMEOUT_SECONDS": PRIVATE_SENTINEL})
    result = subprocess.run(
        [sys.executable, "-B", "-m", POLICY_MODULE],
        cwd=tmp_path,
        env=isolated_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert PRIVATE_SENTINEL not in result.stderr
    assert "ValidationError" in result.stderr
    assert "Traceback" not in result.stderr
    assert len(result.stderr) < 180
