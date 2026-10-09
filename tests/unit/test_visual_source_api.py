"""Original PDF rendering is pinned to the released stored source."""

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pymupdf
import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.knowledge.visual_router import original_pdf_page
from app.modules.learning_product import library


def test_original_page_renders_stored_pdf_and_rejects_unavailable_pages(tmp_path, monkeypatch):
    root = tmp_path / "storage"
    originals = root / "originals"
    originals.mkdir(parents=True)
    document = pymupdf.open()
    document.new_page().insert_text((72, 80), "Pinned original textbook page")
    raw = document.tobytes()
    document.close()
    digest = hashlib.sha256(raw).hexdigest()
    filename = originals / f"{digest}.pdf"
    filename.write_bytes(raw)
    version = SimpleNamespace(
        id="version-1", storage_path=f"originals/{digest}.pdf", raw_hash=digest
    )
    monkeypatch.setattr(
        library, "released_rows", lambda *a, **k: (object(), [(None, None, None, version)])
    )
    settings = Settings(_env_file=None, storage_root=str(root))
    actor = SimpleNamespace(id="user", workspace_id="workspace")

    response = original_pdf_page(
        "doc", 1, version.id, digest, db=object(), actor=actor, settings=settings
    )
    assert response.media_type == "image/png"
    assert response.body.startswith(b"\x89PNG")
    assert response.headers["X-Source-SHA256"] == digest
    assert float(response.headers["X-PDF-Page-Width"]) > 0
    assert float(response.headers["X-PDF-Page-Height"]) > 0
    assert response.headers["Cache-Control"] == "private, no-store"
    with pytest.raises(AppError, match="NOT_FOUND"):
        original_pdf_page("doc", 2, version.id, digest, db=object(), actor=actor, settings=settings)
    with pytest.raises(AppError) as stale:
        original_pdf_page(
            "doc", 1, version.id, "b" * 64, db=object(), actor=actor, settings=settings
        )
    assert stale.value.code == "EVIDENCE_UNAVAILABLE"


def test_original_page_rejects_storage_escape(tmp_path, monkeypatch):
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"not a pdf")
    root = tmp_path / "storage"
    root.mkdir()
    version = SimpleNamespace(id="v", storage_path=str(outside), raw_hash="a" * 64)
    monkeypatch.setattr(
        library, "released_rows", lambda *a, **k: (object(), [(None, None, None, version)])
    )
    settings = Settings(_env_file=None, storage_root=str(root))
    actor = SimpleNamespace(id="user", workspace_id="workspace")
    with pytest.raises(AppError, match="SOURCE_UNAVAILABLE"):
        original_pdf_page("doc", 1, "v", "a" * 64, db=object(), actor=actor, settings=settings)
