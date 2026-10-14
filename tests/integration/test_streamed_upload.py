"""HTTP upload preserves source hashes while reading UTF-8 in bounded chunks."""

from __future__ import annotations

import hashlib
from pathlib import Path


def test_streamed_upload_handles_split_utf8_and_cleans_temporary_files(runtime):
    payload = b"a" * 65535 + "€".encode("utf-8")
    response = runtime.client.post(
        "/api/v1/documents",
        headers=runtime.headers("admin@example.com"),
        data={"title": "Split UTF-8 stream"},
        files={"file": ("split-utf8.txt", payload, "text/plain")},
    )
    assert response.status_code == 201, response.text
    version = response.json()["data"]["version"]
    assert version["size_bytes"] == len(payload)
    assert version["raw_hash"] == hashlib.sha256(payload).hexdigest()
    assert Path(runtime.settings.storage_root, version["storage_path"]).read_bytes() == payload
    assert list(Path(runtime.settings.storage_root).rglob(".upload-*.part")) == []


def test_streamed_http_upload_rejects_over_limit_without_a_staging_or_original_file(runtime):
    root = Path(runtime.settings.storage_root)
    previous = runtime.settings.max_upload_bytes
    runtime.settings.max_upload_bytes = 64
    try:
        response = runtime.client.post(
            "/api/v1/documents",
            headers=runtime.headers("admin@example.com"),
            data={"title": "Bounded upload"},
            files={"file": ("too-large.txt", b"x" * 65, "text/plain")},
        )
    finally:
        runtime.settings.max_upload_bytes = previous
    assert response.status_code == 413
    assert list(root.rglob(".upload-*.part")) == []
    assert not (root / "originals" / (hashlib.sha256(b"x" * 65).hexdigest() + ".txt")).exists()
