"""Run one source parser in a bounded child process without worker credentials."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Callable
from uuid import uuid4

from . import parse_worker


POLICY_VERSION = "isolated_parse_v1"
ABSOLUTE_MAX_BYTES = 536_870_912
_RESULT_READ_BYTES = 64 * 1024
_ENVIRONMENT_KEYS = {
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "VIRTUAL_ENV",
}


class ParseIsolationFailure(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class ParseIsolationCancelled(Exception):
    """A revoked durable job stopped its parser child before publication."""


@dataclass(frozen=True)
class ParsedSource:
    units: list[dict]
    child_pid: int
    output_bytes: int


def _child_environment() -> dict[str, str]:
    allowed = {key: value for key, value in os.environ.items() if key.upper() in _ENVIRONMENT_KEYS}
    allowed["PYTHONIOENCODING"] = "utf-8"
    allowed["PYTHONDONTWRITEBYTECODE"] = "1"
    return allowed


def _run_child(command: list[str], timeout_seconds: float, cancel_check: Callable[[], bool] | None):
    deadline = time.monotonic() + timeout_seconds
    try:
        child = subprocess.Popen(
            command,
            cwd=str(Path(__file__).resolve().parents[1]),
            env=_child_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as exc:
        raise ParseIsolationFailure(
            "PARSER_EXECUTION_ERROR", "The isolated parser could not start."
        ) from exc
    try:
        while True:
            if cancel_check is not None and cancel_check():
                raise ParseIsolationCancelled
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ParseIsolationFailure(
                    "PARSER_TIMEOUT", "Source parsing exceeded the configured wall-time limit."
                )
            try:
                return child.wait(timeout=min(0.25, remaining))
            except subprocess.TimeoutExpired:
                continue
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()


@contextmanager
def _result_directory(root: Path):
    # tempfile.mkdtemp retries PermissionError on Windows when os.access says
    # the parent is writable. A sandbox can deny each mkdir despite that check.
    # One unpredictable name and one mkdir produce an immediate, explicit error.
    directory = root / (".parse-isolated-" + uuid4().hex)
    try:
        directory.mkdir(mode=0o700)
    except OSError as exc:
        raise ParseIsolationFailure(
            "PARSER_EXECUTION_ERROR", "Temporary parser storage is unavailable."
        ) from exc
    try:
        yield directory
    finally:
        try:
            (directory / "result.json").unlink(missing_ok=True)
            directory.rmdir()
        except OSError as exc:
            raise ParseIsolationFailure(
                "PARSER_EXECUTION_ERROR", "Temporary parser output could not be removed."
            ) from exc


def _read_result(
    output: Path,
    maximum: int,
    deadline: float,
    cancel_check: Callable[[], bool] | None,
) -> bytes:
    # BufferedReader.read(size) can allocate size before observing EOF. The
    # configured ceiling must bound actual output, not reserve that much memory.
    raw = bytearray()
    with output.open("rb") as stream:
        while True:
            if cancel_check is not None and cancel_check():
                raise ParseIsolationCancelled
            if time.monotonic() >= deadline:
                raise ParseIsolationFailure(
                    "PARSER_TIMEOUT", "Source parsing exceeded the configured wall-time limit."
                )
            block = stream.read(min(_RESULT_READ_BYTES, maximum - len(raw) + 1))
            if not block:
                break
            if len(raw) + len(block) > maximum:
                raise ParseIsolationFailure(
                    "PARSER_PROTOCOL_ERROR", "The isolated parser returned an invalid result size."
                )
            raw.extend(block)
    if cancel_check is not None and cancel_check():
        raise ParseIsolationCancelled
    if time.monotonic() >= deadline:
        raise ParseIsolationFailure(
            "PARSER_TIMEOUT", "Source parsing exceeded the configured wall-time limit."
        )
    return bytes(raw)


def parse_isolated(
    path: Path,
    media_type: str,
    parser_revision: str,
    expected_sha256: str,
    *,
    temporary_root: Path,
    max_input_bytes: int,
    max_output_bytes: int,
    timeout_seconds: float,
    cancel_check: Callable[[], bool] | None = None,
) -> ParsedSource:
    """Return the unchanged parser units, or an explicit non-publishing failure."""
    deadline = time.monotonic() + timeout_seconds
    if (
        not 1 <= max_input_bytes <= ABSOLUTE_MAX_BYTES
        or not 1 <= max_output_bytes <= ABSOLUTE_MAX_BYTES
        or timeout_seconds <= 0
    ):
        raise ValueError("Parser execution limits are invalid")
    if not path.is_file():
        raise ParseIsolationFailure("SOURCE_UNAVAILABLE", "Original source is unavailable.")
    if path.stat().st_size > max_input_bytes:
        raise ParseIsolationFailure(
            "PARSER_INPUT_LIMIT", "Original source exceeds the parser input limit."
        )
    with _result_directory(temporary_root) as work:
        output = Path(work) / "result.json"
        command = [
            sys.executable,
            "-m",
            "pipelines.parse_worker",
            "--source",
            str(path),
            "--media-type",
            media_type,
            "--parser-revision",
            parser_revision,
            "--expected-sha256",
            expected_sha256,
            "--output",
            str(output),
            "--input-max-bytes",
            str(max_input_bytes),
            "--output-max-bytes",
            str(max_output_bytes),
        ]
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ParseIsolationFailure(
                "PARSER_TIMEOUT", "Source parsing exceeded the configured wall-time limit."
            )
        result = _run_child(command, remaining, cancel_check)
        if cancel_check is not None and cancel_check():
            raise ParseIsolationCancelled
        if time.monotonic() > deadline:
            raise ParseIsolationFailure(
                "PARSER_TIMEOUT", "Source parsing exceeded the configured wall-time limit."
            )
        failures = {
            parse_worker.EXIT_SOURCE_UNAVAILABLE: (
                "SOURCE_UNAVAILABLE",
                "Original source changed before isolated parsing.",
            ),
            parse_worker.EXIT_INPUT_LIMIT: (
                "PARSER_INPUT_LIMIT",
                "Original source exceeds the parser input limit.",
            ),
            parse_worker.EXIT_OUTPUT_LIMIT: (
                "PARSER_OUTPUT_LIMIT",
                "Parsed source exceeds the parser output limit.",
            ),
            parse_worker.EXIT_PARSE_FAILED: ("PARSER_FAILED", "Isolated source parsing failed."),
        }
        if result != 0:
            code, message = failures.get(
                result, ("PARSER_EXECUTION_ERROR", "The isolated parser exited unexpectedly.")
            )
            raise ParseIsolationFailure(code, message)
        if not output.is_file() or not 0 < output.stat().st_size <= max_output_bytes:
            raise ParseIsolationFailure(
                "PARSER_PROTOCOL_ERROR", "The isolated parser returned an invalid result size."
            )
        raw = _read_result(output, max_output_bytes, deadline, cancel_check)
        if cancel_check is not None and cancel_check():
            raise ParseIsolationCancelled
        if len(raw) > max_output_bytes:
            raise ParseIsolationFailure(
                "PARSER_PROTOCOL_ERROR", "The isolated parser returned an invalid result size."
            )
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParseIsolationFailure(
                "PARSER_PROTOCOL_ERROR", "The isolated parser returned invalid JSON."
            ) from exc
        if (
            not isinstance(payload, dict)
            or payload.get("version") != POLICY_VERSION
            or type(payload.get("child_pid")) is not int
            or payload["child_pid"] <= 0
            or payload["child_pid"] == os.getpid()
            or not isinstance(payload.get("units"), list)
            or not all(isinstance(unit, dict) for unit in payload["units"])
        ):
            raise ParseIsolationFailure(
                "PARSER_PROTOCOL_ERROR", "The isolated parser returned an invalid result."
            )
        if time.monotonic() > deadline:
            raise ParseIsolationFailure(
                "PARSER_TIMEOUT", "Source parsing exceeded the configured wall-time limit."
            )
        return ParsedSource(payload["units"], payload["child_pid"], len(raw))
