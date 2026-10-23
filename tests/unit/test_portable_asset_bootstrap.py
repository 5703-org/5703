"""Public cache restoration and the actual pre-provisioning launcher branch."""

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from scripts.release.hydrate_public_model_assets import HydrationError, _relative, hydrate

ROOT = Path(__file__).resolve().parents[2]


def fixture_bundle(root):
    assets = []
    for i in range(26):
        name = "README.md" if i == 0 else f"asset{i}.bin"
        source = f"resources/model-assets/{name}"
        data = f"Authored public asset fixture {i}".encode()
        p = root / source
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        assets.append(
            {
                "asset": source,
                "target": f"artifacts/huggingface/snapshot/{name}",
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "optional": i >= 23,
            }
        )
    manifest = {
        "format": "cs30-public-model-assets-v1",
        "assets": assets,
        "empty_markers": [
            {
                "target": f"artifacts/huggingface/.no_exist/rev/m{i}",
                "bytes": 0,
                "sha256": hashlib.sha256(b"").hexdigest(),
                "optional": False,
                "derived": True,
            }
            for i in range(4)
        ],
        "derived_files": [
            {**assets[0], "target": "artifacts/huggingface/blobs/readme", "derived": True}
        ],
    }
    raw = json.dumps(manifest).encode()
    (root / "resources/model-assets/MANIFEST.json").write_bytes(raw)
    return manifest, hashlib.sha256(raw).hexdigest()


def test_hydrate_then_verify_and_repeat_preserve_exact_targets(tmp_path):
    manifest, pin = fixture_bundle(tmp_path)
    first = hydrate(tmp_path, expected_manifest_sha256=pin)
    assert len(first["created"]) == 28
    assert first["network_DB_key_or_Gold_access"] is False
    assert first["delete_or_replace_actions"] == 0
    for row in manifest["assets"][:23]:
        assert (tmp_path / row["target"]).read_bytes() == (tmp_path / row["asset"]).read_bytes()
    assert not (tmp_path / manifest["assets"][23]["target"]).exists()
    assert hydrate(tmp_path, verify_only=True, expected_manifest_sha256=pin)["created"] == []
    assert hydrate(tmp_path, expected_manifest_sha256=pin)["created"] == []


def test_corrupt_source_fails_before_creating_any_runtime_file(tmp_path):
    manifest, pin = fixture_bundle(tmp_path)
    source = tmp_path / manifest["assets"][25]["asset"]
    source.write_bytes(b"x" * source.stat().st_size)
    with pytest.raises(HydrationError, match="SOURCE_HASH_MISMATCH"):
        hydrate(tmp_path, expected_manifest_sha256=pin)
    assert not (tmp_path / "artifacts").exists()


def test_existing_different_target_is_preserved_without_partial_new_outputs(tmp_path):
    manifest, pin = fixture_bundle(tmp_path)
    target = tmp_path / manifest["assets"][3]["target"]
    target.parent.mkdir(parents=True)
    existing = b"x" * manifest["assets"][3]["bytes"]
    target.write_bytes(existing)
    with pytest.raises(HydrationError, match="EXISTING_TARGET_DIFFERS"):
        hydrate(tmp_path, expected_manifest_sha256=pin)
    assert target.read_bytes() == existing
    assert not (tmp_path / manifest["assets"][0]["target"]).exists()


@pytest.mark.parametrize(
    "path", ["../escape", ".secrets/key", ".env", "C:/outside", "artifacts/a.db"]
)
def test_public_asset_path_rejects_escape_and_private_targets(path):
    with pytest.raises(HydrationError):
        _relative(path)


PS_BRANCH = r"""
param([string]$Source,[string]$Project,[int]$StubExit)
$ErrorActionPreference='Stop'
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Launcher parse failed'}
$statements=@($ast.EndBlock.Statements);$selected=@()
for($i=0;$i -lt $statements.Count;$i++){
 if($statements[$i] -is [Management.Automation.Language.AssignmentStatementAst] -and
    $statements[$i].Left.VariablePath.UserPath -eq 'publicAssetManifest'){
   $selected=@($statements[$i],$statements[$i+1]);break
 }
}
if($selected.Count -ne 2){throw 'Missing actual asset branch'}
$migrate=$ast.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.Extent.Text -match 'app\.cli migrate'},$true)
if($migrate.Count -ne 1 -or $selected[1].Extent.EndOffset -ge $migrate[0].Extent.StartOffset){throw 'Asset branch must precede migration'}
$projectRoot=$Project;$fixtureScriptRoot=Join-Path $Project 'scripts/release';$python='Invoke-FakePython'
$script:calls=0;$script:callArgs=@()
function Invoke-FakePython {$script:calls++;$script:callArgs=@($args);$global:LASTEXITCODE=$StubExit}
$failure=$null
# An extracted AST has no original file scope. Rebind only its script-directory
# automatic variable, while executing the unchanged condition/command/exit guard.
try {foreach($s in $selected){Invoke-Expression ($s.Extent.Text.Replace('$PSScriptRoot','$fixtureScriptRoot'))}}catch{$failure=$_.Exception.Message}
@{calls=$script:calls;args=$script:callArgs;failure=$failure}|ConvertTo-Json -Compress
"""


@pytest.mark.parametrize("mode", ["no_manifest", "missing_helper", "success", "helper_failure"])
@pytest.mark.skipif(os.name != "nt", reason="Actual Windows PowerShell launcher AST")
def test_actual_launcher_asset_branch_is_gated_and_fail_closed(tmp_path, mode):
    script = tmp_path / "scripts/release/branch.ps1"
    script.parent.mkdir(parents=True)
    script.write_text(PS_BRANCH, encoding="utf-8")
    if mode != "no_manifest":
        path = tmp_path / "resources/model-assets/MANIFEST.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("authored stub", encoding="utf-8")
    if mode in {"success", "helper_failure"}:
        path = tmp_path / "scripts/release/hydrate_public_model_assets.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("authored stub never executed", encoding="utf-8")
    ps = (
        Path(os.environ.get("SystemRoot", r"C:\Windows"))
        / "System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    result = subprocess.run(
        [
            str(ps),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-Source",
            str(ROOT / "scripts/release/start_local.ps1"),
            "-Project",
            str(tmp_path),
            "-StubExit",
            "1" if mode == "helper_failure" else "0",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["calls"] == (1 if mode in {"success", "helper_failure"} else 0), output
    assert bool(output["failure"]) == (mode in {"missing_helper", "helper_failure"})
    if output["calls"]:
        assert output["args"][-2:] == ["--project-root", str(tmp_path)]
