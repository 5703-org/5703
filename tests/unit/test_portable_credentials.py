"""Portable credential persistence and native Windows launcher boundaries."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.cli import initial_admin_password_matches, seed
from app.core.security import verify_password
from app.db.base import Base
from app.modules.identity.models import Role, StudentProfile, User, Workspace
from app.modules.knowledge.models import ActiveCorpus, Configuration, Document
from scripts.release.common import file_hash
from scripts.release.corpus_bundle import import_bundle

ROOT = Path(__file__).resolve().parents[2]
TEST_PASSWORD = "a" * 48


@pytest.fixture
def local_accounts(tmp_path):
    url = f"sqlite:///{(tmp_path / 'accounts.sqlite').as_posix()}"
    engine = create_engine(url)
    Base.metadata.create_all(
        engine,
        tables=[
            Base.metadata.tables[item.__tablename__]
            for item in (
                Workspace,
                Role,
                User,
                StudentProfile,
                Configuration,
                ActiveCorpus,
                Document,
            )
        ],
    )
    try:
        yield engine, SimpleNamespace(database_url=url, storage_root=tmp_path / "storage")
    finally:
        engine.dispose()


def failing_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    data = bundle / "rows.jsonl.gz"
    data.write_bytes(gzip.compress(b"invalid corpus row\n"))
    (bundle / "MANIFEST.json").write_text(
        json.dumps(
            {
                "schema": "official-corpus-bundle-v1",
                "data": {"path": data.name, "sha256": file_hash(data)},
                "files": [],
            }
        ),
        encoding="utf-8",
    )
    return bundle


def test_failed_corpus_import_keeps_one_reusable_private_credential(
    local_accounts, tmp_path, monkeypatch
):
    engine, settings = local_accounts
    bundle = failing_bundle(tmp_path)
    monkeypatch.setenv("CS30_PORTABLE_INITIAL_PASSWORD", TEST_PASSWORD)
    stored_hash = None
    for _ in range(2):
        with pytest.raises(json.JSONDecodeError):
            import_bundle(bundle, settings)
        with Session(engine) as db:
            admin = db.scalar(select(User).where(User.email == "admin@example.com"))
            assert admin is not None
            assert initial_admin_password_matches(db, TEST_PASSWORD)
            assert not verify_password("Passw0rd!", admin.hashed_password)
            assert db.scalar(select(func.count()).select_from(User)) == 3
            assert db.scalar(select(func.count()).select_from(Document)) == 0
            if stored_hash is not None:
                assert admin.hashed_password == stored_hash
            stored_hash = admin.hashed_password


@pytest.mark.parametrize("changed", ["password", "status", "role"])
def test_seed_retry_preserves_existing_admin_and_does_not_offer_wrong_password(
    local_accounts, changed
):
    engine, _ = local_accounts
    with Session(engine) as db:
        seed(db, initial_password=TEST_PASSWORD)
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        if changed == "status":
            admin.status = "deactivated"
        if changed == "role":
            admin.role_id = db.scalars(select(Role.id).where(Role.name == "student")).one()
        admin.token_version = 7
        db.commit()
        before = (admin.hashed_password, admin.status, admin.role_id, admin.token_version)
        seed(db, initial_password="b" * 48)
        db.expire_all()
        assert (admin.hashed_password, admin.status, admin.role_id, admin.token_version) == before
        assert not initial_admin_password_matches(db, "b" * 48)
        assert initial_admin_password_matches(db, TEST_PASSWORD) == (changed == "password")


@pytest.mark.parametrize("changed", ["status", "role"])
def test_corpus_import_requires_active_admin_without_promoting_existing_account(
    local_accounts, tmp_path, monkeypatch, changed
):
    engine, settings = local_accounts
    bundle = failing_bundle(tmp_path)
    monkeypatch.setenv("CS30_PORTABLE_INITIAL_PASSWORD", TEST_PASSWORD)
    with Session(engine) as db:
        seed(db, initial_password=TEST_PASSWORD)
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        if changed == "status":
            admin.status = "deactivated"
        else:
            admin.role_id = db.scalars(select(Role.id).where(Role.name == "student")).one()
        db.commit()
        before = (admin.hashed_password, admin.status, admin.role_id)
        with pytest.raises(ValueError, match="active local administrator"):
            import_bundle(bundle, settings)
        db.expire_all()
        assert (admin.hashed_password, admin.status, admin.role_id) == before


WINDOWS = pytest.mark.skipif(sys.platform != "win32", reason="Native Windows ACL contract")
PS_SCRIPT = r"""
param([string]$Source, [string]$Credential, [string]$Mode)
$ErrorActionPreference = 'Stop'
$tokens = $null; $errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($Source, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'Launcher PowerShell parsing failed.' }
$functions = $ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst]}, $true)
foreach ($definition in $functions) { Invoke-Expression $definition.Extent.Text }
if ($Mode -eq 'fallback') {
    $directory = Split-Path -Parent $Credential
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    Set-PortableOwnerOnlyAclWithIcacls -Path $directory -Identity $sid -Directory
    [IO.File]::WriteAllText($Credential, 'authored ACL test data')
    Set-PortableOwnerOnlyAclWithIcacls -Path $Credential -Identity $sid
    $directoryAcl = [IO.Directory]::GetAccessControl($directory)
    $fileAcl = [IO.File]::GetAccessControl($Credential)
    $directoryRules = @($directoryAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
    $fileRules = @($fileAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
    @{
        directory_protected=$directoryAcl.AreAccessRulesProtected;
        file_protected=$fileAcl.AreAccessRulesProtected;
        directory_owner_only=($directoryRules.Count -eq 1 -and $directoryRules[0].IdentityReference.Value -eq $sid.Value);
        file_owner_only=($fileRules.Count -eq 1 -and $fileRules[0].IdentityReference.Value -eq $sid.Value)
    } | ConvertTo-Json -Compress
    exit
}
if ($Mode -eq 'invalid') {
    $original = [IO.File]::ReadAllText($Credential)
    $rejected = $false
    try { $null = Get-PortableInitialPassword -Path $Credential } catch { $rejected = $_.Exception.Message -eq 'The private initial credential file is invalid.' }
    @{rejected=$rejected; unchanged=($original -ceq [IO.File]::ReadAllText($Credential))} | ConvertTo-Json -Compress
    exit
}
$first = Get-PortableInitialPassword -Path $Credential
if ($Mode -eq 'parallel') {
    $hash = [Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($first)))).Replace('-','') } finally { $hash.Dispose() }
    exit
}
$second = Get-PortableInitialPassword -Path $Credential
$other = Get-PortableInitialPassword -Path ($Credential + '.other')
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$fileAcl = [IO.File]::GetAccessControl($Credential)
$directoryAcl = [IO.Directory]::GetAccessControl((Split-Path -Parent $Credential))
$rules = @($fileAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
$directoryRules = @($directoryAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
@{
    version=$PSVersionTable.PSVersion.ToString(); format=($first -match '^[0-9a-f]{48}$'); reused=($first -ceq $second);
    independent=($first -cne $other); file_protected=$fileAcl.AreAccessRulesProtected;
    directory_protected=$directoryAcl.AreAccessRulesProtected;
    file_owner_only=($rules.Count -eq 1 -and $rules[0].IdentityReference.Value -eq $sid);
    directory_owner_only=($directoryRules.Count -eq 1 -and $directoryRules[0].IdentityReference.Value -eq $sid)
} | ConvertTo-Json -Compress
"""


def run_powershell(runner, credential, mode):
    result = subprocess.run(
        [
            shutil.which("powershell.exe") or "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(runner),
            str(ROOT / "scripts/release/start_local.ps1"),
            str(credential),
            mode,
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@WINDOWS
def test_windows_powershell51_credential_retry_and_owner_only_acl(tmp_path):
    runner = tmp_path / "probe.ps1"
    runner.write_text(PS_SCRIPT, encoding="utf-8")
    result = json.loads(run_powershell(runner, tmp_path / ".secrets/password.txt", "inspect"))
    assert result.pop("version").startswith("5.1.")
    assert all(result.values()), result


@WINDOWS
def test_concurrent_launchers_never_overwrite_winning_credential(tmp_path):
    runner = tmp_path / "probe.ps1"
    runner.write_text(PS_SCRIPT, encoding="utf-8")
    credential = tmp_path / ".secrets/password.txt"
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: run_powershell(runner, credential, "parallel"), range(4)))
    assert len(set(results)) == 1
    assert len(results[0]) == 64


@WINDOWS
def test_invalid_existing_credential_is_preserved_and_rejected(tmp_path):
    runner = tmp_path / "probe.ps1"
    runner.write_text(PS_SCRIPT, encoding="utf-8")
    credential = tmp_path / ".secrets/password.txt"
    credential.parent.mkdir()
    credential.write_text("invalid authored test credential", encoding="utf-8")
    assert json.loads(run_powershell(runner, credential, "invalid")) == {
        "rejected": True,
        "unchanged": True,
    }


@WINDOWS
def test_icacls_fallback_protects_directory_and_file_before_secret_write(tmp_path):
    runner = tmp_path / "probe.ps1"
    runner.write_text(PS_SCRIPT, encoding="utf-8")
    result = json.loads(run_powershell(runner, tmp_path / ".secrets/password.txt", "fallback"))
    assert all(result.values()), result
