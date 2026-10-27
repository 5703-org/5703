"""Native dependency failures must stop startup honestly without exposing raw output."""

import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "windows_native_preflight", ROOT / "scripts/release/native_preflight.py"
)
N = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(N)


def failed_import(error):
    def call(module):
        raise error

    return call


def child_result(module, *, status="passed", exit_code=0, **updates):
    value = {
        "schema": N.PROTOCOL,
        "module": module,
        "status": status,
        "python_bits": struct.calcsize("P") * 8,
        "version": "synthetic",
    }
    value.update(updates)
    return subprocess.CompletedProcess(
        [], exit_code, stdout=json.dumps(value).encode(), stderr=b"PRIVATE_STDERR"
    )


def test_cpu_has_no_dependency_bypass_and_imports_both_in_isolated_bounded_children():
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return child_result(argv[-1])

    result = N.check_native_imports(runner=run)
    assert result["status"] == "PASS_NATIVE_IMPORTS"
    assert [a[-1] for a, _ in calls] == ["torch", "pymupdf"]
    assert all(a[1:3] == ["-I", "-B"] and k["timeout"] == 20 for a, k in calls)
    assert "PRIVATE_STDERR" not in json.dumps(result)


def test_missing_selected_module_names_the_missing_install_without_runtime_claim():
    row = N.probe_in_process(
        "torch", importer=failed_import(ModuleNotFoundError("private", name="torch"))
    )
    assert row["status"] == "failed" and row["code"] == "NATIVE_MODULE_MISSING"
    assert "not installed" in row["message"] and "official_runtime_help" not in row


def test_missing_python_dependency_is_not_misdiagnosed_as_visual_cpp():
    row = N.probe_in_process(
        "torch", importer=failed_import(ModuleNotFoundError("private", name="numpy"))
    )
    assert row["code"] == "NATIVE_DEPENDENCY_MISSING" and row["dependency"] == "numpy"
    assert "numpy" in row["message"] and "official_runtime_help" not in row


def test_dll_failure_keeps_useful_basename_and_winerror_without_full_private_path():
    error = OSError(
        "Error loading C:\\PRIVATE_USER\\SECRET_VALUE\\torch\\lib\\c10.dll or a dependency"
    )
    error.winerror = 126
    row = N.probe_in_process("torch", importer=failed_import(error))
    assert row["code"] == "NATIVE_LIBRARY_LOAD_FAILED" and row["winerror"] == 126
    assert row["native_file"] == "c10.dll" and row["official_runtime_help"] == N.VC_RUNTIME_HELP
    assert "Another dependent DLL" in row["message"]
    assert "PRIVATE_USER" not in json.dumps(row) and "SECRET_VALUE" not in json.dumps(row)


def test_pymupdf_extra_import_error_is_honest_failure_with_runtime_guidance():
    error = ImportError(
        "DLL load failed while importing _extra: PRIVATE_NATIVE_DETAIL", name="_extra"
    )
    row = N.probe_in_process("pymupdf", importer=failed_import(error))
    assert row["status"] == "failed" and row["dependency"] == "_extra"
    assert "component _extra" in row["message"] and "PRIVATE_NATIVE_DETAIL" not in json.dumps(row)


def test_unrelated_import_error_is_not_a_definite_dll_failure():
    row = N.probe_in_process(
        "torch", importer=failed_import(ImportError("cannot import PRIVATE_NAME"))
    )
    assert row["code"] == "NATIVE_IMPORT_FAILED" and "official_runtime_help" not in row
    assert "PRIVATE_NAME" not in json.dumps(row)


def test_success_means_actual_import_completed_with_observed_version(monkeypatch):
    seen = []
    monkeypatch.setattr(N.metadata, "version", lambda _: "fixed-test-version")
    row = N.probe_in_process("pymupdf", importer=seen.append)
    assert (
        seen == ["pymupdf"] and row["status"] == "passed" and row["version"] == "fixed-test-version"
    )


def test_unavailable_distribution_metadata_is_not_a_fabricated_version(monkeypatch):
    def absent(_):
        raise N.metadata.PackageNotFoundError

    monkeypatch.setattr(N.metadata, "version", absent)
    row = N.probe_in_process("pymupdf", importer=lambda _: None)
    assert row["status"] == "passed" and row["version"] is None


def test_timeout_is_failure_and_second_module_is_still_diagnosed():
    calls = []

    def run(argv, **kwargs):
        calls.append(argv[-1])
        if argv[-1] == "torch":
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output=b"PRIVATE_OUTPUT")
        return child_result("pymupdf")

    result = N.check_native_imports(timeout_seconds=2, runner=run)
    assert (
        calls == ["torch", "pymupdf"] and result["status"] == "NATIVE_DEPENDENCY_PREFLIGHT_FAILED"
    )
    assert result["checks"][0]["code"] == "NATIVE_IMPORT_TIMEOUT"
    assert result["checks"][1]["status"] == "passed" and "PRIVATE_OUTPUT" not in json.dumps(result)


@pytest.mark.parametrize("value", [0, -1, 31, float("inf"), float("nan"), True])
def test_unbounded_or_invalid_timeout_is_refused_before_subprocess(value):
    with pytest.raises(ValueError, match="timeout"):
        N.check_native_imports(
            timeout_seconds=value, runner=lambda *a, **k: pytest.fail("must not run")
        )


@pytest.mark.parametrize(
    "kind",
    [
        "invalid_json",
        "wrong_module",
        "failure_with_zero_exit",
        "passed_with_nonzero_exit",
        "missing_architecture",
    ],
)
def test_crash_or_inconsistent_child_protocol_cannot_report_success(kind):
    def run(argv, **kwargs):
        module = argv[-1]
        if kind == "invalid_json":
            return subprocess.CompletedProcess(
                argv, 1, stdout=b"PRIVATE_TRACEBACK", stderr=b"PRIVATE_STDERR"
            )
        if kind == "wrong_module":
            return child_result("other_module")
        if kind == "failure_with_zero_exit":
            return child_result(module, status="failed")
        if kind == "passed_with_nonzero_exit":
            return child_result(module, exit_code=1)
        return child_result(module, python_bits=None)

    result = N.check_native_imports(runner=run)
    assert result["status"] == "NATIVE_DEPENDENCY_PREFLIGHT_FAILED"
    assert all(x["code"] == "NATIVE_IMPORT_PROCESS_FAILED" for x in result["checks"])
    assert "PRIVATE_" not in json.dumps(result)


def test_cli_returns_failure_to_calling_launcher_without_mock_success(monkeypatch, capsys):
    monkeypatch.setattr(
        N, "check_native_imports", lambda **_: {"status": "NATIVE_DEPENDENCY_PREFLIGHT_FAILED"}
    )
    assert N.main([]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "NATIVE_DEPENDENCY_PREFLIGHT_FAILED"


def test_startup_and_install_consumers_fail_before_database_or_services():
    startup = (ROOT / "scripts/release/start_local.ps1").read_text(encoding="utf-8")
    installer = (ROOT / "scripts/release/install_windows_dependencies.ps1").read_text(
        encoding="utf-8"
    )
    native = startup.index("& $python -B (Join-Path $PSScriptRoot 'native_preflight.py')")
    assert (
        native
        < startup.index("from retrieval.runtime import resolve_device")
        < startup.index("-m app.cli migrate")
    )
    assert native < startup.index("if (-not $UseExistingDatabase)")
    assert native < startup.index("docker compose --env-file")
    assert (
        "if ($LASTEXITCODE -ne 0) { throw 'Native dependency preflight failed" in startup[native:]
    )
    native = installer.index("& $venvPython -B (Join-Path $PSScriptRoot 'native_preflight.py')")
    assert (
        installer.index("& $venvPython -m pip install")
        < native
        < installer.index("& $npmCommand.Source ci")
    )
    assert (
        "if ($LASTEXITCODE -ne 0) { throw 'Installed native dependency imports failed"
        in installer[native:]
    )


@pytest.fixture
def preferred_start(monkeypatch, tmp_path):
    source_spec = importlib.util.spec_from_file_location(
        "main201_source", ROOT / "scripts/release/main201_source.py"
    )
    source = importlib.util.module_from_spec(source_spec)
    monkeypatch.setitem(sys.modules, "main201_source", source)
    source_spec.loader.exec_module(source)
    spec = importlib.util.spec_from_file_location(
        "candidate_native_coordinator", ROOT / "scripts/release/upgrade_main201.py"
    )
    coordinator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coordinator)
    project = tmp_path / "owned project"
    python, node, powershell = (
        project / ".venv/Scripts/python.exe",
        project / "node.exe",
        project / "powershell.exe",
    )
    for path in (python, node, powershell):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic executable; never run")
    monkeypatch.setattr(coordinator, "os", SimpleNamespace(name="nt", fsync=os.fsync))
    monkeypatch.setattr(
        coordinator,
        "runtime_manifest",
        lambda *a, **k: {
            "api_port": 8000,
            "frontend_port": 5173,
            "database_identity": {"host": "127.0.0.1", "port": 15432, "database": "learning"},
        },
    )

    def forbidden(*args, **kwargs):
        pytest.fail(
            "Failed imports must not reach database inspection, migration or service launch"
        )

    monkeypatch.setattr(coordinator, "metadata", forbidden)
    monkeypatch.setattr(coordinator, "start_roles", forbidden)
    events = []
    kernel = SimpleNamespace(CloseHandle=lambda job: events.append(("closed", job)))
    monkeypatch.setattr(coordinator, "bounded_job", lambda process: (kernel, "owned-fake-job"))
    monkeypatch.setattr(
        coordinator,
        "terminate_bounded_job",
        lambda kernel, job: events.append(("waited-empty", job)),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "upgrade_main201.py",
            "start",
            "--project",
            str(project),
            "--python",
            str(python),
            "--node",
            str(node),
            "--powershell",
            str(powershell),
        ],
    )
    return coordinator, project, events


def failed_native_result():
    error = OSError("PRIVATE_PATH/config.env: could not load c10.dll")
    error.winerror = 126
    return N.check_native_imports(
        runner=lambda argv, **kwargs: subprocess.CompletedProcess(
            argv,
            1 if argv[-1] == "torch" else 0,
            stdout=json.dumps(
                N.probe_in_process("torch", importer=failed_import(error))
                if argv[-1] == "torch"
                else json.loads(child_result("pymupdf").stdout)
            ).encode(),
            stderr=b"PRIVATE_KEY_AND_STDERR",
        )
    )


def test_preferred_start_reports_typed_failure_and_durable_diagnosis_before_any_start(
    preferred_start, monkeypatch
):
    coordinator, project, events = preferred_start
    child = SimpleNamespace(
        returncode=1,
        communicate=lambda **kwargs: (
            json.dumps(failed_native_result()).encode(),
            b"PRIVATE_STDERR",
        ),
    )
    monkeypatch.setattr(coordinator.subprocess, "Popen", lambda *a, **k: child)
    with pytest.raises(RuntimeError) as failure:
        coordinator.main()
    message = str(failure.value)
    assert "NATIVE_LIBRARY_LOAD_FAILED" in message and "c10.dll" in message
    assert "WinError 126" in message and "native_preflight.py" in message
    paths = list((project / "artifacts/runtime").glob("native-preflight-*.json"))
    assert len(paths) == 1 and str(paths[0]) in message
    report = json.loads(paths[0].read_text())
    assert report["status"] == "NATIVE_DEPENDENCY_PREFLIGHT_FAILED"
    assert report["checks"][0]["code"] == "NATIVE_LIBRARY_LOAD_FAILED"
    assert "PRIVATE" not in json.dumps(report) + message
    assert events == [("waited-empty", "owned-fake-job"), ("closed", "owned-fake-job")]


@pytest.mark.parametrize(
    "kind", ["invalid_json", "wrong_schema", "wrong_module", "false_success", "unknown_failure"]
)
def test_preferred_start_rejects_untrusted_or_inconsistent_protocol(
    preferred_start, monkeypatch, kind
):
    coordinator, project, events = preferred_start
    value = failed_native_result()
    if kind == "wrong_schema":
        value["schema"] = "private-unapproved"
    if kind == "wrong_module":
        value["checks"][0]["module"] = "PRIVATE_MODULE"
    if kind == "false_success":
        value["status"] = "PASS_NATIVE_IMPORTS"
    if kind == "unknown_failure":
        value["checks"][0]["code"] = "PRIVATE_ARBITRARY_ERROR"
    raw = b"PRIVATE_TRACEBACK" if kind == "invalid_json" else json.dumps(value).encode()
    child = SimpleNamespace(
        returncode=1, communicate=lambda **kwargs: (raw, b"PRIVATE_SECRET_STDERR")
    )
    monkeypatch.setattr(coordinator.subprocess, "Popen", lambda *a, **k: child)
    with pytest.raises(RuntimeError, match="NATIVE_IMPORT_PROCESS_FAILED") as failure:
        coordinator.main()
    (path,) = (project / "artifacts/runtime").glob("native-preflight-*.json")
    report = json.loads(path.read_text())
    assert report["status"] != "PASS_NATIVE_IMPORTS" and report["checks"] == []
    assert "PRIVATE" not in str(failure.value) + path.read_text()
    assert events[-1] == ("closed", "owned-fake-job")


def test_native_diagnostic_reconstructs_only_safe_fields(preferred_start, monkeypatch):
    coordinator, project, events = preferred_start
    value = failed_native_result()
    value["api_key"] = value["checks"][0]["message"] = "PRIVATE_SECRET"
    value["checks"][0]["native_file"] = "C:/PRIVATE_PATH/c10.dll"
    value["checks"][0]["dependency"] = "PRIVATE SECRET"
    value["checks"][0]["official_runtime_help"] = "https://PRIVATE_SECRET.invalid"
    child = SimpleNamespace(
        returncode=1, communicate=lambda **kwargs: (json.dumps(value).encode(), b"PRIVATE_STDERR")
    )
    monkeypatch.setattr(coordinator.subprocess, "Popen", lambda *a, **k: child)
    with pytest.raises(RuntimeError) as failure:
        coordinator.main()
    (path,) = (project / "artifacts/runtime").glob("native-preflight-*.json")
    report = json.loads(path.read_text())
    assert report["checks"][0] == {
        "module": "torch",
        "status": "failed",
        "code": "NATIVE_LIBRARY_LOAD_FAILED",
        "winerror": 126,
    }
    assert report["official_runtime_help"] == N.VC_RUNTIME_HELP
    assert "PRIVATE" not in path.read_text() + str(failure.value)


def test_parent_timeout_records_unknown_module_completion_and_keeps_owned_cleanup(
    preferred_start, monkeypatch
):
    coordinator, project, events = preferred_start
    calls = []

    def communicate(timeout):
        calls.append(timeout)
        if len(calls) == 1:
            raise subprocess.TimeoutExpired("synthetic", timeout, output=b"PRIVATE_TIMEOUT_OUTPUT")
        return b"", b"PRIVATE_STDERR"

    monkeypatch.setattr(
        coordinator.subprocess, "Popen", lambda *a, **k: SimpleNamespace(communicate=communicate)
    )
    with pytest.raises(RuntimeError, match="NATIVE_IMPORT_TIMEOUT"):
        coordinator.main()
    (path,) = (project / "artifacts/runtime").glob("native-preflight-*.json")
    report = json.loads(path.read_text())
    assert report["code"] == "NATIVE_IMPORT_TIMEOUT" and report["checks"] == []
    assert calls == [55, 10] and events[-1] == ("closed", "owned-fake-job")
    assert events.count(("waited-empty", "owned-fake-job")) == 2
    assert "PRIVATE" not in path.read_text()


def test_failed_native_process_creation_still_has_sanitized_actionable_diagnosis(
    preferred_start, monkeypatch
):
    coordinator, project, events = preferred_start

    def fail(*args, **kwargs):
        raise OSError("PRIVATE_EXECUTABLE_DETAIL")

    monkeypatch.setattr(coordinator.subprocess, "Popen", fail)
    with pytest.raises(RuntimeError, match="NATIVE_IMPORT_PROCESS_FAILED") as failure:
        coordinator.main()
    (path,) = (project / "artifacts/runtime").glob("native-preflight-*.json")
    assert "Standalone:" in str(failure.value) and "PRIVATE" not in path.read_text() + str(
        failure.value
    )
    assert events == []


def test_successful_native_result_is_preserved_without_changing_command_stdout(
    preferred_start, monkeypatch
):
    coordinator, project, events = preferred_start
    value = N.check_native_imports(runner=lambda argv, **kwargs: child_result(argv[-1]))
    raw = json.dumps(value).encode()
    child = SimpleNamespace(
        returncode=0, communicate=lambda **kwargs: (raw, b"PRIVATE_IGNORED_STDERR")
    )
    monkeypatch.setattr(coordinator.subprocess, "Popen", lambda *a, **k: child)
    path = project / "artifacts/runtime/native-preflight-success.json"
    assert (
        coordinator.run(
            ["fixture-python", "-B", "native_preflight.py"], project, native_diagnostic=path
        )
        == raw.decode()
    )
    report = json.loads(path.read_text())
    assert report["status"] == "PASS_NATIVE_IMPORTS" and all(
        row["status"] == "passed" for row in report["checks"]
    )
    assert events[-1] == ("closed", "owned-fake-job") and "PRIVATE" not in path.read_text()


def test_diagnostic_write_never_overwrites_an_existing_file_and_prevents_start(
    preferred_start, monkeypatch
):
    coordinator, project, events = preferred_start
    path = project / "artifacts/runtime/native-preflight-existing.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"preserved pre-existing content")
    child = SimpleNamespace(
        returncode=1,
        communicate=lambda **kwargs: (json.dumps(failed_native_result()).encode(), b""),
    )
    monkeypatch.setattr(coordinator.subprocess, "Popen", lambda *a, **k: child)
    with pytest.raises(FileExistsError):
        coordinator.run(
            ["fixture-python", "-B", "native_preflight.py"], project, native_diagnostic=path
        )
    assert path.read_bytes() == b"preserved pre-existing content"
    assert events[-1] == ("closed", "owned-fake-job")


def test_other_command_failures_do_not_globally_expose_captured_output(
    preferred_start, monkeypatch, capsys
):
    coordinator, project, events = preferred_start
    child = SimpleNamespace(
        returncode=1,
        communicate=lambda **kwargs: (b"PRIVATE_CIM_OR_MODEL_OUTPUT", b"PRIVATE_STDERR"),
    )
    monkeypatch.setattr(coordinator.subprocess, "Popen", lambda *a, **k: child)
    with pytest.raises(RuntimeError, match="^BOUNDED_NATIVE_COMMAND_FAILED_ordinary.exe$"):
        coordinator.run(["ordinary.exe"], project)
    output = capsys.readouterr()
    assert output.out == output.err == ""
    assert not (project / "artifacts/runtime").exists()


@pytest.mark.parametrize(
    "code,dependency", [("NATIVE_MODULE_MISSING", "torch"), ("NATIVE_DEPENDENCY_MISSING", "numpy")]
)
def test_preferred_start_names_missing_dependency_and_selected_environment(
    preferred_start, monkeypatch, code, dependency
):
    coordinator, project, events = preferred_start
    value = failed_native_result()
    value["checks"][0].update(code=code, dependency=dependency)
    value["checks"][0].pop("native_file", None)
    value["checks"][0].pop("winerror", None)
    child = SimpleNamespace(
        returncode=1, communicate=lambda **kwargs: (json.dumps(value).encode(), b"PRIVATE_STDERR")
    )
    monkeypatch.setattr(coordinator.subprocess, "Popen", lambda *a, **k: child)
    with pytest.raises(RuntimeError) as failure:
        coordinator.main()
    assert code in str(failure.value) and dependency in str(failure.value)
    (path,) = (project / "artifacts/runtime").glob("native-preflight-*.json")
    report = json.loads(path.read_text())
    assert "locked Python dependencies" in report["next_step"]
    assert (
        report["standalone_command"].startswith("& '")
        and "owned project" in report["standalone_command"]
    )
    assert "official_runtime_help" not in report


@pytest.mark.parametrize("metadata_valid", [False, True])
def test_installed_release_rollback_checks_metadata_before_source_and_restores_after(
    preferred_start, monkeypatch, tmp_path, metadata_valid
):
    coordinator, project, events = preferred_start
    backup = tmp_path / "owned backup"
    (backup / "source").mkdir(parents=True)
    authority = {"path": str(tmp_path / "public-authority.json"), "sha256": "a" * 64}
    coordinator.S.write_new(
        backup / "PLAN.json", {"target": str(project), "source_authority": authority}
    )
    plan_pin = coordinator.S.pin(backup / "PLAN.json")
    coordinator.S.write_new(
        backup / "native-journal.json", {"project": str(project), "plan": plan_pin}
    )
    coordinator.S.write_new(
        backup / "source/journal.json", {"target": str(project), "payload_plan": plan_pin}
    )
    coordinator.S.write_new(backup / "release-update.json", {"synthetic": True})
    coordinator.S.write_new(
        project / coordinator.STATE,
        {
            "schema": "direct_native_managed_processes_v1",
            "project": str(project),
            "source_authority_sha256": authority["sha256"],
            "source_authority": authority,
            "status": "STOPPED",
            "families": [],
        },
    )
    monkeypatch.setattr(
        coordinator,
        "runtime_manifest",
        lambda *a, **k: {
            "api_port": 8000,
            "frontend_port": 5173,
            "source_authority": authority,
            "source_authority_sha256": authority["sha256"],
            "database_identity": {"host": "127.0.0.1", "port": 15432, "database": "learning"},
        },
    )
    monkeypatch.setattr(
        coordinator,
        "metadata",
        lambda *a, **k: {
            "pending_jobs": 0,
            "pending_requests": 0,
            "worker_locks": [],
            "answer_only_active_count": 0,
        },
    )
    calls = []

    def restore(target, folder, *, verify_only=False):
        assert target == project and folder == backup
        calls.append("metadata-preflight" if verify_only else "metadata-restore")
        if verify_only and not metadata_valid:
            raise RuntimeError("SYNTHETIC_PREVIOUS_METADATA_MISMATCH")
        return {"status": "checked" if verify_only else "restored"}

    def rollback(journal):
        assert journal == backup / "source/journal.json"
        calls.append("source-rollback")
        return {"status": "rolled-back"}

    monkeypatch.setattr(coordinator.S, "restore_previous_release", restore)
    monkeypatch.setattr(coordinator.S, "rollback", rollback)
    monkeypatch.setattr(coordinator, "ports_free", lambda *a: None)
    monkeypatch.setattr(coordinator, "target_processes_absent", lambda *a: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            *sys.argv[:1],
            "rollback-source",
            "--project",
            str(project),
            "--python",
            str(project / ".venv/Scripts/python.exe"),
            "--node",
            str(project / "node.exe"),
            "--powershell",
            str(project / "powershell.exe"),
            "--backup",
            str(backup),
        ],
    )
    if metadata_valid:
        coordinator.main()
        assert calls == ["metadata-preflight", "source-rollback", "metadata-restore"]
    else:
        with pytest.raises(RuntimeError, match="SYNTHETIC_PREVIOUS_METADATA_MISMATCH"):
            coordinator.main()
        assert calls == ["metadata-preflight"]
    assert events == []


@pytest.fixture
def installed_rollback(preferred_start, monkeypatch, tmp_path):
    """Model real public manifests and a stopped process family; execute no child or SQL."""
    _, project, _ = preferred_start
    spec = importlib.util.spec_from_file_location(
        "rollback_native_coordinator", ROOT / "scripts/release/upgrade_main201.py"
    )
    coordinator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coordinator)
    monkeypatch.setattr(coordinator, "os", SimpleNamespace(name="nt", fsync=os.fsync))
    source = project / "scripts/public.py"
    source.parent.mkdir()
    source.write_text("old public source\n")
    old_row = {
        "path": "scripts/public.py",
        **{k: coordinator.S.pin(source)[k] for k in ("bytes", "sha256")},
    }

    def release(row, sha):
        return {
            "schema": "direct_native_upgrade_release_v1",
            "source_rows": [row],
            "source_row_count": 1,
            "source_inventory_sha256": coordinator.S.inventory_hash([row]),
            "source_authority": {
                "path": str(tmp_path / (sha[0] + "-authority.json")),
                "sha256": sha,
            },
            "source_authority_sha256": sha,
            "migration_head": "synthetic-forward-head",
            "api_port": 8000,
            "frontend_port": 5173,
            "database_identity": {"host": "127.0.0.1", "port": 15432, "database": "synthetic_only"},
        }

    old = release(old_row, "a" * 64)
    coordinator.S.write_new(project / coordinator.RELEASE, old)
    baseline = coordinator.S.pin(project / coordinator.RELEASE)
    source.write_text("new public source\n")
    row = {
        "path": "scripts/public.py",
        **{k: coordinator.S.pin(source)[k] for k in ("bytes", "sha256")},
    }
    new = release(row, "b" * 64)
    backup = tmp_path / "exact installed backup"
    (backup / "source").mkdir(parents=True)
    coordinator.S.write_new(
        backup / "PLAN.json",
        {
            "target": str(project),
            "source_authority": new["source_authority"],
            "baseline_kind": "installed",
            "baseline_release": baseline,
        },
    )
    plan_pin = coordinator.S.pin(backup / "PLAN.json")
    coordinator.S.write_new(
        backup / "native-journal.json", {"project": str(project), "plan": plan_pin}
    )
    coordinator.S.write_new(
        backup / "source/journal.json", {"target": str(project), "payload_plan": plan_pin}
    )
    family = {"role": "api", "root_pid": 10, "members": [{"pid": 10, "created_filetime": 123}]}
    state = {
        "schema": "direct_native_managed_processes_v1",
        "project": str(project),
        "source_authority": old["source_authority"],
        "source_authority_sha256": old["source_authority_sha256"],
        "families": [family],
        "starts": [
            {"status": "RESUMED_OWNED_ROOT", "role": "api", "root_identity": family["members"][0]}
        ],
    }
    events = []

    def stopped(family, shell, state, save):
        family["status"] = "EXIT_CONFIRMED"
        state.setdefault("stops", []).append(
            {"pid": 10, "created_filetime": 123, "status": "EXIT_CONFIRMED"}
        )
        events.append("actual-family-exit")
        save()

    monkeypatch.setattr(coordinator, "stop_family", stopped)
    monkeypatch.setattr(coordinator, "validate_family", lambda *a: [])
    monkeypatch.setattr(coordinator, "ports_free", lambda *a: events.append("ports-clear"))
    monkeypatch.setattr(
        coordinator, "target_processes_absent", lambda *a: events.append("processes-clear")
    )
    monkeypatch.setattr(
        coordinator,
        "metadata",
        lambda *a, **k: {
            "pending_jobs": 0,
            "pending_requests": 0,
            "worker_locks": [],
            "answer_only_active_count": 0,
        },
    )

    def rollback(journal):
        assert journal == backup / "source/journal.json"
        events.append("source-rollback")
        source.write_text("old public source\n")
        return {"status": "rolled-back"}

    monkeypatch.setattr(coordinator.S, "rollback", rollback)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "upgrade_main201.py",
            "rollback-source",
            "--project",
            str(project),
            "--python",
            str(project / ".venv/Scripts/python.exe"),
            "--node",
            str(project / "node.exe"),
            "--powershell",
            str(project / "powershell.exe"),
            "--backup",
            str(backup),
        ],
    )
    return coordinator, project, backup, state, old, new, events


@pytest.mark.parametrize(
    "crash_window", ["before-metadata", "after-metadata-before-state", "after-new-state"]
)
def test_installed_rollback_preserves_exited_family_and_restores_startable_old_authority(
    installed_rollback, crash_window
):
    coordinator, project, backup, state, old, new, events = installed_rollback
    if crash_window != "before-metadata":
        coordinator.S.install_release(
            project, new, backup, coordinator.S.pin(project / coordinator.RELEASE)
        )
    if crash_window == "after-new-state":
        state.update(
            source_authority=new["source_authority"],
            source_authority_sha256=new["source_authority_sha256"],
        )
    coordinator.S.write_new(project / coordinator.STATE, state)
    coordinator.main()
    restored = coordinator.runtime_manifest(project)
    assert restored == old
    stopped = json.loads((project / coordinator.STATE).read_text())
    assert stopped["status"] == "STOPPED"
    assert stopped["source_authority"] == old["source_authority"]
    assert stopped["families"][0]["status"] == stopped["stops"][0]["status"] == "EXIT_CONFIRMED"
    assert stopped["families"][0]["members"] == state["families"][0]["members"]
    assert stopped["starts"] == state["starts"]
    assert (
        coordinator.normalize_managed_state(stopped, project, old["source_authority_sha256"])
        is stopped
    )
    assert (
        events.index("actual-family-exit")
        < events.index("ports-clear")
        < events.index("source-rollback")
    )


def test_rollback_rejects_third_authority_before_process_or_source_actions(installed_rollback):
    coordinator, project, backup, state, old, new, events = installed_rollback
    state.update(
        source_authority={"path": "unrelated", "sha256": "c" * 64}, source_authority_sha256="c" * 64
    )
    coordinator.S.write_new(project / coordinator.STATE, state)
    with pytest.raises(RuntimeError, match="MANAGED_STATE_RELEASE_AUTHORITY_MISMATCH"):
        coordinator.main()
    assert events == []


def test_normal_start_still_rejects_old_state_against_new_release(installed_rollback, monkeypatch):
    coordinator, project, backup, state, old, new, events = installed_rollback
    coordinator.S.install_release(
        project, new, backup, coordinator.S.pin(project / coordinator.RELEASE)
    )
    coordinator.S.write_new(project / coordinator.STATE, state)
    monkeypatch.setattr(sys, "argv", [*sys.argv[:1], "start", *sys.argv[2:]])
    with pytest.raises(RuntimeError, match="MANAGED_STATE_RELEASE_AUTHORITY_MISMATCH"):
        coordinator.main()
    assert events == []


def test_rollback_rejects_changed_successor_metadata_before_stopping_old_family(installed_rollback):
    coordinator, project, backup, state, old, new, events = installed_rollback
    coordinator.S.install_release(
        project, new, backup, coordinator.S.pin(project / coordinator.RELEASE)
    )
    altered = {**new, "api_port": 18180}
    coordinator.S.atomic_source(
        project / coordinator.RELEASE, (json.dumps(altered, indent=2) + "\n").encode()
    )
    coordinator.S.write_new(project / coordinator.STATE, state)
    with pytest.raises(RuntimeError, match="EXACT_INSTALLED_RELEASE_ROLLBACK_REQUIRED"):
        coordinator.main()
    assert events == []
