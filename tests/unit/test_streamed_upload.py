"""Bounded upload reads and temporary-file cleanup at failure boundaries."""

from __future__ import annotations

import asyncio
from io import BytesIO
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.modules.knowledge import service


class InterruptedStream:
    def __init__(self, failure: BaseException):
        self.calls = 0
        self.failure = failure

    def read(self, size):
        assert size <= 64 * 1024
        self.calls += 1
        if self.calls == 1:
            return b"first chunk"
        raise self.failure


def _settings(tmp_path, limit=64):
    return SimpleNamespace(storage_root=str(tmp_path), max_upload_bytes=limit)


def _temporary_files(tmp_path):
    return list(tmp_path.rglob(".upload-*.part"))


def test_upload_exceeds_limit_before_a_large_read_and_removes_stage(tmp_path):
    class SizedStream(BytesIO):
        def read(self, size=-1):
            assert size == 64 * 1024
            return super().read(size)

    with pytest.raises(AppError) as error:
        service.ingest_stream(
            None, _settings(tmp_path), "owner", "large.txt", SizedStream(b"a" * 65), "Large"
        )
    assert error.value.code == "UPLOAD_TOO_LARGE"
    assert _temporary_files(tmp_path) == []


@pytest.mark.parametrize("failure", [OSError("read failed"), asyncio.CancelledError()])
def test_upload_read_failure_or_cancellation_removes_stage(tmp_path, failure):
    with pytest.raises(type(failure)):
        service.ingest_stream(
            None,
            _settings(tmp_path),
            "owner",
            "interrupted.txt",
            InterruptedStream(failure),
            "Interrupted",
        )
    assert _temporary_files(tmp_path) == []


def test_invalid_utf8_isolated_without_storage_or_database_write(tmp_path):
    with pytest.raises(AppError) as error:
        service.ingest_stream(
            None,
            _settings(tmp_path),
            "owner",
            "invalid.txt",
            BytesIO(b"broken \xe2"),
            "Invalid",
        )
    assert error.value.code == "UNSUPPORTED_MEDIA"
    assert _temporary_files(tmp_path) == []


def test_interrupted_original_copy_removes_partial_hash_file_and_stage(tmp_path, monkeypatch):
    class NoExistingVersion:
        bind = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))

        def scalar(self, _query):
            return None

    def interrupted_copy(_source, target, length):
        assert length == 64 * 1024
        target.write(b"partial")
        raise OSError("copy interrupted")

    monkeypatch.setattr(service.shutil, "copyfileobj", interrupted_copy)
    with pytest.raises(OSError, match="copy interrupted"):
        service.ingest_stream(
            NoExistingVersion(),
            _settings(tmp_path),
            "owner",
            "copy.txt",
            BytesIO(b"valid UTF-8"),
            "Copy interrupted",
        )
    assert list((tmp_path / "originals").iterdir()) == []
