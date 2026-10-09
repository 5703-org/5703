"""Recover exact development fit inputs from a replay, verifying their frozen hash."""

import argparse
import json
from pathlib import Path

from retrieval.adaptive import fingerprint
from retrieval.cpu_backend import file_hash, torch_threads
from scripts.verify.cpu_backend_replay import corpus, dump


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    args = parser.parse_args()
    target = args.replay / "development-fit-input.reconstructed.json"
    if target.exists():
        raise ValueError("Preserve the existing reconstruction")
    import numpy as np
    from retrieval.embedding import make_embedding
    from retrieval.lexical import LexicalIndex
    from retrieval.ranking import rrf

    frozen = json.loads((args.replay / "frozen-input.json").read_text(encoding="utf-8"))
    policy = json.loads((args.replay / "frozen-adaptive-policy.json").read_text(encoding="utf-8"))
    rows, vectors, identity = corpus(args.bundle)
    if identity != frozen["corpus"]:
        raise ValueError("Corpus identity changed")
    matrix = np.asarray(vectors, dtype=np.float64)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    index = LexicalIndex(rows)
    with torch_threads(2):
        embedder = make_embedding(identity["configuration"], runtime_device="cpu")
    development = []
    for case in frozen["cases"]:
        if case["split"] != "development":
            continue
        original = json.loads((args.replay / f"{case['id']}.json").read_text(encoding="utf-8"))
        with torch_threads(2):
            encoded = np.asarray(
                embedder.encode([case["query"]], kind="query")[0], dtype=np.float64
            )
        scores = matrix @ (encoded / np.linalg.norm(encoded))
        selected = sorted(range(len(rows)), key=lambda i: (-scores[i], rows[i]["chunk_id"]))[:50]
        dense = [{**rows[i], "score": float(scores[i]), "score_type": "cosine"} for i in selected]
        candidates = rrf([dense, index.search(case["query"], 50)], k=20)
        if [x["chunk_id"] for x in candidates] != original["candidate_ids"]:
            raise ValueError("Recomputed candidate membership/order changed")
        development.append(
            dict(
                case,
                candidates=candidates,
                reference_ids=original["backends"]["torch_2"]["ordered_ids"][:5],
            )
        )
    actual = fingerprint(development)
    if actual != policy["development_sha256"]:
        raise ValueError("Reconstructed input does not match the original frozen fit hash")
    dump(target, development)
    receipt = {
        "status": "passed",
        "scope": "Post-run exact reconstruction; original input policy and outcomes unchanged",
        "canonical_sha256": actual,
        "file_sha256": file_hash(target),
        "development_groups": len(development),
        "heldout_inputs_used": 0,
    }
    dump(args.replay / "development-reconstruction.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
