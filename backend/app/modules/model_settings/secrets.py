"""Fernet storage with a separate deployment key, never a database or log key."""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path
import subprocess
import tempfile

from cryptography.fernet import Fernet, InvalidToken
from app.core.exceptions import AppError


def _unavailable():
    return AppError(
        "MODEL_UNAVAILABLE",
        detail="Model credential encryption is unavailable. Check the deployment key configuration.",
    )


def _restrict_windows(path: Path):
    if os.name != "nt":
        return
    # Restrict the empty file before secret bytes are written. No shell and no
    # key material in arguments; the caller owns this newly created temp file.
    identity = subprocess.run(
        ["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, text=True, check=True
    )
    sid = next(csv.reader(io.StringIO(identity.stdout)))[1]
    subprocess.run(
        ["icacls", str(path), "/inheritance:r", "/grant:r", f"*{sid}:(F)", "/q"],
        capture_output=True,
        check=True,
    )


def _read_key(settings, *, create=False):
    if settings.model_config_encryption_key:
        return settings.model_config_encryption_key.encode("ascii")
    path = Path(settings.model_config_key_file).absolute()
    if path.is_symlink():
        raise _unavailable()
    if not path.exists() and create and settings.env in {"dev", "test", "demo"}:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=".model-key-", dir=path.parent)
        pending = Path(temporary)
        try:
            _restrict_windows(pending)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = None
                stream.write(Fernet.generate_key())
                stream.flush()
                os.fsync(stream.fileno())
            try:
                # Atomically publish without replacing another process's key.
                os.link(pending, path)
            except FileExistsError:
                pass
        finally:
            if descriptor is not None:
                os.close(descriptor)
            pending.unlink(missing_ok=True)
    return path.read_bytes().strip()


def cipher(settings, *, create=False):
    try:
        return Fernet(_read_key(settings, create=create))
    except (
        OSError,
        ValueError,
        UnicodeError,
        subprocess.SubprocessError,
        IndexError,
        StopIteration,
    ):
        raise _unavailable() from None


def encryption_ready(settings):
    try:
        cipher(settings)
        return True
    except AppError:
        return False


def encrypt(settings, plaintext: str):
    return cipher(settings, create=True).encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(settings, ciphertext: str):
    try:
        return cipher(settings).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError, ValueError):
        raise _unavailable() from None
