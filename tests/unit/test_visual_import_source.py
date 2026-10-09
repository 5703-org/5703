"""A portable visual catalog must resolve the same official PDF bytes."""

from hashlib import sha256

import pytest

from scripts.verify.import_visual_regions import original_source


def test_portable_visual_source_accepts_exact_installed_pdf(tmp_path):
    raw = b"official source bytes for a portable installation"
    digest = sha256(raw).hexdigest()
    installed = tmp_path / "artifacts" / "storage" / "originals" / f"{digest}.pdf"
    installed.parent.mkdir(parents=True)
    installed.write_bytes(raw)
    book = {"source_path": "artifacts/openstax/originals/absent.pdf", "source_sha256": digest}

    assert original_source(book, tmp_path) == installed.resolve()


def test_portable_visual_source_rejects_changed_copy_without_falling_back(tmp_path):
    raw = b"authentic official source bytes"
    digest = sha256(raw).hexdigest()
    installed = tmp_path / "artifacts" / "storage" / "originals" / f"{digest}.pdf"
    bundled = tmp_path / "resources" / "official-corpus" / "storage" / "originals" / f"{digest}.pdf"
    installed.parent.mkdir(parents=True)
    bundled.parent.mkdir(parents=True)
    installed.write_bytes(b"changed source")
    bundled.write_bytes(raw)
    book = {"source_path": "artifacts/openstax/originals/absent.pdf", "source_sha256": digest}

    with pytest.raises(ValueError, match="hash changed"):
        original_source(book, tmp_path)


def test_portable_visual_source_rejects_manifest_path_escape(tmp_path):
    digest = sha256(b"x").hexdigest()
    book = {"source_path": "../../outside.pdf", "source_sha256": digest}

    with pytest.raises(ValueError, match="escaped"):
        original_source(book, tmp_path)
