"""File-only controls for an exact installed predecessor and runtime metadata rollback."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
SOURCE = Path(
    os.environ.get(
        "CS30_RELEASE_HELPER_UNDER_TEST",
        Path(__file__).resolve().parents[2] / "scripts/release/main201_source.py",
    )
)
SPEC = importlib.util.spec_from_file_location("installed_release_source_under_test", SOURCE)
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class InstalledReleaseControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="cs30-installed-release-", dir=os.environ.get("CS30_RELEASE_TEST_DIRECTORY")
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project, self.backup = self.root / "project", self.root / "backup"
        self.project.mkdir()
        self.backup.mkdir()
        self.file = self.project / "backend/example.py"
        self.file.parent.mkdir()
        self.file.write_bytes(b"original public source\n")
        self.rows = [
            {
                "path": "backend/example.py",
                "bytes": self.file.stat().st_size,
                "sha256": hashlib.sha256(self.file.read_bytes()).hexdigest(),
            }
        ]
        self.release = self.manifest(self.rows)
        self.actual_path = self.project / "UPGRADE_MANIFEST.json"
        self.write(self.actual_path, self.release)
        self.expected = self.root / "EXPECTED-RELEASE.json"
        self.write(self.expected, self.release)

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def manifest(rows):
        return {
            "schema": "direct_native_upgrade_release_v1",
            "source_rows": rows,
            "source_row_count": len(rows),
            "source_inventory_sha256": S.inventory_hash(rows),
            "source_authority_sha256": "a" * 64,
            "source_authority": {"path": "old/location.json", "sha256": "a" * 64},
            "migration_head": "unit_revision",
            "database_identity": {"port": 15432},
            "api_port": 8000,
        }

    def match(self):
        return S.read_installed_baseline(
            self.project, self.expected, S.pin(self.expected)["sha256"]
        )

    def test_installed_complete_baseline_allows_relocated_authority_and_existing_ports(self):
        changed = copy.deepcopy(self.release)
        changed["source_authority"]["path"] = "destination/retained-authority.json"
        changed["database_identity"]["port"] = 15592
        changed["api_port"] = 18092
        self.write(self.actual_path, changed)
        actual, reference = self.match()
        self.assertEqual(actual, changed)
        self.assertEqual(reference, S.pin(self.actual_path))

    def test_source_drift_is_rejected(self):
        self.file.write_bytes(b"unreviewed change")
        with self.assertRaisesRegex(RuntimeError, "SOURCE_DRIFT"):
            self.match()

    def test_empty_duplicate_and_forged_inventory_are_rejected(self):
        variants = []
        empty = self.manifest([])
        variants.append(empty)
        duplicate = self.manifest(self.rows * 2)
        variants.append(duplicate)
        forged = copy.deepcopy(self.release)
        forged["source_inventory_sha256"] = "b" * 64
        variants.append(forged)
        for value in variants:
            with self.subTest(value=value):
                self.write(self.actual_path, value)
                with self.assertRaises(RuntimeError):
                    self.match()

    def test_self_consistent_truncated_manifest_cannot_replace_reviewed_inventory(self):
        second = self.project / "configs/example.yaml"
        second.parent.mkdir()
        second.write_bytes(b"retained\n")
        rows = self.rows + [
            {
                "path": "configs/example.yaml",
                "bytes": second.stat().st_size,
                "sha256": hashlib.sha256(second.read_bytes()).hexdigest(),
            }
        ]
        self.write(self.expected, self.manifest(rows))
        with self.assertRaisesRegex(RuntimeError, "REVIEWED_INSTALLED_BASELINE"):
            self.match()

    def test_pinned_expected_manifest_cannot_be_substituted(self):
        with self.assertRaisesRegex(RuntimeError, "PINNED_INSTALLED_BASELINE"):
            S.read_installed_baseline(self.project, self.expected, "b" * 64)

    def test_manifest_drift_after_plan_is_rejected_before_source_apply(self):
        plan = {
            "schema": "main201_direct_source_plan_v1",
            "target": str(self.project),
            "workspace_root": str(self.root),
            "protected_roots": [str(self.expected)],
            "baseline_kind": "installed",
            "baseline_release": S.pin(self.actual_path),
            "baseline_rows": self.rows,
            "files": [],
            "source_files": [],
        }
        path = self.root / "PLAN.json"
        self.write(path, plan)
        self.release["api_port"] = 18092
        self.write(self.actual_path, self.release)
        with self.assertRaisesRegex(RuntimeError, "INSTALLED_RELEASE_CHANGED_AFTER_PLAN"):
            S.preflight(path, self.project)
        self.assertEqual(self.file.read_bytes(), b"original public source\n")

    def test_exact_previous_manifest_is_backed_up_and_restored(self):
        original = self.actual_path.read_bytes()
        before = S.pin(self.actual_path)
        successor = copy.deepcopy(self.release)
        successor["source_authority_sha256"] = successor["source_authority"]["sha256"] = "b" * 64
        result = S.install_release(self.project, successor, self.backup, before)
        self.assertEqual(result["status"], "APPLIED_RELEASE_METADATA_REPLACEMENT")
        self.assertEqual((self.backup / "release-preimage.json").read_bytes(), original)
        current = self.actual_path.read_bytes()
        checked = S.restore_previous_release(self.project, self.backup, verify_only=True)
        self.assertEqual(checked["metadata_mutations"], 0)
        self.assertEqual(self.actual_path.read_bytes(), current)
        restored = S.restore_previous_release(self.project, self.backup)
        self.assertEqual(restored["status"], "RESTORED_PREVIOUS_RUNTIME_RELEASE_MANIFEST")
        self.assertEqual(self.actual_path.read_bytes(), original)

    def test_legacy_baseline_refuses_an_unowned_runtime_manifest_before_source_apply(self):
        plan = {
            "schema": "main201_direct_source_plan_v1",
            "target": str(self.project),
            "workspace_root": str(self.root),
            "protected_roots": [str(self.expected)],
            "baseline_kind": "current563",
            "baseline_rows": self.rows,
            "files": [],
            "source_files": [],
        }
        path = self.root / "PLAN.json"
        self.write(path, plan)
        with self.assertRaisesRegex(RuntimeError, "UNOWNED_RUNTIME_MANIFEST_BEFORE_SOURCE_APPLY"):
            S.preflight(path, self.project)

    def test_unowned_existing_manifest_is_not_overwritten(self):
        original = self.actual_path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "PRESERVE_UNOWNED"):
            S.install_release(self.project, self.release, self.backup)
        self.assertEqual(self.actual_path.read_bytes(), original)

    def test_external_release_drift_blocks_rollback_preflight(self):
        S.install_release(self.project, self.release, self.backup, S.pin(self.actual_path))
        self.actual_path.write_bytes(b"foreign replacement")
        with self.assertRaisesRegex(RuntimeError, "EXACT_INSTALLED_RELEASE_ROLLBACK"):
            S.restore_previous_release(self.project, self.backup, verify_only=True)

    def test_preimage_drift_blocks_rollback_preflight(self):
        S.install_release(self.project, self.release, self.backup, S.pin(self.actual_path))
        (self.backup / "release-preimage.json").write_bytes(b"foreign preimage")
        with self.assertRaisesRegex(RuntimeError, "EXACT_RELEASE_ROLLBACK_PREIMAGE"):
            S.restore_previous_release(self.project, self.backup, verify_only=True)

    def test_original_install_without_previous_manifest_keeps_legacy_rollback_scope(self):
        self.actual_path.unlink()
        S.install_release(self.project, self.release, self.backup)
        result = S.restore_previous_release(self.project, self.backup)
        self.assertEqual(result["status"], "RETAINED_SUCCESSOR_RELEASE_NO_PREVIOUS_MANIFEST")
        self.assertTrue(self.actual_path.is_file())

    def test_preimage_and_prepared_intent_are_flushed_before_metadata_replacement(self):
        original_fsync, original_atomic = S.os.fsync, S.atomic_source
        flushed = []

        def flush(descriptor):
            flushed.append(descriptor)
            original_fsync(descriptor)

        def atomic(path, raw):
            if path == self.actual_path:
                self.assertGreaterEqual(len(flushed), 2)
            return original_atomic(path, raw)

        with (
            mock.patch.object(S.os, "fsync", side_effect=flush),
            mock.patch.object(S, "atomic_source", side_effect=atomic),
        ):
            S.install_release(self.project, self.release, self.backup, S.pin(self.actual_path))
        self.assertGreaterEqual(len(flushed), 4)

    def test_prepared_metadata_intent_before_swap_keeps_exact_previous_manifest(self):
        before = S.pin(self.actual_path)
        preimage = self.backup / "release-preimage.json"
        preimage.write_bytes(self.actual_path.read_bytes())
        record = {
            "schema": "direct_native_release_replacement_v1",
            "status": "PREPARED_RELEASE_METADATA_REPLACEMENT",
            "project": str(self.project),
            "before": before,
            "before_backup": S.pin(preimage),
            "after": {"path": str(self.actual_path), "bytes": 1, "sha256": "b" * 64},
        }
        self.write(self.backup / "release-update.json", record)
        result = S.restore_previous_release(self.project, self.backup, verify_only=True)
        self.assertEqual(result["status"], "PREVIOUS_RUNTIME_RELEASE_MANIFEST_UNCHANGED")
        self.assertEqual(S.pin(self.actual_path), before)


if __name__ == "__main__":
    unittest.main()
