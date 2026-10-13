"""Hydrate this candidate's fixed public assets without shipping runtime caches.

Only the pinned manifest's artifact targets are writable. All immutable inputs
and all existing selected outputs are checked before the first creation. A
failure retains every pre-existing file and any newly created partial output.
"""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys


MANIFEST_SHA256 = "9c1e4f05c16bb74f1b36080ad7a05c5a6e64e487448385754243112ad349bb20"
MANIFEST_PATH = "resources/model-assets/MANIFEST.json"
CHUNK_BYTES = 1024 * 1024
MAX_ASSET_BYTES = 512 * CHUNK_BYTES
MAX_MANIFEST_BYTES = 128 * 1024
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


class HydrationError(Exception):
    """A finite diagnostic containing only an approved relative public path."""

    def __init__(self, code: str, target: str = ""):
        super().__init__(code)
        self.code, self.target = code, target
        self.created: list[str] = []


def _need(value, code, target=""):
    if not value:
        raise HydrationError(code, target)


def _relative(value):
    _need(isinstance(value, str) and value and "\\" not in value and ":" not in value,
          "INVALID_RELATIVE_PATH")
    p = PurePosixPath(value)
    _need(not p.is_absolute() and p.as_posix() == value, "INVALID_RELATIVE_PATH")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                *(f"LPT{i}" for i in range(1, 10))}
    for part in p.parts:
        _need(part not in {"", ".", ".."} and part.rstrip(" .") == part
              and not any(ord(c) < 32 for c in part)
              and part.split(".")[0].upper() not in reserved,
              "INVALID_RELATIVE_PATH")
        _need(part.casefold() not in {".secrets", "private", "private_fixture", ".git",
                                    "week09-private-db", "eval-private", "evaluator-private"}
              and not part.casefold().startswith(".env"), "PRIVATE_PATH_REFUSED")
    _need(p.suffix.casefold() not in {".key", ".pem", ".db", ".dump", ".sqlite", ".sqlite3"},
          "PRIVATE_PATH_REFUSED")
    return p


def _normal(path, *, directory):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    _need(not stat.S_ISLNK(info.st_mode)
          and not getattr(info, "st_file_attributes", 0) & 0x400,
          "REPARSE_OR_SYMLINK_REFUSED")
    _need(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
          "ORDINARY_DIRECTORY_REQUIRED" if directory else "ORDINARY_FILE_REQUIRED")
    return True


class _WindowsIO:
    """Stdlib handle leases; never lock a global ancestor directory."""

    def __init__(self):
        from ctypes import wintypes
        self.dll = ctypes.WinDLL("kernel32", use_last_error=True)
        self.dll.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
            wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
            wintypes.HANDLE]
        self.dll.CreateFileW.restype = wintypes.HANDLE
        self.dll.CloseHandle.argtypes = [wintypes.HANDLE]
        self.dll.CloseHandle.restype = wintypes.BOOL
        self.dll.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE,
            ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.dll.GetFileInformationByHandleEx.restype = wintypes.BOOL

    def _open(self, path, *, directory=False, create=False):
        access = 0x80 if directory else (0xC0000000 if create else 0x80000000)
        share = 3 if directory else (0 if create else 1)
        flags = 0x00200000 | (0x02000000 if directory else 0x80)
        handle = self.dll.CreateFileW(str(path), access, share, None,
                                      1 if create else 3, flags, None)
        if handle == ctypes.c_void_p(-1).value:
            code = ctypes.get_last_error()
            if code in {80, 183}:
                raise FileExistsError
            if code in {2, 3}:
                raise FileNotFoundError
            raise HydrationError(f"WINDOWS_FILE_ACTION_REFUSED_{code}")
        attributes = (ctypes.c_uint32 * 2)()
        if not self.dll.GetFileInformationByHandleEx(handle, 9,
                ctypes.byref(attributes), ctypes.sizeof(attributes)):
            code = ctypes.get_last_error()
            self.dll.CloseHandle(handle)
            raise HydrationError(f"WINDOWS_FILE_METADATA_REFUSED_{code}")
        if attributes[0] & 0x400 or bool(attributes[0] & 0x10) != directory:
            self.dll.CloseHandle(handle)
            raise HydrationError("REPARSE_OR_WRONG_HANDLE_TYPE_REFUSED")
        return handle

    def lease_directory(self, path):
        handle = self._open(path, directory=True)

        def close():
            _need(self.dll.CloseHandle(handle), "DIRECTORY_HANDLE_CLOSE_FAILED")

        return close

    def file(self, path, *, create=False):
        import msvcrt
        handle = self._open(path, create=create)
        try:
            descriptor = msvcrt.open_osfhandle(handle,
                os.O_BINARY | (os.O_RDWR if create else os.O_RDONLY))
        except Exception:
            self.dll.CloseHandle(handle)
            raise
        try:
            return os.fdopen(descriptor, "w+b" if create else "rb")
        except Exception:
            os.close(descriptor)
            raise


class _Tree:
    def __init__(self, root, stack):
        self.root = Path(os.path.abspath(root))
        self.stack, self.leased = stack, set()
        self.windows = _WindowsIO() if os.name == "nt" else None
        # Read metadata only outside the project; leases remain project-scoped.
        for directory in reversed((self.root, *self.root.parents)):
            _need(_normal(directory, directory=True), "PROJECT_PATH_UNAVAILABLE")
        self._lease(self.root)

    def path(self, relative):
        return self.root.joinpath(*_relative(relative).parts)

    def _lease(self, directory):
        _need(directory == self.root or directory.is_relative_to(self.root),
              "OUTSIDE_PROJECT_REFUSED")
        if directory not in self.leased:
            _need(_normal(directory, directory=True), "DIRECTORY_UNAVAILABLE")
            if self.windows:
                self.stack.callback(self.windows.lease_directory(directory))
            self.leased.add(directory)

    def parents(self, relative, *, create=False):
        target = self.path(relative)
        current = self.root
        for part in target.relative_to(self.root).parts[:-1]:
            current = current / part
            if not _normal(current, directory=True):
                if not create:
                    return False
                try:
                    current.mkdir()
                except FileExistsError:
                    pass
                _need(_normal(current, directory=True), "DIRECTORY_CREATION_CONFLICT", relative)
            self._lease(current)
        return True

    def read(self, relative):
        if not self.parents(relative):
            raise FileNotFoundError
        path = self.path(relative)
        if not _normal(path, directory=False):
            raise FileNotFoundError
        if self.windows:
            stream = self.windows.file(path)
        else:
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            stream = os.fdopen(descriptor, "rb")
        _need(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "ORDINARY_FILE_REQUIRED", relative)
        return self.stack.enter_context(stream)

    def create(self, relative):
        self.parents(relative, create=True)
        path = self.path(relative)
        if self.windows:
            stream = self.windows.file(path, create=True)
        else:
            descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0), 0o600)
            stream = os.fdopen(descriptor, "w+b")
        return self.stack.enter_context(stream)


def _hash(stream, size, target):
    stream.seek(0)
    digest, count = hashlib.sha256(), 0
    while block := stream.read(CHUNK_BYTES):
        count += len(block)
        _need(count <= size, "SIZE_MISMATCH", target)
        digest.update(block)
    _need(count == size, "SIZE_MISMATCH", target)
    stream.seek(0)
    return digest.hexdigest()


def _pin(row):
    _need(type(row.get("bytes")) is int and 0 <= row["bytes"] <= MAX_ASSET_BYTES,
          "INVALID_SIZE")
    _need(isinstance(row.get("sha256"), str)
          and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]), "INVALID_SHA256")
    _need(type(row.get("optional")) is bool, "INVALID_OPTIONAL_FLAG")


def _manifest(raw, expected_sha):
    _need(len(raw) <= MAX_MANIFEST_BYTES
          and hashlib.sha256(raw).hexdigest() == expected_sha, "MANIFEST_PIN_MISMATCH")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            _need(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=unique)
    _need(value.get("format") == "cs30-public-model-assets-v1", "MANIFEST_FORMAT")
    assets, markers, derived = (value.get(key) for key in
                              ("assets", "empty_markers", "derived_files"))
    _need(isinstance(assets, list) and len(assets) == 26
          and sum(row.get("optional") is False for row in assets) == 23
          and sum(row.get("optional") is True for row in assets) == 3,
          "ASSET_CARDINALITY")
    _need(isinstance(markers, list) and len(markers) == 4
          and isinstance(derived, list) and len(derived) == 1,
          "DERIVED_CARDINALITY")
    source_names, targets = set(), set()
    by_source = {}
    for row in assets:
        _pin(row)
        source, target = _relative(row["asset"]), _relative(row["target"])
        _need(source.parts[:2] == ("resources", "model-assets"), "SOURCE_PREFIX_REFUSED")
        _need(target.parts[:2] == ("artifacts", "huggingface")
              or target.parts[:3] == ("artifacts", "reranker-onnx", "20260926"),
              "TARGET_PREFIX_REFUSED")
        _need(row["asset"] not in source_names and row["target"] not in targets,
              "DUPLICATE_MEMBER")
        source_names.add(row["asset"])
        targets.add(row["target"])
        by_source[row["asset"]] = row
    for row in markers:
        _pin(row)
        target = _relative(row["target"])
        _need(target.parts[:2] == ("artifacts", "huggingface")
              and ".no_exist" in target.parts and row["bytes"] == 0
              and row["sha256"] == EMPTY_SHA256 and row["optional"] is False
              and row.get("derived") is True, "INVALID_EMPTY_MARKER")
        _need(row["target"] not in targets, "DUPLICATE_MEMBER")
        targets.add(row["target"])
    for row in derived:
        _pin(row)
        target = _relative(row["target"])
        _need(target.parts[:2] == ("artifacts", "huggingface")
              and "blobs" in target.parts and row["asset"] in by_source
              and row["asset"].endswith("/README.md")
              and row["optional"] is False and row.get("derived") is True,
              "INVALID_DERIVED_FILE")
        asset = by_source[row["asset"]]
        _need((row["bytes"], row["sha256"]) == (asset["bytes"], asset["sha256"]),
              "DERIVED_SOURCE_MISMATCH")
        _need(row["target"] not in targets, "DUPLICATE_MEMBER")
        targets.add(row["target"])
    return value


def hydrate(project_root, *, verify_only=False, include_optional=False,
            expected_manifest_sha256=MANIFEST_SHA256):
    """Tests may provide a separately pinned synthetic manifest; CLI cannot."""
    created, reused = [], []
    try:
        with ExitStack() as stack:
            tree = _Tree(project_root, stack)
            manifest_stream = tree.read(MANIFEST_PATH)
            raw = manifest_stream.read(MAX_MANIFEST_BYTES + 1)
            manifest = _manifest(raw, expected_manifest_sha256)
            sources = {}
            # Pin and hash every one of the 26 immutable files before mutation.
            for row in manifest["assets"]:
                stream = tree.read(row["asset"])
                _need(_hash(stream, row["bytes"], row["asset"]) == row["sha256"],
                      "SOURCE_HASH_MISMATCH", row["asset"])
                sources[row["asset"]] = stream
            outputs = [row for row in manifest["assets"]
                       if include_optional or not row["optional"]]
            outputs += manifest["empty_markers"] + manifest["derived_files"]
            missing = []
            for row in outputs:
                try:
                    existing = tree.read(row["target"])
                except FileNotFoundError:
                    if verify_only:
                        raise HydrationError("MISSING_RUNTIME_TARGET", row["target"])
                    missing.append(row)
                    continue
                _need(_hash(existing, row["bytes"], row["target"]) == row["sha256"],
                      "EXISTING_TARGET_DIFFERS", row["target"])
                reused.append(row["target"])
            # Every existing target is now pinned and equal; no file is replaced.
            for row in missing:
                try:
                    output = tree.create(row["target"])
                except FileExistsError:
                    existing = tree.read(row["target"])
                    _need(_hash(existing, row["bytes"], row["target"]) == row["sha256"],
                          "CONCURRENT_TARGET_DIFFERS", row["target"])
                    reused.append(row["target"])
                    continue
                created.append(row["target"])
                source = sources.get(row.get("asset")) or io.BytesIO(b"")
                source.seek(0)
                digest, count = hashlib.sha256(), 0
                while block := source.read(CHUNK_BYTES):
                    count += len(block)
                    _need(count <= row["bytes"], "SOURCE_CHANGED_DURING_COPY", row["target"])
                    digest.update(block)
                    output.write(block)
                _need(count == row["bytes"] and digest.hexdigest() == row["sha256"],
                      "SOURCE_CHANGED_DURING_COPY", row["target"])
                output.flush()
                os.fsync(output.fileno())
                _need(_hash(output, row["bytes"], row["target"]) == row["sha256"],
                      "OUTPUT_READBACK_MISMATCH", row["target"])
            result = {"status": "PUBLIC_MODEL_ASSETS_VERIFY_PASS" if verify_only
                      else "PUBLIC_MODEL_ASSETS_HYDRATE_PASS",
                      "manifest_sha256": expected_manifest_sha256,
                      "immutable_inputs_verified": len(sources),
                      "selected_runtime_targets_verified": len(outputs),
                      "created": created, "identical_reused": reused,
                      "include_optional": include_optional,
                      "runtime_cache_in_archive": False,
                      "network_DB_key_or_Gold_access": False,
                      "delete_or_replace_actions": 0}
        return result
    except HydrationError as exc:
        exc.created = created.copy()
        raise
    except Exception as exc:
        failure = HydrationError("FILESYSTEM_OR_INPUT_ACTION_REFUSED")
        failure.created = created.copy()
        raise failure from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path,
                        default=Path(__file__).absolute().parents[2])
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--include-optional", action="store_true")
    args = parser.parse_args()
    try:
        result = hydrate(args.project_root, verify_only=args.verify_only,
                         include_optional=args.include_optional)
    except HydrationError as exc:
        print(json.dumps({"status": "FAILED_RETAINED", "code": exc.code,
                          "approved_relative_target": exc.target,
                          "newly_created_targets_retained": exc.created,
                          "preexisting_files_overwritten_or_deleted": 0}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
