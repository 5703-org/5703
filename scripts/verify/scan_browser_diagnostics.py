"""Read-only credential scan of generated frontend diagnostics and trace members."""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[2]
DIRECTORIES = [ROOT / "artifacts/reports/frontend", ROOT / "evidence/ui"]
PATTERNS = [
    re.compile(rb"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(rb"(?i)\bBearer[ \t]+[A-Za-z0-9._~+/-]+=*"),
]
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".webm", ".mp4", ".woff", ".woff2"}


def main():
    record = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Read-only scan of generated frontend report files and decompressed trace members; no credential values recorded.",
        "prior_sanitization_record": "evidence/ui/browser-diagnostic-sanitization.json",
        "files_scanned": 0,
        "archive_members_scanned": 0,
        "remaining_matches": 0,
        "matching_paths": [],
    }
    for directory in DIRECTORIES:
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.suffix.lower() in MEDIA_SUFFIXES:
                continue
            if not path.resolve().is_relative_to(directory.resolve()):
                raise RuntimeError("Report path escaped its owned directory")
            record["files_scanned"] += 1
            if path.suffix == ".zip":
                with zipfile.ZipFile(path) as archive:
                    contents = [
                        archive.read(name)
                        for name in archive.namelist()
                        if Path(name).suffix.lower() not in MEDIA_SUFFIXES
                    ]
                record["archive_members_scanned"] += len(contents)
            else:
                contents = [path.read_bytes()]
            count = sum(len(pattern.findall(raw)) for raw in contents for pattern in PATTERNS)
            record["remaining_matches"] += count
            if count:
                record["matching_paths"].append(
                    {"path": path.relative_to(ROOT).as_posix(), "count": count}
                )
    record["passed"] = record["remaining_matches"] == 0
    output = ROOT / "evidence/ui/browser-diagnostic-final-scan.json"
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record))
    if not record["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
