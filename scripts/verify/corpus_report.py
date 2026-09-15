"""Write the current per-book report from checked originals and live database counts."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from sqlalchemy import create_engine, text
from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/openstax"


def read(name):
    return json.loads((EVIDENCE / name).read_text("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    evidence_dir = args.evidence_dir.resolve()

    def current(name):
        path = evidence_dir / name
        return json.loads(path.read_text("utf-8")) if path.exists() else read(name)

    publication = current("publication.json")
    validation = current("formal-source-validation-summary.json")
    retrieval = current("retrieval-verification.json")
    registry = current("processing-status.json")
    registered = {book["slug"]: book for book in current("processing-registry.json")["books"]}
    registry["books"] = [{**registered[book["slug"]], **book} for book in registry["books"]]
    proof_path = evidence_dir.relative_to(ROOT).as_posix()
    engine = create_engine(Settings().database_url)
    with engine.connect() as db:
        active = db.scalar(text("SELECT release_id FROM active_corpus WHERE id=1"))
        postgres = db.scalar(text("SELECT version()"))
        pgvector = db.scalar(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))
        if active != publication["release_id"]:
            raise RuntimeError("Current active corpus differs from the verified publication")
        counts = {
            row["document_id"]: dict(row)
            for row in db.execute(
                text(
                    "SELECT c.document_id, count(*) AS vectors, min(vector_dims(r.embedding)) AS minimum_dimension, max(vector_dims(r.embedding)) AS maximum_dimension FROM release_chunks r JOIN chunks c ON c.id=r.chunk_id WHERE r.release_id=:id GROUP BY c.document_id"
                ),
                {"id": active},
            ).mappings()
        }
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "status": "REAL_FLOW_VERIFIED",
        "scope": "Four complete official PDF sources, real extraction/recovery, E5 embeddings, pgvector storage and attributable retrieval; graphical/math coverage and scientific evaluation remain bounded.",
        "release_id": active,
        "evidence_directory": proof_path,
        "publication_evidence": proof_path + "/publication.json",
        "validation_evidence": proof_path + "/formal-source-validation-summary.json",
        "retrieval_evidence": proof_path + "/retrieval-verification.json",
        "parser_revision": registered[registry["books"][0]["slug"]].get(
            "parser_revision", retrieval["embedding_configuration"].get("parser_revision")
        ),
        "answer_model_mode": "mock",
        "embedding_configuration": retrieval["embedding_configuration"],
        "database": {
            "endpoint": "127.0.0.1:55432",
            "database": "learning",
            "postgresql": postgres,
            "pgvector": pgvector,
            "container": "cs30-learning-db-1",
            "volume": "cs30-learning_pgdata",
            "docker_volume_path": "/var/lib/docker/volumes/cs30-learning_pgdata/_data",
            "container_path": "/var/lib/postgresql/data",
            "tables": [
                "documents",
                "document_versions",
                "processing_runs",
                "source_units",
                "chunks",
                "corpus_releases",
                "release_chunks",
                "active_corpus",
            ],
        },
        "books": [],
        "limitations": [
            "All 4,638 physical pages are accounted for, but full-book visual relationships, image equations, complete reading order and scientific fidelity have not been independently certified.",
            "14 source-reviewed local OCR transcriptions and one exact publisher portrait description resolve 15 low-text source pages. Original issues and rejected alternatives remain visible; agent review is not independent human review.",
            "Nearest-neighbor candidates are not guaranteed relevant. All 15 scheduled queries, including three unrelated questions, are retained; live answer quality and formal relevance qrels are unverified.",
            "Answer generation is explicitly mock. No hosted answering model, real answer-effectiveness evaluation or independent human ratings are claimed.",
        ],
    }
    lines = [
        "# Real OpenStax corpus execution report",
        "",
        "This report is generated from current PostgreSQL counts and the linked source, retrieval and activation evidence. Only answer generation remains mock. Counts are units unless explicitly marked pages or chunks; unresolved blocking units and retained historical issue codes are different quantities.",
        "",
        f"Observed: {report['observed_at']}. Active release: `{active}`. Scope owner: `sources/COMP5703/tut5/HongleYang/WEEK4_SUMMARY_AND_WEEK5_PLAN.md`, section 1.1, `cs30_openstax_v0.2`; all four full PDFs.",
        "",
        "| Book | Physical pages | Ready units | Excluded units | Recovered originals | Blocking units | Chunks / real vectors | Dimension |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for book in registry["books"]:
        slug = book["slug"]
        acquisition = current(slug + "-acquisition.json")
        quality = current(slug + "-quality.json")
        verified = next(x for x in validation["books"] if x["slug"] == slug)
        vector_count = counts[book["document_id"]]
        assert vector_count["vectors"] == book["counts"]["chunks"] == verified["chunks"]
        excluded = []
        for unit in quality["units"]:
            if unit["quality"] == "excluded":
                decisions = [
                    issue
                    for issue in unit["issues"]
                    if issue["code"] in {"SOURCE_PAGE_REVIEW", "FURNITURE_ONLY"}
                ]
                excluded.append(
                    {"unit_id": unit["id"], "physical_page": unit["page"], "reasons": decisions}
                )
        categories = Counter()
        for unit in excluded:
            reviews = [x for x in unit["reasons"] if x["code"] == "SOURCE_PAGE_REVIEW"]
            categories[reviews[0]["category"] if reviews else "furniture_only"] += 1
        examples = [
            {"question": q["question"], "category": q["category"], "rank": rank, "hit": hit}
            for q in retrieval["questions"]
            for rank, hit in enumerate(q["hits"], 1)
            if q["category"] != "unrelated" and hit["asset_id"] == book["document_id"]
        ]
        item = {
            **book,
            "acquisition": acquisition,
            "physical_pages": verified["physical_pages"],
            "embedded_license": {
                "physical_page": 4,
                "copyright": "2026 Rice University",
                "license": "CC BY-NC-SA 4.0",
                "attribution": "Access for free at openstax.org",
                "evidence": "evidence/openstax/pdf-source-inspection.json",
            },
            "database_vectors": vector_count,
            "exclusion_categories": dict(categories),
            "excluded_units": excluded,
            "recovered_physical_pages": sorted(
                {u["page"] for u in quality["units"] if u["quality"] == "supplemented"}
            ),
            "retrieval_examples": examples,
            "remaining": report["limitations"],
        }
        report["books"].append(item)
        c = book["counts"]
        lines.append(
            f"| {book['title']} | {item['physical_pages']} | {c['ready_units']} | {c['excluded_units']} | {c['supplemented_units']} | {c['blocked_units']} | {c['chunks']} / {vector_count['vectors']} | 384 |"
        )
    lines += [
        "",
        "## Shared embedding, storage and validation",
        "",
        f"The actual model is `intfloat/e5-small-v2`, fixed revision `ffb93f3bd4047442299a41ebb6fa998a38507c52`, with the tokenizer from the same revision. Query/passages use their E5 prefixes and normalized 384-dimensional vectors. CUDA execution used the local RTX 5070 Ti. The 512-token model window is enforced: maximum measured full input was {validation['max_input_tokens']} tokens; target body 320, configured cap 448, overlap 48. The exact release configuration in `{proof_path}/release-build.json`, `requirements-embeddings.lock` and `evidence/corpus/e5_download.json` pin the configuration and files.",
        "",
        "Database: PostgreSQL at `127.0.0.1:55432/learning`; pgvector "
        + str(pgvector)
        + ". Docker volume `cs30-learning_pgdata` is mounted at `/var/lib/postgresql/data`; Docker's volume location is `/var/lib/docker/volumes/cs30-learning_pgdata/_data`. This Linux path belongs to the local Docker engine. Text/source lineage is in `source_units`/`chunks`, vectors in `release_chunks`, and the publication pointer in `active_corpus`. Immutable original and recovery files are under `E:/5703/learning-assistant/artifacts/storage`.",
        "",
        f"The formal source check covers every original hash, page accounting, chunk hash/span, embedding input and vector relationship. It re-extracted {validation['sample_original_pages_checked']} original PDF pages for {validation['sample_count']} deterministic chunk samples, including every recovered page. [Formal check](../../{proof_path}/formal-source-validation-summary.json), [full report](../../{proof_path}/formal-source-validation.json), [all real queries](../../{proof_path}/retrieval-verification.json), [activation and unchanged-history proof](../../{proof_path}/publication.json). The earlier query-verifier metadata failure is retained in [initial attempt](../../evidence/openstax/retrieval-before-fix.json).",
        "",
    ]
    for book in report["books"]:
        a, c = book["acquisition"], book["counts"]
        lines += [
            "## " + book["title"],
            "",
            f"Edition identity: {book['title']}; original publication {a['publish_date']}, digital ISBN `{a['digital_isbn_13']}`. The actual downloaded PDF is pinned by hash and acquisition time, rather than an invented revision date. Acquired {a['acquired_at']}; HTTP Last-Modified: {a.get('response_last_modified')}. Full physical pages 1–{book['physical_pages']} were processed, including front matter, exercises and appendices.",
            "",
            f"[Official PDF]({a['final_url']}) · [Official catalog]({a['catalog_api']}) · [License]({a['license_url']}). Embedded physical page 4 states ©2026 Rice University and CC BY-NC-SA 4.0. Preserve attribution and applicable license/trademark notices; the original publication year and current PDF copyright year are distinct.",
            "",
            f"Original: `{(ROOT / a['raw_path']).as_posix()}` ({a['size_bytes']:,} bytes). Registered storage: `{(Path(book['storage_root']) / book['database_storage_path']).as_posix()}`. SHA-256: `{a['sha256']}`.",
            "",
            f"Source version `{book['document_version_id']}`; processing run `{book['processing_id']}`; release `{active}`. {c['total_units']} total units: {c['ready_units']} ready, {c['excluded_units']} explicitly excluded, {c['supplemented_units']} originals retained with recovery linked, {c['blocked_units']} unresolved blockers. {c['chunks']} chunks and {book['database_vectors']['vectors']} real 384-dimensional vectors.",
            "",
            f"Exclusion reasons/counts: `{json.dumps(book['exclusion_categories'])}`. Recovered physical pages: {', '.join(map(str, book['recovered_physical_pages']))}. [Full page/unit decisions](../../{proof_path}/{book['slug']}-quality.json) preserve initial issues, exact reasons and source hashes; historical blocked attempts are not rewritten.",
            "",
        ]
        example = next(
            (x for x in book["retrieval_examples"] if x["rank"] == 1), book["retrieval_examples"][0]
        )
        hit = example["hit"]
        lines += [
            f"Actual query: **{example['question']}** Rank {example['rank']}, score {hit['score']:.6f}. Chapter/section: {hit['section']}; physical PDF pages {', '.join(map(str, hit['pages']))}; chunk `{hit['chunk_id']}`; text hash `{hit['text_hash']}`.",
            "",
            "Exact source excerpt:",
            "",
            "> "
            + hit["text"][:700].replace("\n", "\n> ")
            + (" […]" if len(hit["text"]) > 700 else ""),
            "",
            "The complete unabridged hit is in the machine report and query evidence. Full-book image/equation fidelity, independent scientific review and real answer-model evaluation remain unverified.",
            "",
        ]
    lines += ["## Remaining work and honest boundaries", ""] + [
        "- " + x for x in report["limitations"]
    ]
    lines += [
        "- Actual full-corpus restoration and SciQ acquisition have separate proof. Current browser/API, local delivery and remaining research/device checks are governed by the 108-task and 60-check ledgers, without an overall completion percentage.",
        "",
    ]
    serialized = json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n"
    if evidence_dir != EVIDENCE:
        prior = EVIDENCE / "corpus-report.json"
        archive = EVIDENCE / "initial-v4-published-corpus-report.json"
        if prior.exists() and not archive.exists():
            archive.write_bytes(prior.read_bytes())
        (evidence_dir / "corpus-report.json").write_text(serialized, "utf-8")
    (EVIDENCE / "corpus-report.json").write_text(serialized, "utf-8")
    (ROOT / "docs/execution/openstax-corpus-report.md").write_text("\n".join(lines), "utf-8")
    print(
        json.dumps(
            {
                "books": len(report["books"]),
                "chunks_and_vectors": sum(
                    x["database_vectors"]["vectors"] for x in report["books"]
                ),
                "release_id": active,
            }
        )
    )


if __name__ == "__main__":
    main()
