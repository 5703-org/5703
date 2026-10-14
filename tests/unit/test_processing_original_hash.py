"""Original integrity is checked before parsing without reading a whole upload."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.exceptions import AppError
from app.modules.knowledge import service
from app.modules.knowledge.models import DocumentVersion, ProcessingRun


def test_original_hash_reads_fixed_blocks(tmp_path):
    original = tmp_path / "large.txt"
    payload = b"source data " * 20000
    original.write_bytes(payload)
    actual_open = Path.open
    read_sizes = []

    class BoundedReader:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def read(self, size):
            read_sizes.append(size)
            assert size == 64 * 1024
            return self.stream.read(size)

    def observed_open(path, *args, **kwargs):
        stream = actual_open(path, *args, **kwargs)
        return BoundedReader(stream) if path == original and args == ("rb",) else stream

    with patch.object(Path, "open", observed_open):
        assert service._file_sha256(original) == hashlib.sha256(payload).hexdigest()
    assert len(read_sizes) >= 4


def test_corrupted_original_is_rejected_before_parser_without_whole_file_read(tmp_path):
    storage = tmp_path / "originals"
    storage.mkdir()
    original = storage / "source.txt"
    expected = b"# Source\nCell membrane transport depends on gradients."
    corrupted = bytearray(expected)
    corrupted[-1] ^= 1
    original.write_bytes(corrupted)
    run = SimpleNamespace(
        id="processing-run",
        state="registered",
        document_version_id="version",
        configuration={"parser_revision": "pypdf_bookmarks_v5"},
        error=None,
    )
    version = SimpleNamespace(
        storage_path="originals/source.txt",
        raw_hash=hashlib.sha256(expected).hexdigest(),
        media_type="text/plain",
    )

    class Session:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0

        def get(self, kind, key):
            if kind is ProcessingRun and key == run.id:
                return run
            if kind is DocumentVersion and key == run.document_version_id:
                return version
            raise AssertionError("Unexpected database lookup")

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    db = Session()
    with (
        patch.object(service, "_execution_fence"),
        patch.object(Path, "read_bytes", side_effect=AssertionError("Whole-file read")),
        patch.object(
            service, "parse", side_effect=AssertionError("Corrupted source was parsed")
        ) as parser,
        patch.object(service, "_file_sha256", wraps=service._file_sha256) as stream_hash,
    ):
        with pytest.raises(AppError) as error:
            service.execute_processing(db, SimpleNamespace(storage_root=str(tmp_path)), run.id)

    assert error.value.code == "SOURCE_UNAVAILABLE"
    stream_hash.assert_called_once_with(original.resolve())
    parser.assert_not_called()
    assert run.state == "failed" and run.error["code"] == "SOURCE_UNAVAILABLE"
    assert db.rollbacks == 1 and db.commits == 2
