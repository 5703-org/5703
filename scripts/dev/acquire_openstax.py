"""Acquire the four scoped official PDFs without overwriting existing originals."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import httpx

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/openstax"
RAW = ROOT / "artifacts/openstax/originals"


def acquire(book):
    slug = book["slug"]
    manifest_path = EVIDENCE / f"{slug}-acquisition.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        path = ROOT / previous["raw_path"]
        if (
            path.is_file()
            and hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == previous["sha256"]
        ):
            print(f"{slug}: verified existing immutable download", flush=True)
            return previous
        raise RuntimeError(
            f"{slug}: existing acquisition record does not verify; refusing replacement"
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    partial = RAW / f"{slug}-{stamp}.pdf.part"
    hasher = hashlib.sha256()
    count = 0
    started = datetime.now(timezone.utc).isoformat()
    report_at = time.monotonic()
    with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(90, connect=30)) as client:
        with client.stream("GET", book["pdf_url"]) as response:
            response.raise_for_status()
            expected = int(response.headers.get("content-length", 0))
            with partial.open("xb") as target:
                for data in response.iter_bytes(1024 * 1024):
                    if count == 0 and not data.startswith(b"%PDF-"):
                        raise RuntimeError(f"{slug}: official response is not PDF bytes")
                    target.write(data)
                    hasher.update(data)
                    count += len(data)
                    if time.monotonic() - report_at > 20:
                        print(f"{slug}: received {count:,} / {expected:,} bytes", flush=True)
                        report_at = time.monotonic()
            if expected and count != expected:
                raise RuntimeError(f"{slug}: incomplete download {count}/{expected}")
            sha = hasher.hexdigest()
            final_path = RAW / f"{slug}-{sha}.pdf"
            if final_path.exists():
                raise RuntimeError(
                    f"{slug}: destination exists without acquisition record; inspect before reuse"
                )
            partial.rename(final_path)
            result = {
                **book,
                "acquisition_started_at": started,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
                "requested_url": book["pdf_url"],
                "final_url": str(response.url),
                "response_content_type": response.headers.get("content-type"),
                "response_etag": response.headers.get("etag"),
                "response_last_modified": response.headers.get("last-modified"),
                "size_bytes": count,
                "sha256": sha,
                "raw_path": final_path.relative_to(ROOT).as_posix(),
                "processing_scope": "Entire official PDF, every physical page accounted for",
                "license_evidence_status": "Official catalog recorded; embedded PDF license inspection pending",
            }
    manifest_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{slug}: acquired {count:,} bytes SHA256 {sha}", flush=True)
    return result


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((ROOT / "evidence/corpus/official_catalog.json").read_text())
    results, failures = [], []
    with ThreadPoolExecutor(max_workers=4) as executor:
        pending = {executor.submit(acquire, book): book["slug"] for book in catalog["books"]}
        for future in as_completed(pending):
            try:
                results.append(future.result())
            except Exception as exc:
                failure = {
                    "book": pending[future],
                    "error_type": type(exc).__name__,
                    "reason": str(exc),
                }
                failures.append(failure)
                print(json.dumps(failure), flush=True)
    (EVIDENCE / "acquisition-run.json").write_text(
        json.dumps(
            {
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "books": results,
                "failures": failures,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
