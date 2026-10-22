"""One direct public-source/native upgrade and durable existing-installation launcher."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener
from uuid import uuid4

import main201_source as S

HERE = Path(__file__).resolve().parent
STATE = "artifacts/runtime/upgrade-processes.json"
RELEASE = "UPGRADE_MANIFEST.json"
HIDDEN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(path, value):
    S.atomic_source(path, (json.dumps(value, indent=2) + "\n").encode())


def resume_suspended(process):
    """Resume only threads belonging to the new, still-held process handle."""
    import ctypes
    from ctypes import wintypes as W
    class Thread(ctypes.Structure):
        _fields_ = [("dwSize", W.DWORD), ("cntUsage", W.DWORD), ("th32ThreadID", W.DWORD),
                    ("th32OwnerProcessID", W.DWORD), ("tpBasePri", W.LONG), ("tpDeltaPri", W.LONG), ("dwFlags", W.DWORD)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = W.HANDLE
    kernel.Thread32First.argtypes = [W.HANDLE, ctypes.POINTER(Thread)]
    kernel.Thread32Next.argtypes = [W.HANDLE, ctypes.POINTER(Thread)]
    kernel.Thread32First.restype = kernel.Thread32Next.restype = W.BOOL
    kernel.OpenThread.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    kernel.OpenThread.restype = W.HANDLE
    kernel.ResumeThread.argtypes = [W.HANDLE]
    kernel.ResumeThread.restype = W.DWORD
    kernel.CloseHandle.argtypes = [W.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(4, 0)
    S.require(snapshot and snapshot != ctypes.c_void_p(-1).value, "SUSPENDED_CHILD_THREAD_SNAPSHOT_FAILED")
    resumed = False
    try:
        thread = Thread()
        thread.dwSize = ctypes.sizeof(thread)
        more = kernel.Thread32First(snapshot, ctypes.byref(thread))
        while more:
            if thread.th32OwnerProcessID == process.pid:
                handle = kernel.OpenThread(2, False, thread.th32ThreadID)
                S.require(handle, "SUSPENDED_CHILD_THREAD_HANDLE_FAILED")
                try:
                    S.require(kernel.ResumeThread(handle) == 1, "SUSPENDED_CHILD_RESUME_FAILED")
                    resumed = True
                finally:
                    kernel.CloseHandle(handle)
            more = kernel.Thread32Next(snapshot, ctypes.byref(thread))
    finally:
        kernel.CloseHandle(snapshot)
    S.require(resumed, "SUSPENDED_CHILD_THREAD_NOT_FOUND")


def checked(path, sha):
    S.require(S.pin(S.regular(path))["sha256"] == sha, "EXACT_PINNED_AUTHORITY_REQUIRED")
    return json.loads(Path(path).read_text())


def bounded_job(process):
    """Associate a still-suspended child before any command can spawn descendants."""
    import ctypes
    from ctypes import wintypes as W
    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", W.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", W.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", W.DWORD), ("SchedulingClass", W.DWORD)]
    class Counters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]
    class Extended(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", Counters),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, W.LPCWSTR]
    kernel.CreateJobObjectW.restype = W.HANDLE
    kernel.SetInformationJobObject.argtypes = [W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD]
    kernel.SetInformationJobObject.restype = W.BOOL
    kernel.AssignProcessToJobObject.argtypes = [W.HANDLE, W.HANDLE]
    kernel.AssignProcessToJobObject.restype = W.BOOL
    kernel.CloseHandle.argtypes = [W.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    S.require(job, "OWNED_BOUNDED_JOB_CREATION_FAILED")
    try:
        limits = Extended()
        limits.BasicLimitInformation.LimitFlags = 0x2000
        S.require(kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)), "OWNED_JOB_LIMIT_FAILED")
        S.require(kernel.AssignProcessToJobObject(job, int(process._handle)), "SUSPENDED_CHILD_JOB_ASSIGNMENT_FAILED")
        resume_suspended(process)
        return kernel, job
    except BaseException:
        kernel.CloseHandle(job)
        process.terminate()
        process.wait(timeout=10)
        raise


def native_start_diagnostic(stdout, returncode, *, timed_out=False):
    """Rebuild only the pinned native-import protocol; never relay child prose."""
    report = {"schema": "windows_native_start_diagnostic_v1", "status": "NATIVE_DEPENDENCY_PREFLIGHT_FAILED",
              "code": "NATIVE_IMPORT_TIMEOUT" if timed_out else "NATIVE_IMPORT_PROCESS_FAILED", "checks": []}
    if timed_out:
        return report
    codes = {"NATIVE_MODULE_MISSING", "NATIVE_DEPENDENCY_MISSING", "NATIVE_LIBRARY_LOAD_FAILED",
             "NATIVE_IMPORT_FAILED", "NATIVE_IMPORT_TIMEOUT", "NATIVE_IMPORT_PROCESS_FAILED"}
    try:
        if len(stdout) > 65536:
            raise ValueError("Native diagnostic exceeds its limit")
        value = json.loads(stdout)
        if (value["schema"] != "windows_native_dependency_preflight_v1"
                or value["status"] not in {"PASS_NATIVE_IMPORTS", "NATIVE_DEPENDENCY_PREFLIGHT_FAILED"}
                or type(value["python_bits"]) is not int or value["python_bits"] not in {32, 64}
                or len(value["checks"]) != 2):
            raise ValueError("Invalid aggregate native result")
        checks = []
        for module, row in zip(("torch", "pymupdf"), value["checks"]):
            if (row["schema"] != "windows_native_import_v1" or row["module"] != module
                    or row["status"] not in {"passed", "failed"}):
                raise ValueError("Invalid native module result")
            clean = {"module": module, "status": row["status"]}
            if row["status"] == "passed":
                if row.get("exit_code") != 0 or row.get("python_bits") != value["python_bits"]:
                    raise ValueError("Inconsistent native success")
            else:
                if row.get("code") not in codes:
                    raise ValueError("Unknown native diagnostic")
                clean["code"] = row["code"]
                if type(row.get("winerror")) is int and 0 <= row["winerror"] <= 65535:
                    clean["winerror"] = row["winerror"]
                for field, pattern in (("native_file", r"[A-Za-z0-9_.-]{1,100}\.(?:dll|pyd)"),
                                       ("dependency", r"[A-Za-z_][A-Za-z0-9_.-]{0,79}")):
                    item = row.get(field)
                    if isinstance(item, str) and re.fullmatch(pattern, item, re.I):
                        clean[field] = item
            checks.append(clean)
        passed = all(row["status"] == "passed" for row in checks)
        if passed != (value["status"] == "PASS_NATIVE_IMPORTS") or passed != (returncode == 0):
            raise ValueError("Inconsistent native process status")
        report.update(status=value["status"], code="PASS_NATIVE_IMPORTS" if passed else "NATIVE_DEPENDENCY_PREFLIGHT_FAILED",
                      python_bits=value["python_bits"], checks=checks)
    except (ValueError, TypeError, KeyError, AttributeError):
        pass
    return report


def preserve_native_diagnostic(path, report, argv):
    """Persist sanitized diagnosis before any database inspection or launch."""
    path = S.regular(path)
    report["standalone_command"] = "& " + " ".join("'" + str(x).replace("'", "''") + "'" for x in argv)
    report["next_step"] = "Run the standalone command; resolve its reported dependency before starting again."
    if any(row.get("code") in {"NATIVE_MODULE_MISSING", "NATIVE_DEPENDENCY_MISSING"} for row in report["checks"]):
        report["next_step"] += " Check the locked Python dependencies in this selected environment."
    details = []
    for row in report["checks"]:
        if row["status"] != "failed":
            continue
        detail = row["module"] + ": " + row["code"]
        if "winerror" in row:
            detail += "; WinError " + str(row["winerror"])
        if "native_file" in row:
            detail += "; " + row["native_file"]
        if "dependency" in row:
            detail += "; component " + row["dependency"]
        details.append(detail)
    if any(row.get("code") == "NATIVE_LIBRARY_LOAD_FAILED" for row in report["checks"]):
        report["official_runtime_help"] = "https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist"
        report["next_step"] += " Check Python/wheel architecture and the official VC++ runtime guidance; other DLLs can cause this failure. Do not copy loose DLLs."
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    if report["status"] != "PASS_NATIVE_IMPORTS":
        reason = "; ".join(details) or ("Native import process exceeded its time limit" if report["code"] == "NATIVE_IMPORT_TIMEOUT"
                                        else "Native import process did not produce a valid completion report")
        raise RuntimeError(report["code"] + ": " + reason + ". Sanitized diagnosis: " + str(path)
                           + ". " + report["next_step"] + " Standalone: " + report["standalone_command"])


def run(argv, cwd, *, timeout=30, environment=None, logs=None, native_diagnostic=None):
    try:
        process = subprocess.Popen([str(x) for x in argv], cwd=cwd, env=environment,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=HIDDEN | (4 if os.name == "nt" else 0))
    except OSError:
        if native_diagnostic is not None:
            preserve_native_diagnostic(native_diagnostic, native_start_diagnostic(b"", 1), argv)
        raise
    kernel = job = None
    try:
        if os.name == "nt":
            try:
                kernel, job = bounded_job(process)
            except BaseException:
                if process.poll() is None:
                    process.kill()  # The exact Popen handle still identifies this suspended child.
                process.communicate(timeout=10)
                raise
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if job is not None:
                terminate_bounded_job(kernel, job)
            else:
                process.kill()
            process.communicate(timeout=10)
            if native_diagnostic is not None:
                preserve_native_diagnostic(native_diagnostic, native_start_diagnostic(b"", 1, timed_out=True), argv)
            raise RuntimeError("BOUNDED_NATIVE_TIMEOUT_OWNED_JOB_CLOSED")
    finally:
        if job is not None:
            try:
                terminate_bounded_job(kernel, job)
            finally:
                kernel.CloseHandle(job)
    if native_diagnostic is not None:
        preserve_native_diagnostic(native_diagnostic, native_start_diagnostic(stdout, process.returncode), argv)
    if logs:
        Path(str(logs) + ".stdout").write_bytes(stdout)
        Path(str(logs) + ".stderr").write_bytes(stderr)
    S.require(process.returncode == 0, "BOUNDED_NATIVE_COMMAND_FAILED_" + Path(str(argv[0])).name)
    return stdout.decode("utf-8", errors="strict")


def terminate_bounded_job(kernel, job):
    """Wait for all of this job's descendants, not merely its root pipe closure."""
    import ctypes
    from ctypes import wintypes as W
    class Accounting(ctypes.Structure):
        _fields_ = [(name, ctypes.c_int64) for name in ("TotalUserTime", "TotalKernelTime", "ThisPeriodTotalUserTime", "ThisPeriodTotalKernelTime")] + [
            (name, W.DWORD) for name in ("TotalPageFaultCount", "TotalProcesses", "ActiveProcesses", "TotalTerminatedProcesses")]
    kernel.TerminateJobObject.argtypes = [W.HANDLE, W.UINT]
    kernel.TerminateJobObject.restype = W.BOOL
    kernel.QueryInformationJobObject.argtypes = [W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD, ctypes.c_void_p]
    kernel.QueryInformationJobObject.restype = W.BOOL
    kernel.IsProcessInJob.argtypes = [W.HANDLE, W.HANDLE, ctypes.POINTER(W.BOOL)]
    kernel.IsProcessInJob.restype = W.BOOL
    kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
    kernel.WaitForSingleObject.restype = W.DWORD
    buffer = ctypes.create_string_buffer(8 + 4096 * ctypes.sizeof(ctypes.c_size_t))
    S.require(kernel.QueryInformationJobObject(job, 3, buffer, len(buffer), None), "BOUNDED_OWNED_JOB_PID_LIST_REQUIRED")
    count = W.DWORD.from_buffer(buffer, 4).value
    S.require(count <= 4096, "OWNED_COMMAND_PROCESS_LIMIT_EXCEEDED")
    ids = (ctypes.c_size_t * count).from_buffer(buffer, 8)
    handles = []
    try:
        for pid in ids:
            try:
                _, handle, _ = process_handle(pid)
            except RuntimeError:
                if ctypes.get_last_error() == 87:  # This job member already exited.
                    continue
                raise
            handles.append(handle)
            member = W.BOOL()
            S.require(kernel.IsProcessInJob(handle, job, ctypes.byref(member)) and member.value,
                      "OWNED_JOB_MEMBER_IDENTITY_CHANGED")
        S.require(kernel.TerminateJobObject(job, 1), "OWNED_BOUNDED_JOB_TERMINATION_FAILED")
        deadline = time.monotonic() + 10
        for handle in handles:
            remaining = max(0, int((deadline - time.monotonic()) * 1000))
            S.require(kernel.WaitForSingleObject(handle, remaining) == 0, "OWNED_JOB_MEMBER_EXIT_TIMEOUT")
        while True:
            info = Accounting()
            S.require(kernel.QueryInformationJobObject(job, 1, ctypes.byref(info), ctypes.sizeof(info), None), "OWNED_JOB_ACCOUNTING_UNAVAILABLE")
            if info.ActiveProcesses == 0:
                return
            S.require(time.monotonic() < deadline, "OWNED_JOB_DESCENDANT_EXIT_TIMEOUT")
            time.sleep(0.02)
    finally:
        for handle in handles:
            kernel.CloseHandle(handle)


def process_handle(pid, terminate=False):
    # Same-handle creation/termination primitive retained from the reviewed
    # main_adoption210_recovery01 Windows implementation.
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000 | 0x100000 | (1 if terminate else 0), False, pid)
    S.require(handle, "OWNED_PROCESS_HANDLE_UNAVAILABLE")
    times = [wintypes.FILETIME() for _ in range(4)]
    if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
        kernel.CloseHandle(handle)
        raise RuntimeError("OWNED_PROCESS_CREATION_UNAVAILABLE")
    return kernel, handle, (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime


def process_image(pid):
    import ctypes
    from ctypes import wintypes as W
    kernel, handle, _ = process_handle(pid)
    try:
        kernel.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, ctypes.POINTER(W.DWORD)]
        kernel.QueryFullProcessImageNameW.restype = W.BOOL
        name, size = ctypes.create_unicode_buffer(32768), W.DWORD(32768)
        S.require(kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)), "OWNED_PROCESS_IMAGE_UNAVAILABLE")
        return name.value
    finally:
        kernel.CloseHandle(handle)


def processes(powershell, project=None):
    script = "$ErrorActionPreference='Stop';Get-CimInstance Win32_Process|ForEach-Object{[pscustomobject]@{pid=$_.ProcessId;parent_pid=$_.ParentProcessId;executable=$_.ExecutablePath;command=$_.CommandLine}}|ConvertTo-Json -Compress"
    raw = json.loads(run([powershell, "-NoProfile", "-NonInteractive", "-Command", script], HERE, timeout=20))
    rows = raw if isinstance(raw, list) else [raw]
    for row in rows:
        command = row.pop("command") or ""
        row["command_sha256"] = hashlib.sha256(command.encode()).hexdigest()
        if not row["executable"]:
            try:
                row["executable"] = process_image(row["pid"])
            except RuntimeError:
                pass  # Unavailable system identities remain unavailable and cannot become owned.
        if project is not None:
            row["targets_project"] = str(project).casefold() in command.casefold()
    return rows


def same(left, right):
    return all(left[key] == right.get(key) for key in ("pid", "parent_pid", "executable", "command_sha256"))


def family_members(root_pid, powershell):
    rows = processes(powershell)
    ids = {root_pid}
    while True:
        found = {row["pid"] for row in rows if row["parent_pid"] in ids}
        if found <= ids:
            break
        ids |= found
    members = []
    for row in rows:
        if row["pid"] in ids:
            kernel, handle, created = process_handle(row["pid"])
            kernel.CloseHandle(handle)
            members.append({**row, "created_filetime": created})
    S.require(any(row["pid"] == root_pid for row in members), "NEW_NATIVE_ROOT_EXITED")
    return members


def validate_family(family, powershell, allow_missing=False):
    rows = {row["pid"]: row for row in processes(powershell)}
    found = []
    for previous in family["members"]:
        actual = rows.get(previous["pid"])
        if actual is None:
            S.require(allow_missing, "OWNED_PROCESS_MISSING_BEFORE_STOP")
            continue
        S.require(same(previous, actual), "OWNED_PROCESS_IDENTITY_CHANGED")
        kernel, handle, created = process_handle(actual["pid"])
        kernel.CloseHandle(handle)
        S.require(created == previous["created_filetime"], "PID_REUSE_REFUSED")
        found.append(previous)
    return found


def refresh_family(family, powershell):
    """Expand descendants only after proving the saved root still has its identity."""
    found = validate_family(family, powershell, True)
    root = next((row for row in found if row["pid"] == family["root_pid"]), None)
    if root:
        actual = family_members(family["root_pid"], powershell)
        saved = {row["pid"]: row for row in family["members"]}
        for row in actual:
            if row["pid"] in saved:
                S.require(same(row, saved[row["pid"]]) and row["created_filetime"] == saved[row["pid"]]["created_filetime"],
                          "OWNED_DESCENDANT_IDENTITY_CHANGED")
        family["members"] = list({row["pid"]: row for row in [*family["members"], *actual]}.values())
    return family


def stop_family(family, powershell, journal, save):
    import ctypes
    from ctypes import wintypes
    refresh_family(family, powershell)
    save()
    for previous in sorted(family["members"], key=lambda row: row["created_filetime"], reverse=True):
        if not any(row["pid"] == previous["pid"] for row in validate_family(family, powershell, True)):
            continue
        kernel, handle, created = process_handle(previous["pid"], True)
        try:
            S.require(created == previous["created_filetime"], "PID_REUSE_REFUSED")
            intent = {"role": family["role"], "pid": previous["pid"], "created_filetime": created, "status": "INTENT", "utc": now()}
            journal.setdefault("stops", []).append(intent)
            save()
            kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
            kernel.TerminateProcess.restype = wintypes.BOOL
            S.require(kernel.TerminateProcess(handle, 0), "OWNED_TERMINATION_FAILED")
            kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.WaitForSingleObject.restype = wintypes.DWORD
            S.require(kernel.WaitForSingleObject(handle, 10000) == 0, "OWNED_EXIT_TIMEOUT")
            intent["status"] = "EXIT_CONFIRMED"
            save()
        finally:
            kernel.CloseHandle(handle)
    S.require(not validate_family(family, powershell, True), "OWNED_FAMILY_NOT_EXITED")
    family["status"] = "EXIT_CONFIRMED"
    save()


def metadata(args, mode="inspect", head=None, allowed=()):
    argv = [args.python, "-B", HERE / "main201_metadata.py", mode, "--project", args.project,
            "--database-host", args.database_host, "--database-port", args.database_port,
            "--database-name", args.database_name]
    if head:
        argv += ["--target-head", head]
    for value in allowed:
        argv += ["--allowed-head", value]
    return json.loads(run(argv, args.project, timeout=90 if mode == "migrate" else 20))


def idle(value, no_locks=False):
    S.require(value["pending_jobs"] == value["pending_requests"] == 0, "PENDING_WORK_BLOCKS_UPGRADE")
    if no_locks:
        S.require(not value["worker_locks"], "UNOWNED_OR_UNSTOPPED_WORKER_LOCKS")


def preserved(args, before):
    after = metadata(args)
    for key in ("active_selection_sha256", "active_corpus_sha256", "epoch_sha256", "database_identity", "storage_root", "key_file"):
        S.require(after[key] == before[key], "PRESERVED_EXISTING_STATE_CHANGED_" + key)
    return after


def child_environment(project, api_port):
    # Private values stay in this process and child environment; never stdout,
    # argv, receipts, delivered files or a copied environment file.
    from dotenv import dotenv_values
    sys.path[:0] = [str(project / "backend"), str(project)]
    from app.core.config import Settings
    environment = dict(os.environ)
    environment.pop("MODEL_CONFIG_ENCRYPTION_KEY", None)
    for name, field in Settings.model_fields.items():
        for alias in [name, name.upper(), *getattr(field.validation_alias, "choices", [field.validation_alias])]:
            if isinstance(alias, str):
                environment.pop(alias, None)
    environment.update({key: value for key, value in dotenv_values(project / ".env", encoding="utf-8-sig").items() if value is not None})
    environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=os.pathsep.join([str(project / "backend"), str(project)]),
                       API_PROXY_URL=f"http://127.0.0.1:{api_port}")
    return environment


def ports_free(args):
    script = f"$ErrorActionPreference='Stop';@(Get-NetTCPConnection -State Listen|Where-Object{{$_.LocalPort -in @({args.api_port},{args.frontend_port})}}|Select-Object LocalPort,OwningProcess)|ConvertTo-Json -Compress"
    output = run([args.powershell, "-NoProfile", "-NonInteractive", "-Command", script], HERE).strip()
    S.require(not (json.loads(output) if output else []), "TARGET_SERVICE_PORT_OCCUPIED_NO_PORT_KILL")


def target_processes_absent(args):
    rows = processes(args.powershell, args.project)
    by_pid = {row["pid"]: row for row in rows}
    ancestors, current = {os.getpid()}, os.getpid()
    while current in by_pid and by_pid[current]["parent_pid"] not in ancestors:
        current = by_pid[current]["parent_pid"]
        ancestors.add(current)
    prefix = str(args.project / ".venv").casefold() + os.sep
    S.require(not any(row["pid"] not in ancestors and ((row.get("executable") or "").casefold().startswith(prefix)
                      or row["targets_project"] and Path(row.get("executable") or "").stem.casefold() in {"python", "pythonw", "node", "uvicorn"})
                      for row in rows), "UNREVIEWED_TARGET_INTERPRETER_PROCESS_NO_KILL")


def normalize_managed_state(state, project, authority_sha256):
    """Retain recoverable partial starts without requiring application readiness."""
    S.require(state["schema"] == "direct_native_managed_processes_v1" and state["project"] == str(project),
              "OWNED_MANAGED_PROCESS_STATE_REQUIRED")
    S.require(state["source_authority_sha256"] == state["source_authority"]["sha256"] == authority_sha256,
              "MANAGED_STATE_RELEASE_AUTHORITY_MISMATCH")
    families = {}
    for family in [*state.get("families", []), *state.get("new_families", [])]:
        key = family["root_pid"]
        S.require(family["members"] and any(row["pid"] == key for row in family["members"]), "RECORDED_FAMILY_ROOT_IDENTITY_REQUIRED")
        if key in families:
            S.require(families[key]["role"] == family["role"], "CONFLICTING_RECORDED_START_ROLE")
            for row in family["members"]:
                old = next((value for value in families[key]["members"] if value["pid"] == row["pid"]), None)
                S.require(old is None or old == row, "CONFLICTING_RECORDED_START_IDENTITY")
                if old is None:
                    families[key]["members"].append(row)
        else:
            families[key] = {**family, "members": list(family["members"])}
    for intent in state.get("starts", []):
        identity = intent.get("root_identity")
        if identity and intent["status"] != "SUSPENDED_LAUNCH_EXIT_CONFIRMED" and identity["pid"] not in families:
            families[identity["pid"]] = {"role": intent["role"], "root_pid": identity["pid"], "members": [identity]}
    state["families"] = list(families.values())
    return state


def require_previous_stopped(previous, powershell):
    retained = [family for family in previous.get("families", []) if family["role"] == "frontend"] if previous.get("status") == "PAUSED_FRONTEND_RETAINED" else []
    for family in previous.get("families", []):
        if family not in retained:
            S.require(not validate_family(family, powershell, True), "PREVIOUS_OWNED_START_EXISTS_RUN_STOP_BEFORE_START")
    return retained


def launch_commands(args, release, journal, save, log_root, commands, *, retain=()):
    environment = child_environment(args.project, args.api_port)
    journal["new_families"] = list(retain)
    def flush():
        save()
        dump(args.project / STATE, {"schema": "direct_native_managed_processes_v1", "project": str(args.project),
                                   "source_authority": release["source_authority"], "families": journal["new_families"],
                                   "source_authority_sha256": release["source_authority"]["sha256"],
                                   "starts": journal.get("starts", []), "control_sha256": journal.get("control_sha256"),
                                   "native_journal_path": journal.get("native_journal_path"),
                                   "status": "STARTING", "api_port": args.api_port, "frontend_port": args.frontend_port})
    for role, argv in commands.items():
        intent = {"role": role, "status": "START_INTENT", "utc": now(),
                  "argv_sha256": hashlib.sha256(json.dumps([str(x) for x in argv]).encode()).hexdigest()}
        journal.setdefault("starts", []).append(intent)
        flush()
        stdout = (log_root / f"{role}.stdout").open("xb")
        stderr = (log_root / f"{role}.stderr").open("xb")
        process = None
        resumed = False
        try:
            process = subprocess.Popen([str(x) for x in argv], cwd=args.project if role != "frontend" else args.project / "frontend",
                                       env=environment, stdout=stdout, stderr=stderr, creationflags=HIDDEN | 4,
                                       close_fds=True)
            kernel, handle, created = process_handle(process.pid)
            kernel.CloseHandle(handle)
            intent.update(pid=process.pid, created_filetime=created, status="START_SUSPENDED")
            root = {"pid": process.pid, "parent_pid": os.getpid(), "executable": process_image(process.pid),
                    "command_sha256": hashlib.sha256(subprocess.list2cmdline([str(x) for x in argv]).encode()).hexdigest(),
                    "created_filetime": created}
            intent["root_identity"] = root
            family = {"role": role, "root_pid": process.pid, "members": [root]}
            journal["new_families"].append(family)
            flush()
            observed = next(row for row in processes(args.powershell) if row["pid"] == process.pid)
            S.require(same(root, observed), "SUSPENDED_ROOT_COMMAND_IDENTITY_MISMATCH")
            resume_suspended(process)
            resumed = True
            intent["status"] = "RESUMED_OWNED_ROOT"
            flush()
            time.sleep(0.25)
            refresh_family(family, args.powershell)
            flush()
        except BaseException:
            if process is not None and not resumed:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
                intent["status"] = "SUSPENDED_LAUNCH_EXIT_CONFIRMED"
            else:
                intent["status"] = "OWNED_LAUNCH_FAILED_REQUIRES_STOP"
            flush()
            raise
        finally:
            stdout.close()
            stderr.close()


def start_roles(args, release, journal, save, log_root, *, retain=()):
    if not retain:
        ports_free(args)
    commands = {
        "api": [args.python, "-B", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", args.api_port, "--timeout-graceful-shutdown", "5"],
        "interactive": [args.python, "-B", "-m", "app.worker", "--queue", "interactive"],
        "background": [args.python, "-B", "-m", "app.worker", "--queue", "background"],
        "frontend": [args.node, args.project / "frontend/node_modules/vite/bin/vite.js", args.project / "frontend", "--configLoader", "runner", "--host", "127.0.0.1", "--port", args.frontend_port, "--strictPort"],
    }
    for family in retain:
        validate_family(family, args.powershell)
        commands.pop(family["role"], None)
    launch_commands(args, release, journal, save, log_root, commands, retain=retain)


def health(args, journal):
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + args.readiness_seconds
    while time.monotonic() < deadline:
        try:
            for family in journal["new_families"]:
                validate_family(family, args.powershell)
            with opener.open(f"http://127.0.0.1:{args.api_port}/ready", timeout=2) as response:
                ready = json.load(response)
                S.require(response.status == 200 and ready["status"] == "ready", "API_NOT_READY")
            with opener.open(f"http://127.0.0.1:{args.frontend_port}/", timeout=2) as response:
                S.require(response.status == 200, "FRONTEND_NOT_READY")
            current = metadata(args)
            idle(current)
            lanes = {row["lock_id"]: row["pg_backend_pid"] for row in current["worker_locks"] if row["mode"] == "ExclusiveLock"}
            S.require(set(lanes) == {5703002, 5703003} and lanes[5703002] != lanes[5703003], "DISTINCT_SPLIT_WORKER_LOCKS_REQUIRED")
            path = Path(current["storage_root"]) / "runtime/worker_retrieval_warmup_v1" / current["database_fingerprint"] / current["namespace_sha256"] / "interactive.json"
            warmup = json.loads(S.regular(path).read_text())
            interactive = next(f for f in journal["new_families"] if f["role"] == "interactive")
            S.require(warmup["state"] == "ready" and warmup["ready"] is True
                      and warmup["pid"] in {row["pid"] for row in interactive["members"]}
                      and warmup["lock_backend_pid"] == lanes[5703002]
                      and datetime.now(timezone.utc) < datetime.fromisoformat(warmup["lease_expires_at"].replace("Z", "+00:00"))
                      and warmup["source_fingerprint"]["epoch_sha256"] == current["epoch_sha256"], "CURRENT_NATIVE_WARMUP_LEASE_REQUIRED")
            return {"api": ready, "frontend_http": 200, "database": current,
                    "warmup": {key: warmup[key] for key in ("pid", "lock_backend_pid", "runtime_device", "checked_at", "lease_expires_at")}}
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("BOUNDED_NATIVE_READINESS_FAILED_PRESERVE_LOGS")


def runtime_manifest(project, *, verify_source=True):
    release = json.loads(S.regular(project / RELEASE).read_text())
    S.require(release["schema"] == "direct_native_upgrade_release_v1", "SUCCESSOR_RUNTIME_MANIFEST_REQUIRED")
    rows = release["source_rows"]
    S.require(isinstance(rows, list) and 0 < len(rows) <= 20000 and release["source_row_count"] == len(rows),
              "EXACT_NONEMPTY_RELEASE_SOURCE_COUNT_REQUIRED")
    seen = set()
    for row in rows:
        S.public_path(row["path"])
        S.require(row["path"].casefold() not in seen and type(row["bytes"]) is int and row["bytes"] >= 0
                  and isinstance(row["sha256"], str) and len(row["sha256"]) == 64
                  and all(c in "0123456789abcdef" for c in row["sha256"]), "UNIQUE_VALID_RELEASE_SOURCE_ROWS_REQUIRED")
        seen.add(row["path"].casefold())
        if verify_source:
            actual = S.pin(S.regular(project / row["path"]))
            S.require(actual["sha256"] == row["sha256"] and actual["bytes"] == row["bytes"], "SUCCESSOR_SOURCE_DRIFT")
    S.require(S.inventory_hash(rows) == release["source_inventory_sha256"], "EXACT_RELEASE_SOURCE_INVENTORY_REQUIRED")
    S.require(release["source_authority"]["sha256"] == release["source_authority_sha256"]
              and len(release["source_authority_sha256"]) == 64, "EXACT_RELEASE_SOURCE_AUTHORITY_REQUIRED")
    return release


def rollback_context(args, release):
    """Permit only the pinned upgrade and exact installed predecessor during rollback."""
    S.require(args.backup is not None, "EXACT_UPGRADE_BACKUP_REQUIRED")
    native_journal = json.loads(S.regular(args.backup / "native-journal.json").read_text())
    source_journal = json.loads(S.regular(args.backup / "source/journal.json").read_text())
    plan = checked(native_journal["plan"]["path"], native_journal["plan"]["sha256"])
    S.require(S.regular(native_journal["project"]) == args.project
              and S.regular(source_journal["target"]) == args.project
              and S.regular(plan["target"]) == args.project
              and source_journal["payload_plan"] == native_journal["plan"],
              "ROLLBACK_BACKUP_PLAN_AND_AUTHORITY_MUST_BELONG_TO_EXACT_TARGET")
    authorities = {plan["source_authority"]["sha256"]}
    baseline = plan.get("baseline_release")
    current = S.pin(S.regular(args.project / RELEASE)) if baseline else None
    if baseline:
        S.require(plan["baseline_kind"] == "installed" and S.regular(baseline["path"]) == args.project / RELEASE,
                  "EXACT_INSTALLED_BASELINE_RELEASE_REQUIRED")
        if current == baseline:
            predecessor = release
        else:
            preimage = S.regular(args.backup / "release-preimage.json")
            preserved_pin = S.pin(preimage)
            S.require(all(preserved_pin[key] == baseline[key] for key in ("bytes", "sha256")),
                      "EXACT_RELEASE_ROLLBACK_PREIMAGE_REQUIRED")
            predecessor = json.loads(preimage.read_text())
        S.release_rows(predecessor)
        authorities.add(predecessor["source_authority_sha256"])
        if S.regular(args.backup / "release-update.json").exists():
            S.restore_previous_release(args.project, args.backup, verify_only=True)
        else:
            S.require(current == baseline, "EXACT_PRE_METADATA_RELEASE_REQUIRED")
    S.require(release["source_authority"]["sha256"] == plan["source_authority"]["sha256"]
              or baseline is not None and current == baseline,
              "ROLLBACK_BACKUP_PLAN_AND_AUTHORITY_MUST_BELONG_TO_EXACT_TARGET")
    return plan, authorities


def restore_stopped_authority(args, state, plan, state_path):
    """Keep actual exited identities while restoring a verified predecessor's launcher lineage."""
    baseline = plan.get("baseline_release")
    if not baseline:
        return
    S.require(S.pin(S.regular(args.project / RELEASE)) == baseline, "EXACT_PREVIOUS_RELEASE_RESTORE_REQUIRED")
    restored = runtime_manifest(args.project)
    S.require(state["status"] == "STOPPED", "STOPPED_STATE_REQUIRED_FOR_RELEASE_REBIND")
    for family in state["families"]:
        S.require(family.get("status") == "EXIT_CONFIRMED" and not validate_family(family, args.powershell, True),
                  "EXITED_FAMILIES_REQUIRED_FOR_RELEASE_REBIND")
    idle(metadata(args), True)
    old_authority = state["source_authority"]
    state.update(source_authority=restored["source_authority"], source_authority_sha256=restored["source_authority_sha256"])
    state["release_rollback"] = {"previous_state_authority": old_authority, "restored_release": baseline,
                                 "status": "STOPPED_IDENTITIES_PRESERVED_OLD_SOURCE_VERIFIED"}
    dump(state_path, state)


def prepare_delivery(args):
    """Resolve the released package in one invocation; never form an overlay chain."""
    index = checked(args.delivery_index, args.delivery_index_sha256)
    S.require(index["schema"] == "direct_native_upgrade_delivery_index_v1"
              and index["authority"] == "Root" and index["status"] == "ROOT_REVIEWED_PORTABLE_UPGRADE"
              and index["dynamic_target_planning_allowed"] is True, "REVIEWED_PORTABLE_DELIVERY_INDEX_REQUIRED")
    def local(row):
        name = Path(row["path"])
        S.require(not name.is_absolute() and ".." not in name.parts, "DELIVERY_INDEX_LOCAL_PUBLIC_PATH_REQUIRED")
        path = S.regular(HERE / name)
        S.require(path.is_relative_to(HERE) and S.pin(path)["sha256"] == row["sha256"], "DELIVERY_INDEX_FILE_DRIFT")
        return path
    authority = local(index["source_authority"])
    manifest = local(index["manifest"])
    target_go = local(index["target_go"])
    code_pins = [{**S.pin(local(row))} for row in index["code_pins"]]
    planner = next(row for row in code_pins if Path(row["path"]).name == "plan_main201.py")
    S.require(S.regular(planner["path"]) == HERE / "plan_main201.py", "EXECUTED_PORTABLE_PLANNER_PIN_REQUIRED")
    import plan_main201
    baseline = local(index["current563_baseline_authority"])
    installed_baseline = local(index["installed_baseline_release"]) if index.get("installed_baseline_release") else None
    original = args.project / "PACKAGE_MANIFEST.json"
    workspace = S.regular(args.workspace_root or args.project.parent)
    protected = [S.regular(value) for value in (args.protected_root or [HERE])]
    options = argparse.Namespace(project=args.project, bundle=HERE, workspace_root=workspace,
                                 authority=authority, authority_sha256=index["source_authority"]["sha256"],
                                 manifest=manifest, manifest_sha256=index["manifest"]["sha256"],
                                 final_target_go=target_go, final_target_go_sha256=index["target_go"]["sha256"],
                                 baseline_kind="current563", baseline_authority=baseline,
                                 baseline_authority_sha256=index["current563_baseline_authority"]["sha256"],
                                 installed_baseline_release=installed_baseline,
                                 installed_baseline_release_sha256=(index["installed_baseline_release"]["sha256"]
                                                                   if installed_baseline else None),
                                 protected_root=protected, reference_migration_head=None)
    plans = []
    for kind in ("Main201", "current563", "installed"):
        if kind == "Main201" and not (original.is_file() and S.pin(original)["sha256"] == plan_main201.BASE_MANIFEST_SHA):
            continue
        if kind == "installed" and not (installed_baseline and (args.project / RELEASE).is_file()):
            continue
        options.baseline_kind = kind
        try:
            plans.append(plan_main201.build(options))
        except RuntimeError:
            continue
    S.require(len(plans) == 1, "EXACTLY_ONE_COMPLETE_REVIEWED_BASELINE_MUST_MATCH")
    plan = plans[0]
    prepared = S.regular(args.project / "artifacts/runtime" / ("upgrade-preparation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")))
    prepared.mkdir(parents=True)
    args.plan = prepared / "PLAN.json"
    S.write_new(args.plan, plan)
    args.plan_sha256 = S.pin(args.plan)["sha256"]
    args.native_go = prepared / "NATIVE-GO.json"
    S.write_new(args.native_go, {"schema": "direct_native_upgrade_go_v1", "authority": "Root",
                               "status": "ROOT_APPROVED_NATIVE_UPGRADE", "plan_sha256": args.plan_sha256,
                               "delivery_index": S.pin(args.delivery_index), "project": str(args.project),
                               "code_pins": code_pins,
                               "host_proof_sha256": args.host_proof_sha256 if args.host_proof else None})
    args.native_go_sha256 = S.pin(args.native_go)["sha256"]
    args.backup = args.backup or workspace / (args.project.name + "-upgrade-backup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f"))


def install(args):
    plan = checked(args.plan, args.plan_sha256)
    go = checked(args.native_go, args.native_go_sha256)
    S.require(plan["status"] == "FINAL_TARGET_BOUND_NATIVE_EXECUTION_NOT_RUN"
              and go["schema"] == "direct_native_upgrade_go_v1" and go["authority"] == "Root"
              and go["status"] == "ROOT_APPROVED_NATIVE_UPGRADE"
              and go["plan_sha256"] == args.plan_sha256, "ACTUAL_REVIEWED_NATIVE_UPGRADE_GO_REQUIRED")
    for row in go["code_pins"]:
        S.require(S.pin(S.regular(row["path"]))["sha256"] == row["sha256"], "REVIEWED_COORDINATOR_CODE_CHANGED")
    S.require({Path(row["path"]).name for row in go["code_pins"]} >= {"upgrade_main201.py", "main201_source.py", "main201_metadata.py"}, "ALL_NATIVE_COORDINATOR_CODE_PINS_REQUIRED")
    for name in ("upgrade_main201.py", "main201_source.py", "main201_metadata.py"):
        exact = [row for row in go["code_pins"] if S.regular(row["path"]) == HERE / name]
        S.require(len(exact) == 1 and S.pin(HERE / name)["sha256"] == exact[0]["sha256"], "ACTUAL_EXECUTED_COORDINATOR_PATH_AND_PIN_REQUIRED")
    S.require(go.get("host_proof_sha256") == (args.host_proof_sha256 if args.host_proof else None), "ROOT_GO_MUST_BIND_EXACT_HOST_PROOF_OR_EXPLICIT_NONE")
    S.preflight(args.plan, args.project)
    backup = S.independent(args.backup, plan["workspace_root"], plan["protected_roots"])
    S.require(not backup.exists() and backup.anchor == args.project.anchor
              and not backup.is_relative_to(args.project) and not args.project.is_relative_to(backup), "FRESH_SAME_VOLUME_BACKUP_REQUIRED")
    backup.mkdir(parents=True)
    journal = {"schema": "direct_native_upgrade_journal_v1", "status": "STARTED", "project": str(args.project),
               "plan": S.pin(args.plan), "control_sha256": args.native_go_sha256,
               "started_utc": now(), "phases": {}, "provider_calls_submitted": 0}
    journal_path = backup / "native-journal.json"
    journal["native_journal_path"] = str(journal_path)
    save = lambda: dump(journal_path, journal)
    save()
    try:
        before = metadata(args)
        S.require(before["head"] in plan["migration"]["accepted_existing_heads"], "REVIEWED_EXISTING_SCHEMA_REQUIRED")
        private = [S.pin(S.regular(args.project / ".env"))]
        if Path(before["key_file"]).is_file():
            private.append(S.pin(S.regular(before["key_file"])))
        journal["preserved_private_file_pins"] = private
        preflight = next(row for row in plan["source_files"] if row["path"] == plan["native_preflight_path"])
        run([args.python, "-B", preflight["source"]], args.project, timeout=55, logs=backup / "native-preflight")
        run([args.python, "-B", "-m", "pip", "check"], args.project, timeout=60, logs=backup / "pip-check")
        journal["phases"]["native-preflight"] = "PASS"
        stage = backup / "frontend-stage"
        stage.mkdir()
        package_manifest = args.project / "PACKAGE_MANIFEST.json"
        if package_manifest.is_file():
            baseline = json.loads(package_manifest.read_text())
            for row in baseline["files"]:
                if row["path"].startswith("frontend/"):
                    source = S.regular(args.project / row["path"])
                    if source.is_file() and S.pin(source)["sha256"] == row["sha256"]:
                        destination = stage / Path(row["path"]).relative_to("frontend")
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(source.read_bytes())
        for row in plan["source_files"]:
            if row["path"].startswith("frontend/"):
                destination = stage / Path(row["path"]).relative_to("frontend")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(S.regular(row["source"]).read_bytes())
        npm_cli = Path(args.node).parent / "node_modules/npm/bin/npm-cli.js"
        S.require(npm_cli.is_file(), "INSTALLED_NATIVE_NODE_NPM_CLI_REQUIRED")
        run([args.node, npm_cli, "ci", "--no-audit", "--no-fund"], stage, timeout=300, logs=backup / "npm-ci")
        run([args.node, npm_cli, "run", "build"], stage, timeout=180, logs=backup / "frontend-build")
        journal["phases"]["frontend-staged"] = "PASS"
        save()
        host = checked(args.host_proof, args.host_proof_sha256) if args.host_proof else {"process_families": []}
        families = host.get("process_families", host.get("families", []))
        if families:
            S.require(host.get("status") in {"PASS_MAIN_NORMAL_SPLIT_READONLY", "ROOT_VERIFIED_OWNED_FAMILIES"}, "EXACT_OWNED_HOST_PROOF_REQUIRED")
            host_project = host.get("project", host.get("source_root"))
            if host_project is None and host.get("control"):
                host_control = checked(host["control"]["path"], host["control"]["sha256"])
                host_project = host_control["source_root"]
            S.require(host_project is not None and S.regular(host_project) == args.project, "HOST_PROOF_MUST_BELONG_TO_EXACT_TARGET")
            for family in families:
                validate_family(family, args.powershell)
            for family in families:
                if family["role"] in {"api", "api-denied"}:
                    stop_family(family, args.powershell, journal, save)
        deadline = time.monotonic() + args.drain_seconds
        while True:
            current = metadata(args)
            if not current["pending_jobs"] and not current["pending_requests"]:
                break
            S.require(time.monotonic() < deadline, "BOUNDED_QUEUE_DRAIN_FAILED")
            time.sleep(0.5)
        for family in families:
            if family["role"] not in {"api", "api-denied"}:
                stop_family(family, args.powershell, journal, save)
        ports_free(args)
        target_processes_absent(args)
        idle(metadata(args), True)
        journal["phases"]["owned-services-drained-stopped"] = "PASS"
        save()
        journal["source_apply"] = S.upgrade(args.plan, args.project, backup / "source", services_stopped=True)
        journal["phases"]["source"] = "PASS"
        save()
        journal["migration"] = metadata(args, "migrate", plan["migration"]["target_head"], plan["migration"]["accepted_existing_heads"])
        preserved(args, before)
        journal["phases"]["native-additive-migration"] = "PASS"
        save()
        for name in ("node_modules", "dist"):
            current = S.regular(args.project / "frontend" / name)
            fresh = S.regular(stage / name)
            S.require(fresh.is_dir(), "STAGED_FRONTEND_DIRECTORY_REQUIRED")
            if current.exists():
                previous = backup / "frontend-preimages" / name
                previous.parent.mkdir(parents=True, exist_ok=True)
                os.rename(current, previous)
                journal.setdefault("frontend_preimages", {})[name] = str(previous)
                save()
            os.rename(fresh, current)
            journal.setdefault("frontend_installed", []).append(name)
            save()
        release = {"schema": "direct_native_upgrade_release_v1", "source_rows": [S.normalized(row) for row in plan["source_files"]],
                   "source_authority": plan["source_authority"], "migration_head": plan["migration"]["target_head"],
                   "source_row_count": len(plan["source_files"]), "source_inventory_sha256": S.inventory_hash(plan["source_files"]),
                   "source_authority_sha256": plan["source_authority"]["sha256"],
                   "database_identity": before["database_identity"], "api_port": args.api_port, "frontend_port": args.frontend_port}
        journal["release_metadata"] = S.install_release(args.project, release, backup, plan.get("baseline_release"))
        save()
        log_root = backup / "native-logs"
        log_root.mkdir()
        start_roles(args, release, journal, save, log_root)
        journal["readiness"] = health(args, journal)
        S.require(journal["readiness"]["database"]["head"] == release["migration_head"], "FINAL_SCHEMA_HEAD_REQUIRED")
        preserved(args, before)
        for row in private:
            S.require(S.pin(S.regular(row["path"])) == row, "EXISTING_ENVIRONMENT_OR_KEY_CHANGED")
        journal["source_verify"] = S.verify(args.plan, args.project)
        journal["status"] = "PASS_NATIVE_UPGRADE_AND_FRESH_READINESS_NOT_MODEL_ACCEPTANCE"
        journal["ended_utc"] = now()
        save()
        dump(args.project / STATE, {"schema": "direct_native_managed_processes_v1", "project": str(args.project),
                                   "source_authority": release["source_authority"], "families": journal["new_families"],
                                   "source_authority_sha256": release["source_authority"]["sha256"],
                                   "api_port": args.api_port, "frontend_port": args.frontend_port})
    except BaseException as error:
        journal.update(status="STOP_PRESERVE_STATE_NO_BLIND_RETRY", ended_utc=now(),
                       safe_code=str(error) if isinstance(error, RuntimeError) else "NATIVE_UPGRADE_FAILED_PRIVATE_DETAILS_NOT_EXPORTED")
        save()
        raise
    return {"status": journal["status"], "journal": S.pin(journal_path), "provider_calls_submitted": 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("install", "start", "stop", "pause", "snapshot", "verify", "rollback-source"))
    p.add_argument("--project", type=Path, required=True)
    p.add_argument("--python", type=Path)
    p.add_argument("--node", type=Path)
    p.add_argument("--powershell", type=Path)
    p.add_argument("--database-host", default="127.0.0.1")
    p.add_argument("--database-port", type=int)
    p.add_argument("--database-name")
    p.add_argument("--api-port", type=int)
    p.add_argument("--frontend-port", type=int)
    p.add_argument("--drain-seconds", type=int, default=180)
    p.add_argument("--readiness-seconds", type=int, default=150)
    p.add_argument("--delivery-index", type=Path)
    p.add_argument("--delivery-index-sha256")
    p.add_argument("--workspace-root", type=Path)
    p.add_argument("--protected-root", type=Path, action="append")
    for name in ("plan", "native-go", "host-proof", "backup"):
        p.add_argument("--" + name, type=Path)
        if name != "backup":
            p.add_argument("--" + name + "-sha256")
    args = p.parse_args()
    args.project = S.regular(args.project)
    if args.mode == "verify":
        release = runtime_manifest(args.project, verify_source=args.mode not in {"stop", "rollback-source"})
        print(json.dumps({"status": "PASS_SUCCESSOR_PUBLIC_SOURCE_ONLY", "source_rows": len(release["source_rows"]), "runtime_acceptance": False}))
        return
    S.require(os.name == "nt", "NATIVE_COORDINATOR_REQUIRES_WINDOWS")
    args.python = S.regular(args.python or args.project / ".venv/Scripts/python.exe")
    args.node = S.regular(args.node or shutil.which("node.exe") or "NODE_NOT_FOUND")
    args.powershell = S.regular(args.powershell or shutil.which("pwsh.exe") or shutil.which("powershell.exe") or "POWERSHELL_NOT_FOUND")
    S.require(args.python.is_file() and args.powershell.is_file(), "EXISTING_NATIVE_PYTHON_AND_POWERSHELL_REQUIRED")
    if args.mode in {"install", "start"}:
        S.require(args.node.is_file(), "EXISTING_NATIVE_NODE_REQUIRED")
    S.require(1 <= args.drain_seconds <= 300 and 1 <= args.readiness_seconds <= 300, "FINITE_NATIVE_LIMITS_REQUIRED")
    if args.mode == "install":
        if args.delivery_index:
            S.require(args.delivery_index_sha256 and not args.plan and not args.native_go,
                      "ONE_EXACT_PORTABLE_INDEX_OR_EXPLICIT_PLAN_REQUIRED")
            prepare_delivery(args)
        S.require(all((args.plan, args.plan_sha256, args.native_go, args.native_go_sha256, args.backup,
                       args.api_port, args.frontend_port, args.database_port, args.database_name)), "EXPLICIT_INSTALL_IDENTITIES_REQUIRED")
        result = install(args)
    else:
        release = runtime_manifest(args.project, verify_source=args.mode not in {"stop", "pause", "snapshot", "rollback-source"})
        args.api_port = args.api_port or release["api_port"]
        args.frontend_port = args.frontend_port or release["frontend_port"]
        identity = release["database_identity"]
        args.database_host, args.database_port, args.database_name = identity["host"], identity["port"], identity["database"]
        state_path = args.project / STATE
        original_plan, rollback_authorities = rollback_context(args, release) if args.mode == "rollback-source" else (None, None)
        previous = {}
        if state_path.exists():
            recorded = json.loads(S.regular(state_path).read_text())
            authority = release["source_authority_sha256"]
            if rollback_authorities is not None:
                S.require(recorded["source_authority_sha256"] in rollback_authorities, "MANAGED_STATE_RELEASE_AUTHORITY_MISMATCH")
                authority = recorded["source_authority_sha256"]
            previous = normalize_managed_state(recorded, args.project, authority)
        if args.mode == "start":
            retain = require_previous_stopped(previous, args.powershell)
            diagnostic = S.regular(args.project / "artifacts/runtime" / ("native-preflight-" + uuid4().hex[:8] + ".json"))
            run([args.python, "-B", args.project / "scripts/release/native_preflight.py"], args.project,
                timeout=55, native_diagnostic=diagnostic)
        if args.mode in {"stop", "pause", "snapshot", "rollback-source"}:
            S.require(previous, "RECORDED_MANAGED_PROCESS_STATE_REQUIRED")
            state = previous
            if args.mode == "snapshot":
                for family in state["families"]:
                    refresh_family(family, args.powershell)
                    validate_family(family, args.powershell)
                print(json.dumps({"status": "ROOT_VERIFIED_OWNED_FAMILIES", "project": str(args.project),
                                  "source_authority": release["source_authority"], "families": state["families"]}))
                return
            for family in state["families"]:
                if family["role"] in {"api", "api-denied"}:
                    stop_family(family, args.powershell, state, lambda: dump(state_path, state))
            deadline = time.monotonic() + args.drain_seconds
            while True:
                current = metadata(args)
                if not current["pending_jobs"] and not current["pending_requests"]:
                    break
                S.require(time.monotonic() < deadline, "BOUNDED_QUEUE_DRAIN_FAILED")
                time.sleep(0.5)
            for family in state["families"]:
                if family["role"] not in {"api", "api-denied"} and not (args.mode == "pause" and family["role"] == "frontend"):
                    stop_family(family, args.powershell, state, lambda: dump(state_path, state))
            idle(metadata(args), True)
            state["status"] = "PAUSED_FRONTEND_RETAINED" if args.mode == "pause" else "STOPPED"
            dump(state_path, state)
            result = {"status": "PASS_OWNED_NATIVE_PAUSE_QUEUES0" if args.mode == "pause" else "PASS_OWNED_NATIVE_STOP_QUEUES0",
                      "journal": S.pin(state_path), "database_mutations": 0}
            if args.mode == "rollback-source":
                ports_free(args)
                target_processes_absent(args)
                current = metadata(args)
                S.require(current["answer_only_active_count"] == 0,
                          "ANSWER_ONLY_ACTIVE_RESTORE_EXPLICIT_CHECKED_SELECTION_BEFORE_OLD_SOURCE_ROLLBACK")
                release_update = S.regular(args.backup / "release-update.json")
                if release_update.is_file():
                    S.restore_previous_release(args.project, args.backup, verify_only=True)
                result = S.rollback(args.backup / "source/journal.json")
                if release_update.is_file():
                    result["release_metadata"] = S.restore_previous_release(args.project, args.backup)
                restore_stopped_authority(args, state, original_plan, state_path)
                result["native_capability_gate"] = "PASS_NO_ACTIVE_ANSWER_ONLY_SELECTION"
                result["additive_schema_retained"] = True
        else:
            before = metadata(args)
            idle(before, True)
            S.require(before["head"] == release["migration_head"], "EXISTING_SUCCESSOR_SCHEMA_REQUIRED_NO_AUTOMATIC_IMPORT")
            log_root = S.regular(args.project / "artifacts/runtime" / ("upgrade-start-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")))
            log_root.mkdir(parents=True)
            state = {"schema": "direct_native_managed_processes_v1", "project": str(args.project), "source_authority": release["source_authority"],
                     "source_authority_sha256": release["source_authority_sha256"]}
            save = lambda: dump(state_path, state)
            start_roles(args, release, state, save, log_root, retain=retain)
            state["readiness"] = health(args, state)
            preserved(args, before)
            state["families"] = state.pop("new_families")
            state["status"] = "RUNNING"
            save()
            result = {"status": "PASS_NATIVE_START_AND_FRESH_READINESS_NOT_MODEL_ACCEPTANCE", "provider_calls_submitted": 0}
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "STOP_PRESERVE_STATE", "safe_code": str(error) if isinstance(error, RuntimeError)
                          else "NATIVE_ACTION_FAILED_PRIVATE_DETAILS_NOT_EXPORTED"}))
        raise SystemExit(2)
