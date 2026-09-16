"""Verify full fixed/structure source coverage and real-vector identity without activation."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.db.session import init_engine
from app.modules.answering.models import Job
from app.modules.knowledge.models import ActiveCorpus, CorpusRelease, SourceUnit
from app.modules.knowledge.service import _release_rows, digest


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vector_hash(values):
    return hashlib.sha256(struct.pack(f"<{len(values)}f", *values)).hexdigest()


def source_coverage(units, chunks):
    intervals = defaultdict(list)
    for chunk in chunks:
        for span in chunk.spans:
            intervals[span["unit_id"]].append((span["start"], span["end"]))
    output = {}
    for unit in units:
        covered = bytearray(len(unit.cleaned_text))
        merged = []
        for start, end in sorted(intervals[unit.id]):
            covered[start:end] = b"\1" * (end - start)
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        required = [i for i, ch in enumerate(unit.cleaned_text) if not ch.isspace()]
        missing = [i for i in required if not covered[i]] if unit.quality == "ready" else []
        if missing or (unit.quality != "ready" and any(covered)):
            raise ValueError(f"Incorrect source coverage at {unit.processing_id}:{unit.sequence}")
        output[(unit.page, unit.sequence)] = {
            "unit_id": unit.id,
            "quality": unit.quality,
            "raw_hash": hashlib.sha256(unit.raw_text.encode()).hexdigest(),
            "cleaned_hash": hashlib.sha256(unit.cleaned_text.encode()).hexdigest(),
            "section": unit.section,
            "issues_hash": digest(unit.issues),
            "source_characters": len(unit.cleaned_text),
            "nonwhitespace_characters": len(required),
            "covered_nonwhitespace": sum(bool(covered[i]) for i in required),
            "merged_coverage_intervals": merged,
        }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=Path("evidence/chunking/fixed-v5"))
    args = parser.parse_args()
    root = args.evidence_dir
    destination = root / "comparison-summary.json"
    if destination.exists():
        raise RuntimeError("Preserve previous comparison evidence")
    registry_path, formal_path = (
        root / "processing-registry.json",
        root / "formal-source-validation.json",
    )
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    plan = json.loads((root / "processing-plan.json").read_text(encoding="utf-8"))
    build = json.loads((root / "release-build.json").read_text(encoding="utf-8"))
    formal = json.loads(formal_path.read_text(encoding="utf-8"))
    if formal["status"] != "passed" or formal["registry_sha256"] != file_sha(registry_path):
        raise RuntimeError(
            "The exact fixed registry requires its complete real-tokenizer validation"
        )
    engine = init_engine(Settings().database_url)
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Actual PostgreSQL is required")
    output = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "read_only": True,
        "baseline_release_id": registry["baseline_release_id"],
        "fixed_release_id": build["release_id"],
        "controlled_factor": "chunking strategy only",
        "plan_hash": registry["plan_hash"],
        "formal_validation": {
            "path": formal_path.as_posix(),
            "sha256": file_sha(formal_path),
            "status": formal["status"],
            "sample_count": len(formal["sample"]),
        },
        "books": [],
        "quality_metrics": None,
        "human_qrels": None,
        "interpretation": "Source coverage, boundaries and actual vector integrity are technical observations. Changed chunks require a versioned source-span review; no relevance grade transfers automatically.",
    }
    try:
        with Session(engine) as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            baseline = db.get(CorpusRelease, registry["baseline_release_id"])
            fixed = db.get(CorpusRelease, build["release_id"])
            job = db.get(Job, build["job_id"])
            if db.get(ActiveCorpus, 1).release_id != baseline.id or baseline.state != "active":
                raise ValueError("The approved active baseline pointer changed")
            if fixed.state != "validated" or job.state != "succeeded":
                raise ValueError("The separate fixed release must be validated and unactivated")
            if (
                baseline.configuration != plan["baseline_configuration"]
                or baseline.manifest != plan["baseline_manifest"]
            ):
                raise ValueError("Historical baseline manifest or configuration changed")
            if fixed.configuration != {**baseline.configuration, "strategy": "fixed"}:
                raise ValueError("More than the declared chunking factor changed")
            before_rows, after_rows = _release_rows(db, baseline), _release_rows(db, fixed)
            output["release_counts"] = {"structure": len(before_rows), "fixed": len(after_rows)}
            output["baseline_manifest_hash"] = digest(baseline.manifest)
            output["fixed_manifest"] = fixed.manifest
            output["active_pointer_unchanged"] = True
            output["comparison_unactivated"] = True
            before_vectors = defaultdict(set)
            for vector, chunk, _ in before_rows:
                before_vectors[(chunk.section, chunk.text_hash)].add(vector_hash(vector.embedding))
            exact_reuse, novel = 0, 0
            for vector, chunk, _ in after_rows:
                possible = before_vectors.get((chunk.section, chunk.text_hash))
                if possible:
                    if vector_hash(vector.embedding) not in possible:
                        raise ValueError(
                            "A shared exact model input changed its stored float32 vector"
                        )
                    exact_reuse += 1
                else:
                    novel += 1
            output["fixed_vectors_matching_exact_baseline_inputs"] = exact_reuse
            output["fixed_vectors_with_different_input_boundaries"] = novel
            for book in registry["books"]:
                prior_id, new_id = book["prior_processing_id"], book["processing_id"]
                unit_sets = {
                    run: list(
                        db.scalars(
                            select(SourceUnit)
                            .where(SourceUnit.processing_id == run)
                            .order_by(SourceUnit.sequence)
                        )
                    )
                    for run in (prior_id, new_id)
                }
                chunk_sets = {
                    prior_id: [
                        chunk for _, chunk, _ in before_rows if chunk.processing_id == prior_id
                    ],
                    new_id: [chunk for _, chunk, _ in after_rows if chunk.processing_id == new_id],
                }
                before = source_coverage(unit_sets[prior_id], chunk_sets[prior_id])
                after = source_coverage(unit_sets[new_id], chunk_sets[new_id])
                if set(before) != set(after):
                    raise ValueError("Source-unit page/sequence identities changed")
                rows = []
                fields = (
                    "quality",
                    "raw_hash",
                    "cleaned_hash",
                    "section",
                    "issues_hash",
                    "nonwhitespace_characters",
                    "covered_nonwhitespace",
                )
                for page, sequence in sorted(before):
                    old, new = before[(page, sequence)], after[(page, sequence)]
                    if any(old[k] != new[k] for k in fields):
                        raise ValueError(
                            f"Original source or usable text coverage changed: {book['slug']}:{sequence}"
                        )
                    rows.append(
                        {
                            "physical_page": page,
                            "sequence": sequence,
                            "structure": old,
                            "fixed": new,
                        }
                    )
                coverage_path = root / f"{book['slug']}-coverage.json"
                coverage_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
                diff_path = root / f"{book['slug']}-diff.json"
                diff = json.loads(diff_path.read_text(encoding="utf-8"))
                if (
                    diff["configuration_changes"]
                    != {"strategy": {"before": "structure", "after": "fixed"}}
                    or not diff["raw_asset_reused"]
                ):
                    raise ValueError("Source or configuration changed beyond the intended factor")
                if any(diff["counts"]["source_units"][k] for k in ("changed", "added", "removed")):
                    raise ValueError("A source unit changed during the chunking comparison")
                output["books"].append(
                    {
                        "slug": book["slug"],
                        "pdf_sha256": book["sha256"],
                        "source_units": len(rows),
                        "physical_pages": len({p for p, _ in before}),
                        "structure_processing_id": prior_id,
                        "fixed_processing_id": new_id,
                        "structure_chunks": len(chunk_sets[prior_id]),
                        "fixed_chunks": len(chunk_sets[new_id]),
                        "all_usable_nonwhitespace_source_characters_covered": True,
                        "raw_cleaned_section_quality_issue_hashes_unchanged": True,
                        "diff_counts": diff["counts"],
                        "coverage_path": coverage_path.as_posix(),
                        "coverage_sha256": file_sha(coverage_path),
                        "diff_path": diff_path.as_posix(),
                        "diff_sha256": file_sha(diff_path),
                    }
                )
            output["status"] = "passed"
    except Exception as exc:
        output.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": output["status"],
                "release_counts": output.get("release_counts"),
                "books": len(output["books"]),
                "error": output.get("error"),
            }
        )
    )
    return 0 if output["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
