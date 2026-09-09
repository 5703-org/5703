"""Reconcile current source/release evidence without changing original requirements."""

from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime.now(timezone.utc).isoformat()
PROOF = [
    "docs/execution/openstax-corpus-report.md",
    "evidence/openstax/formal-source-validation-summary.json",
    "evidence/openstax/retrieval-verification.json",
    "evidence/openstax/publication.json",
]
CURRENT = (
    "All four official complete PDFs (4,638 pages) were acquired, hash/license checked, "
    "parsed and reviewed. 5,541 source units retain 73 documented exclusions and 15 "
    "supplemented originals; no blocking units remain. 10,584 actual E5 vectors of "
    "384 dimensions are published in PostgreSQL/pgvector release "
    "39483e7f-efbe-42e7-855e-469fd924383e. All 15 real queries and the reversible "
    "unavailable-source filter check passed; original/answer/evidence records are unchanged."
)
LIMIT = (
    "Full-book visual/equation semantics and independent scientific review remain unverified. "
    "Only answer generation remains mock; formal answer/relevance/human research is not established."
)


def main():
    publication = json.loads((ROOT / PROOF[-1]).read_text("utf-8"))
    assert publication["status"] == "passed" and publication["history_preserved"]
    checkpoint = {
        "observed_at": NOW, "official_pdf_count": 4, "physical_pages": 4638,
        "official_downloads_verified": True, "pinned_e5_inference_verified": True,
        "all_books_native_parsed": True, "full_book_vectors_verified": True,
        "official_release_published": True, "release_id": publication["release_id"],
        "real_vector_count": 10584, "dimension": 384,
        "actual_retrieval_questions": 15, "remaining": LIMIT,
    }
    task_ids = {"DAT-01", "DAT-03", "DAT-04", "DAT-05", "DAT-06", "DAT-07", "DAT-08", "RET-01", "RET-02", "RET-03", "RET-06"}
    check_ids = {"AC-04", "AC-05", "AC-06", "AC-14", "AC-28"}
    for filename, key, selected in (("tasks.json", "tasks", task_ids), ("acceptance.json", "checks", check_ids)):
        path = ROOT / "docs/execution" / filename
        ledger = json.loads(path.read_text("utf-8"))
        old = ledger.get("corpus_checkpoint")
        if old != checkpoint and old:
            ledger.setdefault("checkpoint_history", []).append(old)
        ledger["corpus_checkpoint"] = checkpoint
        ledger["reconciliation_phase"] = "official_corpus_published_remaining_project_continues"
        ledger["project_complete"] = False
        ledger["reconciled_at"] = NOW
        for item in ledger[key]:
            identity = item.get("task_id", item.get("check_id"))
            if identity in selected:
                item.setdefault("verification_history", []).append({
                    "observed_at": item.get("reconciled_at"), "status": item["status"],
                    "component_statuses": item.get("component_statuses", []),
                    "remaining_scope": item.get("remaining_scope"),
                })
                item["status"] = "REAL_FLOW_VERIFIED"
                if key == "tasks":
                    item["implementation_status"] = "REAL_FLOW_VERIFIED"
                    item["verification_status"] = "REAL_FLOW_VERIFIED"
                item["component_statuses"] = [{
                    "component": "current official corpus execution", "status": "REAL_FLOW_VERIFIED",
                    "detail": CURRENT, "observed_at": NOW, "evidence_paths": PROOF,
                }, {"component": "remaining semantic/human scope", "status": "IMPLEMENTED_UNVERIFIED", "detail": LIMIT}]
                item["remaining_scope"] = LIMIT
                item["reconciliation_note"] = CURRENT + " " + LIMIT
                if item.get("implementation_trace"):
                    item["implementation_trace"]["limitation"] = LIMIT
                item["evidence_paths"] = list(dict.fromkeys(item.get("evidence_paths", []) + PROOF))
                item["reconciled_at"] = NOW
                item["completion_claim"] = False
        path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", "utf-8")

    prd = ROOT / "PRD.md"
    value = prd.read_text("utf-8")
    replacements = {
        "Official PDF acquired and hash-verified; initial full parsing quarantined two empty pages; chunking, vectors and publication pending": "Full official PDF processed; all blockers resolved with retained source evidence; real E5/pgvector release active (see per-book report)",
        "Official PDF acquired and hash-verified; initial full parsing running; vectors and publication pending": "Full official PDF processed; 2,370 chunks/real vectors in the active release; seven source pages recovered",
        "Official PDF acquired with exact historical pilot SHA256; current full processing queued": "Exact historical pilot SHA256; pilot cover/blank inspected; 1,404 chunks/real vectors active; two appendix pages recovered",
        "The pinned E5 checkpoint has executed genuine offline CUDA inference on this computer ([model verification](evidence/corpus/e5_verification.json)); that model smoke test does not mean the full corpus vectors have been built.": "The pinned E5 checkpoint has generated all 10,584 real vectors. The [per-book report](docs/execution/openstax-corpus-report.md) records current source counts, original PDF locations, actual questions and the activated release; [publication evidence](evidence/openstax/publication.json) proves historical records stayed unchanged.",
        "They do not establish a real OpenStax release, learned embedding execution, model correctness, formal SciQ scores, independent ratings or physical mobile keyboard behavior.": "Separately, the four-book OpenStax/E5/pgvector release and 15 actual retrieval queries have now passed the linked current source and publication checks. Neither set of evidence establishes live answer correctness, formal SciQ scores, independent ratings or physical mobile keyboard behavior.",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = value.replace("1. Reconcile this PRD", "1. Completed first pass: reconcile this PRD").replace("2. Download the four official books", "2. Completed with explicit visual/semantic limits: download the four official books").replace("3. Update per-book", "3. Current publication evidence: update per-book")
    prd.write_text(value, "utf-8")

    spec = ROOT / "SPEC.md"
    value = spec.read_text("utf-8")
    pairs = {
        "Authored PDF and negative tests; four real books not yet processed in this implementation": "All four official full PDFs processed; 4,638 pages accounted, 73 reviewed exclusions and 15 recovered originals; source semantics remain bounded",
        "Span/hash tests; full-book output not yet verified": "All 10,584 full-corpus chunks pass source/span/hash/token checks; 50 deterministic samples checked against 67 original pages",
        "Real model adapter exists; checkpoint/inference execution not yet verified": "Actual fixed-revision E5 CUDA execution generated 10,584 normalized 384-dimensional vectors",
        "Actual pgvector SQL/known-vector checks; learned-vector book retrieval not yet verified": "Real E5/pgvector retrieval: all 15 scheduled queries and source-unavailability filtering verified; no formal relevance score claimed",
        "The default answer provider remains mock while the formal corpus is upgraded to real OpenStax data and real local embeddings.": "The answer provider remains explicitly mock while the active formal corpus uses real OpenStax data and real local E5 embeddings.",
        "full-book vector construction remains a separate pending step.": "all 10,584 full-book vectors have now been built, validated and activated with source checks in `evidence/openstax/publication.json`.",
    }
    for old, new in pairs.items():
        value = value.replace(old, new)
    at = value.index("## Current verification and gaps")
    value = value[:at] + "## Current verification and gaps\n\n" + CURRENT + " " + LIMIT + "\n\n" + (
        "The [per-book report](docs/execution/openstax-corpus-report.md) and its machine-readable source enumerate editions, licenses, hashes, paths, recovery reasons, exact counts and source excerpts. Parser `pypdf_bookmarks_v4` follows actual PDF outline destinations. Fourteen agent-reviewed real OCR transcripts and one exact official portrait description supplement native text; all original issues and failed candidates remain preserved. Footers/blank/cover decisions are tied to exact PDF/page/native-text hashes. No complete diagram or equation understanding is claimed.\n\n"
        "Actual full-corpus backup-v2 restored to the distinct `cs30_restore_openstax_20260908` database and independent storage. Seven originals, 44 supplementary source artifacts, complete user/profile values, all corpus/vector values, active pointer and historical answer/evidence fingerprints match the exported database snapshot. Evidence: `evidence/recovery/backup-real-openstax-20260908/restore-cs30_restore_openstax_20260908.json`.\n\n"
        "Earlier mock/authored software, browser and clean Compose checks remain separately scoped. Continue current official-corpus browser/API journeys, remaining compatibility/static/CI/packaging, actual SciQ acquisition and controlled retrieval studies. Hosted answering, formal semantic metrics, independent qrels/ratings and physical-device acceptance are not implied by corpus publication.\n"
    )
    spec.write_text(value, "utf-8")
    print("Updated canonical 108/60 ledgers and substantive PRD/SPEC from current publication proof.")


if __name__ == "__main__":
    main()
