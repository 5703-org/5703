"""Runtime public assets support explicit storage without accepting escaped paths."""

from hashlib import sha256
import pytest
from scripts.release.import_public_visuals import original_source, verified_catalog


def source(tmp_path):
    root = tmp_path / "runtime"
    root.mkdir()
    storage = tmp_path / "configured-storage"
    (storage / "originals").mkdir(parents=True)
    content = b"public-source-fixture"
    digest = sha256(content).hexdigest()
    target = storage / "originals" / f"{digest}.pdf"
    target.write_bytes(content)
    return root, storage, target, {"source_path": "old-source/absent.pdf", "source_sha256": digest}


def test_explicit_storage_uses_exact_public_source(tmp_path):
    root, storage, target, book = source(tmp_path)
    assert original_source(book, root, storage_root=storage) == target
    with pytest.raises(ValueError, match="unavailable"):
        original_source(book, root)


def test_corrupted_configured_source_is_rejected(tmp_path):
    root, storage, target, book = source(tmp_path)
    target.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash changed"):
        original_source(book, root, storage_root=storage)


def test_escaped_manifest_path_cannot_fall_back_to_valid_storage(tmp_path):
    root, storage, target, book = source(tmp_path)
    book["source_path"] = "../../outside.pdf"
    with pytest.raises(ValueError, match="escaped"):
        original_source(book, root, storage_root=storage)


def test_catalog_must_be_confined_before_reading(tmp_path):
    root, storage, target, book = source(tmp_path)
    with pytest.raises(ValueError, match="escaped"):
        verified_catalog(tmp_path / "outside", root=root, storage_root=storage)
