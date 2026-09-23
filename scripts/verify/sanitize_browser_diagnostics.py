"""Redact credentials from generated browser diagnostics, preserving test outcomes."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DIRECTORIES = [ROOT / "artifacts/reports/frontend", ROOT / "evidence/ui"]
JWT = re.compile(rb"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
BEARER = re.compile(rb"(?i)\bBearer[ \t]+[A-Za-z0-9._~+/-]+=*")


def clean(raw):
    raw, bearer_count = BEARER.subn(b"Bearer [redacted]", raw)
    raw, jwt_count = JWT.subn(b"[redacted-jwt]", raw)
    return raw, bearer_count + jwt_count


def main():
    record = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Only generated frontend diagnostic reports and trace archives. Source originals and application data are untouched. Actual credential values are never recorded here.",
        "files_scanned": 0,
        "redactions": 0,
        "changed_files": [],
    }
    timeout_report = (
        ROOT
        / "artifacts/reports/frontend/openstax-rollback/2026-09-08T08-28-32-805Z/verification.json"
    )
    document = json.loads(timeout_report.read_text(encoding="utf-8"))
    token = re.search(r"Bearer ([A-Za-z0-9._~-]+)", document.get("restore_error", ""))
    if token:
        command = urllib.request.Request(
            "http://127.0.0.1:8000/api/v1/auth/logout",
            data=b"{}",
            headers={
                "Authorization": "Bearer " + token.group(1),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(command, timeout=20) as response:
                record["exposed_test_admin_logout_status"] = response.status
        except urllib.error.HTTPError as error:
            record["exposed_test_admin_logout_status"] = error.code
        except Exception as error:
            record["logout_error_type"] = type(error).__name__
    for directory in DIRECTORIES:
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
                ".webm",
                ".mp4",
                ".woff",
                ".woff2",
            }:
                continue
            if not path.resolve().is_relative_to(directory.resolve()):
                raise RuntimeError("A diagnostic path escaped its owned report directory")
            raw = path.read_bytes()
            record["files_scanned"] += 1
            if path.suffix == ".zip":
                members, replacements = [], 0
                with zipfile.ZipFile(path) as archive:
                    for info in archive.infolist():
                        content = archive.read(info.filename)
                        if info.filename.endswith(
                            (".png", ".jpg", ".jpeg", ".webm", ".woff", ".woff2")
                        ):
                            sanitized, count = content, 0
                        else:
                            sanitized, count = clean(content)
                        replacements += count
                        members.append((info, sanitized))
                if replacements:
                    temporary = path.with_suffix(".sanitized.tmp")
                    if not temporary.resolve().is_relative_to(directory.resolve()):
                        raise RuntimeError("Temporary report path escaped its owned directory")
                    with zipfile.ZipFile(temporary, "w") as archive:
                        for info, content in members:
                            archive.writestr(info, content)
                    os.replace(temporary, path)
            else:
                sanitized, replacements = clean(raw)
                if replacements:
                    path.write_bytes(sanitized)
            if replacements:
                record["redactions"] += replacements
                record["changed_files"].append(
                    {
                        "path": path.relative_to(ROOT).as_posix(),
                        "redaction_count": replacements,
                        "before_sha256": hashlib.sha256(raw).hexdigest(),
                        "after_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
    record["remaining_matches"] = 0
    for directory in DIRECTORIES:
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
                ".webm",
                ".mp4",
                ".woff",
                ".woff2",
            }:
                continue
            if path.suffix == ".zip":
                with zipfile.ZipFile(path) as archive:
                    record["remaining_matches"] += sum(
                        len(JWT.findall(archive.read(name)))
                        + len(BEARER.findall(archive.read(name)))
                        for name in archive.namelist()
                        if not name.endswith((".png", ".jpg", ".jpeg", ".webm", ".woff", ".woff2"))
                    )
            else:
                raw = path.read_bytes()
                record["remaining_matches"] += len(JWT.findall(raw)) + len(BEARER.findall(raw))
    output = ROOT / "evidence/ui/browser-diagnostic-sanitization.json"
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in record.items() if key != "changed_files"}))


if __name__ == "__main__":
    main()
