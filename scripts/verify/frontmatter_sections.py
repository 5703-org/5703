"""Read-only audit of synthetic page labels carried into frontmatter sections."""

from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from pypdf import PdfReader
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.db.session import init_engine
from app.modules.identity.models import User
from app.modules.knowledge.models import ActiveCorpus, Chunk, ReleaseChunk, SourceUnit
from pipelines.pdf_structure import outline_destinations, split_bookmarked_page


def main():
    output = Path("evidence/openstax/frontmatter-section-audit.json")
    if output.exists():
        raise RuntimeError("Preserve the first audit artifact")
    registry = json.loads(
        Path("evidence/openstax/processing-registry.json").read_text(encoding="utf-8")
    )
    baseline = "39483e7f-efbe-42e7-855e-469fd924383e"
    books = []
    with Session(init_engine(Settings().database_url)) as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        active = db.get(ActiveCorpus, 1)
        active_id = active.release_id if active else None
        for book in registry["books"]:
            units = list(
                db.scalars(
                    select(SourceUnit)
                    .where(
                        SourceUnit.processing_id == book["processing_id"],
                        SourceUnit.section.like("PDF physical page %"),
                    )
                    .order_by(SourceUnit.sequence)
                )
            )
            chunks = list(
                db.scalars(
                    select(Chunk)
                    .join(ReleaseChunk, ReleaseChunk.chunk_id == Chunk.id)
                    .where(
                        ReleaseChunk.release_id == baseline,
                        Chunk.processing_id == book["processing_id"],
                        Chunk.section.like("PDF physical page %"),
                    )
                    .order_by(Chunk.id)
                )
            )
            reader = PdfReader(Path(book["raw_path"]), strict=True)
            destinations = outline_destinations(reader)
            page_numbers = sorted({u.page for u in units} | {p for c in chunks for p in c.pages})
            # Reproduce only the observed prefix, using the unmodified splitter and actual PDF text.
            carry = None
            reproduction = []
            for page in range(1, max(page_numbers, default=0) + 1):
                raw = reader.pages[page - 1].extract_text() or ""
                segments, carry = split_bookmarked_page(
                    raw, page, destinations, carry, legacy_synthetic_carry=True
                )
                reproduction.append(
                    {
                        "physical_page": page,
                        "actual_bookmark_destinations": destinations.get(page, []),
                        "produced_sections": sorted({segment[0] for segment in segments}),
                        "returned_carry": carry,
                    }
                )
            books.append(
                {
                    "slug": book["slug"],
                    "title": book["title"],
                    "processing_id": book["processing_id"],
                    "registered_original_sha256": book["sha256"],
                    "first_actual_outline_destinations": {
                        str(p): destinations[p] for p in sorted(destinations)[:2]
                    },
                    "synthetic_named_unit_count": len(units),
                    "synthetic_named_unit_pages": sorted({u.page for u in units}),
                    "units": [
                        {
                            "unit_id": u.id,
                            "page": u.page,
                            "section": u.section,
                            "quality": u.quality,
                        }
                        for u in units
                    ],
                    "affected_released_chunk_count": len(chunks),
                    "affected_released_pages": sorted({p for c in chunks for p in c.pages}),
                    "chunks": [
                        {
                            "chunk_id": c.id,
                            "section": c.section,
                            "physical_pages": c.pages,
                            "text_hash": c.text_hash,
                            "spans": c.spans,
                            "preview": c.text[:160],
                        }
                        for c in chunks
                    ],
                    "actual_pdf_prefix_reproduction": reproduction,
                }
            )
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "baseline_release_id": baseline,
        "observed_active_release_id": active_id,
        "affected_released_chunk_count": sum(b["affected_released_chunk_count"] for b in books),
        "cause": {
            "module": "pipelines/pdf_structure.py",
            "function": "split_bookmarked_page",
            "source_sha256": hashlib.sha256(
                Path("pipelines/pdf_structure.py").read_bytes()
            ).hexdigest(),
            "function_source": inspect.getsource(split_bookmarked_page),
            "finding": "A synthetic physical-page fallback is returned as carried section state. On following pages without actual bookmark events, that same fallback survives. This label is generated by code, not copied from a PDF bookmark title.",
        },
        "scope": {
            "incorrect": "Section labels for the listed released frontmatter chunks imply physical page1 even when the independent chunk page list is pages3–6.",
            "preserved": "Original PDF bytes, actual chunk physical-page arrays, source text/hash and source-unit spans are unchanged. No active/historical DB rows or parser files were modified by this audit.",
            "not_claimed": "This is an exhaustive search for this synthetic-prefix defect in the four selected processing runs, not an independent re-review of every book section locator.",
        },
        "books": books,
    }
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "affected_chunks": result["affected_released_chunk_count"],
                "books": [
                    {
                        k: b[k]
                        for k in (
                            "slug",
                            "affected_released_chunk_count",
                            "affected_released_pages",
                        )
                    }
                    for b in books
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
