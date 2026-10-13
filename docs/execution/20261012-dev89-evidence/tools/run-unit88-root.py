"""Candidate: run the current Main unit suite using only new W test storage."""

from __future__ import annotations

import argparse
import faulthandler
import hashlib
from http.server import HTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

WORKSPACE = Path(__file__).resolve().parent
MAIN = Path(r"E:\5703\learning-assistant")
PYTHON = MAIN / ".venv/Scripts/python.exe"
PINS = {
    "generation/checked.py": "2b675807b299c2d802eda90ef6dfd10beaeac9a7737ec2dfe40279f66862515b",
    "tests/unit/test_single_selection_teacher_contract.py": "910f812fd96bc729e64ec6eb37696848a743bf8b12d909c65c07f0c08a275efa",
    "tests/unit/test_single_selection_wire_contract.py": "7d06eb097df4612f258e34efbbfbd2c2b754ab973b0c8255d15e101995e1ddae",
    "tests/unit/test_v22_integration.py": "b0ff8b09890860de6b76b5cc0c842d054772b2b1ca7941a4d13a46d7008aae7e",
    "tests/unit/test_lossless_output_integration84.py": "aa07bcf78ba4208cca6016a6960510bac31bae5115588d31b186116e0125aea2",
}
TOKEN_CACHE = {
    "9b5ad71b2ce5302211f9c61530b329a4922fc6a4": "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7",
    "fb374d419588a4632f3f557e76b4b70aebbca790": "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d",
}
HTTP_FIXTURES = {
    "test_adapter_replacement.py": ("local_transport", "fd4e27fed6ec7d9fc15c4bb410aadc05af663359527bfe5d5ebfeabe32728c24"),
    "test_generation_providers.py": ("provider_server", "82633c5db2ab357347e4c26c71ada23ab3f25a696286b223d4b1d566be534d05"),
    "test_model_settings.py": ("probe_server", "4a49627bc8cfe41192becde81ad57b7cec306fc179fe27abce1cf8d8a0265043"),
    "test_provider_switching_matrix.py": ("authored_server", "5dee413a6c92b529f0491d11052ac66069cb904d9876919bbacdf9920446cf48"),
}
PARENT_TIMEOUT_SECONDS = 240
PARSER_DEVNULL_SOURCE_SHA = "d83d84d1a6202714cc0688c5df5db07d38272599530105e83c00f1154402a76d"


def hashes():
    return {name: hashlib.sha256((MAIN / name).read_bytes()).hexdigest() for name in PINS}


def output_path(value):
    result = Path(value).resolve()
    if result == WORKSPACE or not result.is_relative_to(WORKSPACE):
        raise ValueError("Output must be a new child of the current workspace")
    if any(part in {".git", ".agents", ".codex", ".aws"} for part in result.parts):
        raise ValueError("Output cannot be a private or repository metadata directory")
    return result


def environment(output):
    prefixes = (
        "DATABASE", "TEST_DATABASE", "LLM_", "MODEL_", "CHAT_", "MEMORY_",
        "EMBEDDING_", "JWT_", "CS30_", "OPENROUTER", "OPENAI", "ANTHROPIC",
        "DEEPSEEK", "GEMINI", "GOOGLE_APPLICATION_CREDENTIALS", "AZURE_OPENAI",
        "WORKER_", "HF_", "HUGGINGFACE_", "TRANSFORMERS_",
    )
    exact = {
        "SECRET_KEY", "APP_ENV", "ENV", "LOCAL_MODEL_DEVICE", "STORAGE_ROOT",
        "VISUAL_CATALOG_STAGING_ROOT", "SEED_DEMO_USERS", "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS", "PYTHONPATH", "PYTHONPYCACHEPREFIX",
    }
    clean = {
        key: value for key, value in os.environ.items()
        if key.upper() not in exact
        and not key.upper().startswith(prefixes)
        and not any(fragment in key.upper() for fragment in ("API_KEY", "API_TOKEN"))
    }
    clean.update({
        "PYTHONPATH": os.pathsep.join([str(MAIN), str(MAIN / "backend")]),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "MODEL_MODE": "mock", "LLM_PROVIDER": "mock", "EMBEDDING_PROVIDER": "mock",
        "MODEL_CONFIG_KEY_FILE": str(output / "synthetic-key-not-created"),
        "STORAGE_ROOT": str(output / "storage"),
        "VISUAL_CATALOG_STAGING_ROOT": str(output / "visual-staging"),
        "TIKTOKEN_CACHE_DIR": str(output / "tiktoken"),
        "TEMP": str(output / "temp"), "TMP": str(output / "temp"),
        "TMPDIR": str(output / "temp"),
        "HF_HOME": str(output / "hf-cache"), "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
        "TORCH_HOME": str(output / "torch-cache"),
        "RUFF_CACHE_DIR": str(output / "ruff-cache"),
        "MYPY_CACHE_DIR": str(output / "mypy-cache"),
    })
    return clean


class UnitIsolationGuard:
    """Allow only reviewed, currently active test-owned HTTP/socketpair endpoints."""

    def __init__(self, output):
        self.output = output
        self.blocked = []
        self.blocked_context = []
        self.parser_null_events = []
        self.parser_null_path = (MAIN / "pipelines/parse_isolated.py").resolve()
        if hashlib.sha256(self.parser_null_path.read_bytes()).hexdigest() != PARSER_DEVNULL_SOURCE_SHA:
            raise ValueError("Reviewed parser null-device source changed")
        self.subprocess_devnull_code = subprocess.Popen._get_devnull.__code__
        self.listeners = []
        self.owned_connects = 0
        self.owned_dns = 0
        self.socketpair_connects = 0
        self.socketpair_code = getattr(socket.socketpair, "__code__", None)
        self.http_server_bind_code = HTTPServer.server_bind.__code__
        self.fixtures = {}
        for filename, (function, expected) in HTTP_FIXTURES.items():
            path = (MAIN / "tests/unit" / filename).resolve()
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("Reviewed local HTTP fixture changed")
            self.fixtures[str(path).casefold()] = (function, filename)

    def inside(self, value):
        if isinstance(value, int):
            return True
        return Path(os.fsdecode(value)).resolve().is_relative_to(self.output)

    def reject(self, event):
        self.blocked.append(event)
        frame = sys._getframe(1)
        frames = []
        for _ in range(6):
            if frame is None:
                break
            frames.append({"file": frame.f_code.co_filename, "function": frame.f_code.co_name,
                           "line": frame.f_lineno})
            frame = frame.f_back
        self.blocked_context.append({"event": event,
                                     "pytest_current_test": os.environ.get("PYTEST_CURRENT_TEST"),
                                     "python_stack": frames})
        raise PermissionError("Isolated unit tripwire rejected " + event)

    def origin(self):
        frame = sys._getframe(2)
        while frame is not None:
            filename = str(Path(frame.f_code.co_filename).resolve()).casefold()
            fixture = self.fixtures.get(filename)
            if fixture is not None and frame.f_code.co_name == fixture[0]:
                return fixture[1]
            frame = frame.f_back
        return None

    def endpoint(self, listener, *, listening):
        try:
            if listener.fileno() < 0:
                return None
            host, port = listener.getsockname()[:2]
            if host not in {"127.0.0.1", "::1"} or port in {0, 5432, 15433}:
                return None
            if listening and not listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN):
                return None
            return host, port
        except OSError:
            return None

    def owned_endpoint(self, address):
        if not isinstance(address, tuple) or len(address) < 2:
            return False
        host, port = address[:2]
        if host not in {"127.0.0.1", "::1"} or not isinstance(port, int):
            return False
        if port in {0, 5432, 15433}:
            return False
        return any(self.endpoint(sock, listening=True) == (host, port)
                   for sock, _fixture in self.listeners)

    def literal_http_name(self, name=""):
        frame = sys._getframe(1)
        if frame.f_code is self.http_server_bind_code and name in {"127.0.0.1", "::1"}:
            server = frame.f_locals.get("self")
            listener = getattr(server, "socket", None)
            if any(listener is sock for sock, _fixture in self.listeners):
                endpoint = self.endpoint(listener, listening=False)
                if endpoint is not None and endpoint[0] == name:
                    return name
        self.reject("socket.getfqdn")

    def reviewed_parser_devnull(self, path, mode, flags, frame):
        # Permit the precise Windows discard device, not a directory or filename
        # named NUL. The exact byte-for-byte os.devnull literal is required.
        if os.name != "nt" or os.devnull.casefold() != "nul":
            return False
        if not isinstance(path, str) or path != os.devnull or mode is not None:
            return False
        allowed_flags = (
            os.O_RDWR | getattr(os, "O_NOINHERIT", 0)
            | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_BINARY", 0)
        )
        if not isinstance(flags, int) or flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR) != os.O_RDWR:
            return False
        if flags & ~allowed_flags:
            return False
        if frame.f_code is not self.subprocess_devnull_code:
            return False
        module = sys.modules.get("pipelines.parse_isolated")
        function = getattr(module, "_run_child", None)
        parser_code = getattr(function, "__code__", None)
        if parser_code is None or Path(parser_code.co_filename).resolve() != self.parser_null_path:
            return False
        caller = frame.f_back
        for _ in range(16):
            if caller is None:
                return False
            if caller.f_code is parser_code:
                self.parser_null_events.append({
                    "event": "reviewed_parser_devnull",
                    "device": os.devnull,
                    "flags": flags,
                    "pytest_current_test": os.environ.get("PYTEST_CURRENT_TEST"),
                })
                return True
            caller = caller.f_back
        return False

    def audit(self, event, args):
        if event == "socket.bind":
            sock, address = args
            frame = sys._getframe(1)
            if (frame.f_code is self.socketpair_code and isinstance(address, tuple)
                    and address[:2] in {("127.0.0.1", 0), ("::1", 0)}):
                return
            fixture = self.origin()
            if (fixture is None or not isinstance(address, tuple)
                    or address[:2] not in {("127.0.0.1", 0), ("::1", 0)}):
                self.reject(event)
            self.listeners.append((sock, fixture))
        if event == "socket.getaddrinfo":
            host, port = args[:2]
            if not self.owned_endpoint((host, port)):
                self.reject(event)
            self.owned_dns += 1
        elif event in {"socket.gethostbyaddr", "socket.gethostbyname", "socket.gethostbyname_ex"}:
            self.reject(event)
        elif event == "socket.connect":
            frame = sys._getframe(1)
            permitted = False
            if frame.f_code is self.socketpair_code:
                values = frame.f_locals
                listener = values.get("lsock")
                pair_socket = values.get("csock")
                endpoint = (values.get("addr"), values.get("port"))
                permitted = (
                    args[0] is pair_socket and args[1] == endpoint
                    and endpoint[0] in {"127.0.0.1", "::1"}
                    and listener is not None and listener.getsockname()[:2] == endpoint
                )
            if not permitted:
                if not self.owned_endpoint(args[1]):
                    self.reject(event)
                self.owned_connects += 1
            else:
                self.socketpair_connects += 1
        elif event == "sqlite3.connect":
            database = os.fsdecode(args[0])
            # URI parsing is outside Path confinement. No current unit fixture
            # requires SQLite file: URIs, including shared-memory variants.
            if database.casefold().startswith("file:"):
                self.reject("sqlite_file_uri")
            if database not in {"", ":memory:"} and not self.inside(database):
                self.reject(event)
        elif event == "open":
            path, mode, flags = args
            if self.reviewed_parser_devnull(path, mode, flags, sys._getframe(1)):
                return
            if os.name == "nt" and isinstance(path, (str, bytes, os.PathLike)):
                basename = os.fsdecode(path).replace("/", "\\").rsplit("\\", 1)[-1]
                reserved = basename.rstrip(" .").split(":", 1)[0].split(".", 1)[0]
                alias_writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or bool(
                    flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                )
                if reserved.casefold() == "nul" and alias_writing:
                    self.reject("unreviewed_devnull_alias")
            if isinstance(path, (str, bytes, os.PathLike)):
                writing = (isinstance(mode, str) and any(letter in mode for letter in "wax+"))
                writing = writing or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
                if writing and not self.inside(path):
                    self.reject(event)
                resolved = Path(os.fsdecode(path)).resolve()
                if not resolved.is_relative_to(self.output) and (
                    resolved.name == ".env" or ".secrets" in resolved.parts
                ):
                    self.reject("private_store_read")
        elif event in {"os.mkdir", "os.remove", "os.rmdir", "os.chmod"}:
            if not self.inside(args[0]):
                self.reject(event)
        elif event in {"os.rename", "os.link"}:
            if not self.inside(args[0]) or not self.inside(args[1]):
                self.reject(event)
        elif event == "os.symlink":
            if not self.inside(args[1]):
                self.reject(event)

    def install(self):
        sys.addaudithook(self.audit)
        socket.getfqdn = self.literal_http_name
        # libpq opens native sockets, so the Python socket audit alone is not
        # enough to prevent a PostgreSQL connection.
        import psycopg

        def no_postgres(*_args, **_kwargs):
            self.reject("postgres_connection")

        psycopg.connect = no_postgres
        psycopg.Connection.connect = classmethod(no_postgres)
        psycopg.AsyncConnection.connect = classmethod(no_postgres)

    def summary(self):
        return {
            "blocked_events": self.blocked, "external_network_allowed": False,
            "blocked_event_context": self.blocked_context,
            "reviewed_parser_devnull_events": self.parser_null_events,
            "postgres_connections_allowed": False,
            "owned_fixture_http_connects": self.owned_connects,
            "owned_fixture_dns_resolutions": self.owned_dns,
            "windows_socketpair_connects": self.socketpair_connects,
            "fixture_listeners": [
                {"fixture": fixture, "still_active": self.endpoint(sock, listening=True) is not None}
                for sock, fixture in self.listeners
            ],
            "python_writes_confined_to_new_output": True,
        }


def child(output):
    guard = UnitIsolationGuard(output)
    guard.install()

    from app.core.config import Settings

    # This process alone disables dotenv; production source remains unchanged.
    Settings.model_config["env_file"] = None
    import pytest

    args = [
        "-c", str(MAIN / "pytest.ini"), str(MAIN / "tests/unit"),
        "-vv", "--tb=short", "-p", "no:cacheprovider", "--basetemp=" + str(output / "pytest-temp"),
        "--junitxml=" + str(output / "pytest.xml"),
        "-o", "log_file=" + str(output / "pytest-logging.log"),
    ]
    with (output / "faulthandler.log").open("x", encoding="utf-8") as stacks:
        faulthandler.enable(file=stacks)
        faulthandler.dump_traceback_later(20, repeat=True, file=stacks)
        try:
            code = int(pytest.main(args))
        finally:
            faulthandler.cancel_dump_traceback_later()
            (output / "tripwire.json").write_text(
                json.dumps(guard.summary(), indent=2) + "\n", encoding="utf-8",
            )
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = output_path(args.output)
    if args.child:
        return child(output)
    before = hashes()
    if before != PINS:
        raise ValueError("The reviewed three-file Main version has changed")
    output.mkdir(parents=False, exist_ok=False)
    for directory in ("temp", "tiktoken"):
        (output / directory).mkdir()
    copied = []
    for name, expected in TOKEN_CACHE.items():
        data = (MAIN / "artifacts/tiktoken" / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Existing offline tokenizer cache failed its source pin")
        with (output / "tiktoken" / name).open("xb") as stream:
            stream.write(data)
        copied.append({"name": name, "bytes": len(data), "sha256": expected})
    command = [str(PYTHON), "-B", "-X", "utf8", str(Path(__file__).resolve()),
               "--output", str(output), "--child"]
    started = time.perf_counter()
    with (output / "pytest.log").open("x", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=MAIN, env=environment(output),
                                   stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        timed_out = False
        killed = False
        try:
            exit_code = process.wait(timeout=PARENT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                exit_code = process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                killed = True
                process.kill()
                exit_code = process.wait(timeout=3)
    after = hashes()
    receipt = {
        "exit_code": exit_code, "seconds": time.perf_counter() - started,
        "owned_child_pid": process.pid, "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
        "timed_out": timed_out, "terminated_only_owned_child": timed_out,
        "kill_fallback_only_owned_child": killed,
        "source_pins_before": before, "source_pins_after": after,
        "reviewed_version_unchanged": before == after == PINS,
        "unit_test_files": len(list((MAIN / "tests/unit").glob("test*.py"))),
        "child_working_directory": str(MAIN),
        "dotenv_disabled_in_child": True,
        "offline_cache_copies": copied, "scope": "full unit suite only",
        "pytest_log": "pytest.log", "junit_xml": "pytest.xml", "tripwire": "tripwire.json",
        "subprocess_scope": "Authored parser, CLI and Windows ACL fixture controls; reviewed source",
        "postgres_integration_excluded": True,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"exit_code": exit_code, "seconds": receipt["seconds"],
                      "timed_out": timed_out,
                      "reviewed_version_unchanged": receipt["reviewed_version_unchanged"],
                      "receipt": str(output / "receipt.json")}))
    return exit_code if receipt["reviewed_version_unchanged"] and not timed_out else 2


if __name__ == "__main__":
    raise SystemExit(main())
