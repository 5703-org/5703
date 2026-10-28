"""Replay recorded genuine retrieval through GenerationService with explicit mock answering."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.models import EvidenceSnapshot
from generation import GenerationRequest, GenerationService


def request_evidence(hits):
    """Retain exact source text/hash; discard retrieval-only metadata at the DTO boundary."""
    return [
        {
            **{key: value for key, value in hit.items() if key in EvidenceSnapshot.model_fields},
            "evidence_id": f"ev_{index:03d}",
            "context_order": index,
        }
        for index, hit in enumerate(hits, 1)
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = ROOT / "evidence/openstax/retrieval-before-fix.json"
    original = source.read_bytes()
    data = json.loads(original)
    records = []
    engine = GenerationService()
    cases = list(data["questions"])
    photosynthesis = next(
        item
        for item in cases
        if item["question"] == "How do plants use light energy in photosynthesis?"
    )
    cases.extend(
        {
            "category": "source_reuse_follow_up",
            "question": question,
            "history": [{"id": "prior-user", "role": "user", "content": "What is photosynthesis?"}],
            "hits": photosynthesis["hits"],
        }
        for question in ("Why does it need light?", "Make it simpler", "Give an example")
    )
    for index, case in enumerate(cases, 1):
        outcome = engine.generate(
            GenerationRequest(
                request_id=f"openstax-mock-replay-{index}",
                mode="interactive_chat",
                condition="E1",
                question=case["question"],
                evidence=request_evidence(case["hits"]),
                history=case.get("history", []),
            )
        )
        records.append(
            {
                "category": case["category"],
                "question": case["question"],
                "input_chunk_ids": [hit["chunk_id"] for hit in case["hits"]],
                "input_text_hashes": [hit["text_hash"] for hit in case["hits"]],
                "history": case.get("history", []),
                "outcome": outcome.to_dict(),
            }
        )
    result = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Actual GenerationService replay of pinned E5/pgvector candidates, using the deterministic mock answer adapter. Not a live answering-model or semantic-calibration result. Follow-up cases reuse the actual photosynthesis candidates without repeating retrieval.",
        "source_path": source.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(original).hexdigest(),
        "release_id": data["release_id"],
        "adapter_sha256": hashlib.sha256(
            (ROOT / "generation/adapters.py").read_bytes()
        ).hexdigest(),
        "query_preparer_sha256": hashlib.sha256(
            (ROOT / "conversation/query.py").read_bytes()
        ).hexdigest(),
        "records": records,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            [
                {
                    "question": record["question"],
                    "type": (record["outcome"]["response"] or {}).get("response_type"),
                    "error": record["outcome"]["error"],
                    "selected_count": len(record["outcome"]["evidence"]),
                }
                for record in records
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
