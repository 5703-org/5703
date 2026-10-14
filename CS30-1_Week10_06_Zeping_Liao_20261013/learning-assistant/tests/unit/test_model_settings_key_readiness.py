"""First-use key readiness; crypto/files only, no database or provider."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "backend/app/modules/model_settings/secrets.py"
spec = spec_from_file_location("model_settings_key_readiness_subject", SOURCE)
secrets = module_from_spec(spec)
spec.loader.exec_module(secrets)


class KeyReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(prefix="key-readiness-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.key = self.root / "private/model-config.key"
        self.settings = SimpleNamespace(
            env="dev", model_config_key_file=str(self.key), model_config_encryption_key=None
        )

    def test_first_development_readiness_creates_usable_key(self):
        restricted_empty_files = []

        def restrict(path):
            self.assertEqual(path.read_bytes(), b"")
            self.assertEqual(path.parent, self.key.parent)
            restricted_empty_files.append(path)

        with patch.object(secrets, "_restrict_windows", side_effect=restrict):
            self.assertTrue(secrets.encryption_ready(self.settings))
            original = self.key.read_bytes()
            self.assertEqual(len(original), 44)
            self.assertEqual(len(restricted_empty_files), 1)
            self.assertTrue(secrets.encryption_ready(self.settings))
            ciphertext = secrets.encrypt(self.settings, "local-test-credential")
            self.assertEqual(secrets.decrypt(self.settings, ciphertext), "local-test-credential")
            self.assertEqual(self.key.read_bytes(), original)
            self.assertEqual(len(restricted_empty_files), 1)
            self.assertEqual(list(self.key.parent.glob(".model-key-*")), [])

    def test_existing_key_and_ciphertext_are_preserved(self):
        self.key.parent.mkdir()
        original = Fernet.generate_key()
        self.key.write_bytes(original)
        ciphertext = Fernet(original).encrypt(b"already-saved").decode("ascii")
        with patch.object(
            secrets, "_restrict_windows", side_effect=AssertionError("unexpected creation")
        ):
            self.assertTrue(secrets.encryption_ready(self.settings))
            self.assertEqual(secrets.decrypt(self.settings, ciphertext), "already-saved")
            self.assertEqual(self.key.read_bytes(), original)

    def test_production_readiness_never_creates_missing_key(self):
        self.settings.env = "production"
        with patch.object(
            secrets, "_restrict_windows", side_effect=AssertionError("unexpected creation")
        ):
            self.assertFalse(secrets.encryption_ready(self.settings))
            with self.assertRaises(secrets.AppError):
                secrets.encrypt(self.settings, "local-test-credential")
        self.assertFalse(self.key.parent.exists())

    def test_invalid_environment_key_does_not_fall_back_to_existing_file(self):
        self.key.parent.mkdir()
        original = Fernet.generate_key()
        self.key.write_bytes(original)
        for invalid in ("invalid-fernet-key", "non-ascii-\u2603"):
            with self.subTest(invalid_type="ascii" if invalid.isascii() else "unicode"):
                self.settings.model_config_encryption_key = invalid
                self.assertFalse(secrets.encryption_ready(self.settings))
                with self.assertRaises(secrets.AppError):
                    secrets.encrypt(self.settings, "local-test-credential")
                self.assertEqual(self.key.read_bytes(), original)

    def test_invalid_existing_file_is_retained_and_not_replaced(self):
        self.key.parent.mkdir()
        original = b"x" * 48
        self.key.write_bytes(original)
        with patch.object(
            secrets, "_restrict_windows", side_effect=AssertionError("unexpected replacement")
        ):
            self.assertFalse(secrets.encryption_ready(self.settings))
            self.assertEqual(self.key.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
