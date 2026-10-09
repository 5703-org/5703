"""Real subprocess parsing, size/time limits and credential separation."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import time
import tracemalloc
from unittest.mock import patch

import pytest

from pipelines.parse import CURRENT_PARSER_REVISION, parse
from pipelines.parse_isolated import (
    ABSOLUTE_MAX_BYTES,
    ParseIsolationCancelled,
    ParseIsolationFailure,
    _child_environment,
    _read_result,
    _run_child,
    parse_isolated,
)


def _source(tmp_path):
    path = tmp_path / "source.txt"
    path.write_text(
        "# Cell transport\nCell membranes regulate diffusion and osmosis across a membrane.\n",
        encoding="utf-8",
    )
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _parse(path, digest, tmp_path, **limits):
    return parse_isolated(
        path,
        "text/plain",
        CURRENT_PARSER_REVISION,
        digest,
        temporary_root=tmp_path,
        max_input_bytes=limits.get("input", 1024 * 1024),
        max_output_bytes=limits.get("output", 1024 * 1024),
        timeout_seconds=limits.get("timeout", 20),
    )


def test_isolated_parser_matches_legacy_units_and_cleans_temporary_output(tmp_path):
    path, digest = _source(tmp_path)
    expected = parse(path, "text/plain", parser_revision=CURRENT_PARSER_REVISION)
    result = _parse(path, digest, tmp_path)
    assert result.units == expected
    assert result.child_pid != os.getpid()
    assert result.output_bytes > 0
    assert not list(tmp_path.glob(".parse-isolated-*"))


def test_input_limit_refuses_before_child_and_source_change_is_rejected(tmp_path):
    path, digest = _source(tmp_path)
    with patch("pipelines.parse_isolated.subprocess.Popen") as spawn:
        with pytest.raises(ParseIsolationFailure) as limited:
            _parse(path, digest, tmp_path, input=path.stat().st_size - 1)
        spawn.assert_not_called()
    assert limited.value.code == "PARSER_INPUT_LIMIT"
    with pytest.raises(ParseIsolationFailure) as changed:
        _parse(path, "0" * 64, tmp_path)
    assert changed.value.code == "SOURCE_UNAVAILABLE"
    assert not list(tmp_path.glob(".parse-isolated-*"))


def test_output_limit_refuses_partial_result_and_cleans_temporary_output(tmp_path):
    path, digest = _source(tmp_path)
    with pytest.raises(ParseIsolationFailure) as limited:
        _parse(path, digest, tmp_path, output=32)
    assert limited.value.code == "PARSER_OUTPUT_LIMIT"
    assert not list(tmp_path.glob(".parse-isolated-*"))


def test_malformed_pdf_is_a_bounded_parser_failure(tmp_path):
    source = tmp_path / "malformed.pdf"
    source.write_bytes(b"%PDF-1.7\ninvalid xref and no pages\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(ParseIsolationFailure) as failed:
        parse_isolated(
            source,
            "application/pdf",
            CURRENT_PARSER_REVISION,
            digest,
            temporary_root=tmp_path,
            max_input_bytes=1024 * 1024,
            max_output_bytes=1024 * 1024,
            timeout_seconds=20,
        )
    assert failed.value.code == "PARSER_FAILED"
    assert not list(tmp_path.glob(".parse-isolated-*"))


def test_unwritable_result_directory_fails_after_one_attempt(tmp_path):
    path, digest = _source(tmp_path)
    with (
        patch("pipelines.parse_isolated.Path.mkdir", side_effect=PermissionError) as mkdir,
        patch("pipelines.parse_isolated.subprocess.Popen") as spawn,
    ):
        with pytest.raises(ParseIsolationFailure) as failed:
            _parse(path, digest, tmp_path)
    assert failed.value.code == "PARSER_EXECUTION_ERROR"
    mkdir.assert_called_once()
    spawn.assert_not_called()


def test_wall_timeout_kills_real_child(tmp_path):
    command = [sys.executable, "-c", "import time; time.sleep(30)"]
    with pytest.raises(ParseIsolationFailure) as timed_out:
        _run_child(command, 0.15, None)
    assert timed_out.value.code == "PARSER_TIMEOUT"


def test_cancellation_stops_real_child(tmp_path):
    command = [sys.executable, "-c", "import time; time.sleep(30)"]
    started = time.monotonic()
    with pytest.raises(ParseIsolationCancelled):
        _run_child(command, 5, lambda: time.monotonic() - started > 0.2)


def test_parser_child_environment_excludes_model_and_database_secrets(monkeypatch):
    excluded = {
        "LLM_API_KEY": "private-answer-key-canary-94f801",
        "DATABASE_URL": "postgresql://private-database-url-canary-29c421",
        "SECRET_KEY": "private-signing-key-canary-73f082",
        "PYTHONPATH": "private-import-path-canary-27f833",
    }
    for key, value in excluded.items():
        monkeypatch.setenv(key, value)
    temporary_path = str(Path("private-parser-working-directory").resolve())
    monkeypatch.setenv("TMP", temporary_path)
    child = _child_environment()
    normalized_keys = {key.upper() for key in child}
    assert "PATH" in normalized_keys
    assert child["TMP"] == temporary_path
    assert normalized_keys <= {
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
        "PYTHONIOENCODING",
        "PYTHONDONTWRITEBYTECODE",
    }
    assert not normalized_keys.intersection(excluded)
    assert all(canary not in value for canary in excluded.values() for value in child.values())


@pytest.mark.parametrize("maximum", [256 * 1024 * 1024, ABSOLUTE_MAX_BYTES])
def test_small_real_result_does_not_allocate_its_configured_ceiling(tmp_path, maximum):
    output = tmp_path / "result.json"
    expected = b'{"version":"isolated_parse_v1","child_pid":12345,"units":[]}'
    output.write_bytes(expected)
    assert not tracemalloc.is_tracing()
    tracemalloc.start()
    try:
        actual = _read_result(output, maximum, time.monotonic() + 20, None)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert actual == expected
    # This permits interpreter/file overhead, but catches a 256/512 MiB read
    # allocation for the actual 60-byte result.
    assert peak < 2 * 1024 * 1024


@pytest.mark.parametrize("maximum", [256 * 1024 * 1024, ABSOLUTE_MAX_BYTES])
def test_real_child_keeps_complete_units_with_large_output_ceiling(tmp_path, maximum):
    path, digest = _source(tmp_path)
    expected = parse(path, "text/plain", parser_revision=CURRENT_PARSER_REVISION)
    result = _parse(path, digest, tmp_path, output=maximum)
    assert result.units == expected
    assert result.child_pid != os.getpid()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    assert not list(tmp_path.glob(".parse-isolated-*"))


def test_result_keeps_every_byte_across_multiple_bounded_reads(tmp_path):
    output = tmp_path / "result.json"
    expected = bytes(range(256)) * 900
    output.write_bytes(expected)
    assert _read_result(output, len(expected), time.monotonic() + 20, None) == expected


def _observe_result_reads(monkeypatch, output, after_first=None):
    original_open = Path.open
    reads = []
    streams = []

    class ObservedResult:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def read(self, maximum):
            reads.append(maximum)
            block = self.stream.read(maximum)
            if len(reads) == 1 and after_first is not None:
                after_first(original_open)
            return block

    def open_result(path, mode="r", *args, **kwargs):
        stream = original_open(path, mode, *args, **kwargs)
        if path == output and mode == "rb":
            streams.append(stream)
            return ObservedResult(stream)
        return stream

    monkeypatch.setattr(Path, "open", open_result)
    return reads, streams


def test_result_growth_after_initial_size_check_is_rejected(monkeypatch, tmp_path):
    output = tmp_path / "result.json"
    output.write_bytes(b"a" * (64 * 1024))
    maximum = 128 * 1024
    assert output.stat().st_size <= maximum

    def grow(original_open):
        with original_open(output, "ab") as stream:
            stream.write(b"b" * (128 * 1024))

    reads, streams = _observe_result_reads(monkeypatch, output, grow)
    with pytest.raises(ParseIsolationFailure) as failed:
        _read_result(output, maximum, time.monotonic() + 20, None)
    assert failed.value.code == "PARSER_PROTOCOL_ERROR"
    assert output.stat().st_size > maximum
    assert reads == [64 * 1024, 64 * 1024, 1]
    assert all(stream.closed for stream in streams)


def test_cancellation_during_result_read_stops_before_next_chunk(monkeypatch, tmp_path):
    output = tmp_path / "result.json"
    output.write_bytes(b"a" * (192 * 1024))
    reads, streams = _observe_result_reads(monkeypatch, output)
    cancelled = iter([False, True])
    with pytest.raises(ParseIsolationCancelled):
        _read_result(output, ABSOLUTE_MAX_BYTES, time.monotonic() + 20, lambda: next(cancelled))
    assert reads == [64 * 1024]
    assert all(stream.closed for stream in streams)


def test_deadline_during_result_read_stops_before_next_chunk(monkeypatch, tmp_path):
    output = tmp_path / "result.json"
    output.write_bytes(b"a" * (192 * 1024))
    reads, streams = _observe_result_reads(monkeypatch, output)
    with patch("pipelines.parse_isolated.time.monotonic", side_effect=[0.0, 2.0]):
        with pytest.raises(ParseIsolationFailure) as failed:
            _read_result(output, ABSOLUTE_MAX_BYTES, 1.0, None)
    assert failed.value.code == "PARSER_TIMEOUT"
    assert reads == [64 * 1024]
    assert all(stream.closed for stream in streams)
