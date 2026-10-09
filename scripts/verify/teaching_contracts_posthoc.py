"""Eight separately frozen engineering checks after the registered comparison.

Cases are selected after observed failures. Results are post-hoc repair evidence,
not a new held-out estimate or a replacement for any registered outcome.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path

from app.core.config import Settings
from generation import ModelConfig
from generation.token_counting import TokenCounter
from scripts.verify.teaching_contracts_live import (
    endpoints,
    read,
    run_one,
    sha,
    source_snapshot,
    write,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predecessor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new post-hoc evidence directory")
    previous = read(args.predecessor / "frozen-study.json")
    schedule = [
        item
        for item in previous["schedule"]
        if item["policy"] == "evidence_reliability_v3"
        and item["case_id"] in {"W8V2-Q01", "W8V2-Q13"}
        and item["stage"] in {"first_hint", "learner_attempt"}
    ]
    assert len(schedule) == 8
    manifest = {
        **previous,
        "schema": "teaching_contract_posthoc_engineering_v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "planned_outcomes": len(schedule),
        "schedule": schedule,
        "source_hashes": source_snapshot(),
        "posthoc_runner_sha256": sha(Path(__file__).read_bytes()),
        "predecessor_study_sha256": sha((args.predecessor / "frozen-study.json").read_bytes()),
        "design": "Post-hoc engineering cases selected after the predecessor128 outcomes: two fixed families, two modes, first-hint and learner-attempt. All predecessor records remain unchanged. Exact tutor-question materialization and independent completeness gate are the successor behavior under test. No scientific effect estimate or quality superiority is inferred.",
        "warmup": "Pinned tokenizer initialized serially before two-thread execution; no provider warmup calls.",
    }
    write(args.output / "frozen-study.json", manifest)
    for relative in manifest["source_hashes"]:
        target = args.output / "frozen-source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Path(relative).read_bytes())
    for key in ["model_config", "checker_config"]:
        TokenCounter(ModelConfig.from_dict(manifest[key])).count(
            "Teaching-contract tokenizer warmup"
        )
    settings = Settings()
    if not settings.llm_api_key:
        raise ValueError("Local provider credential unavailable")
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(
            pool.map(
                lambda item: run_one(item, manifest, args.output, settings.llm_api_key), schedule
            )
        )
    attempts = [a for r in rows for a in (r.get("outcome") or {}).get("attempts", [])]
    summary = {
        "schema": "teaching_contract_posthoc_results_v1",
        "planned": len(schedule),
        "terminal": len(rows),
        "frozen_study_sha256": sha((args.output / "frozen-study.json").read_bytes()),
        "outcomes": [
            {
                "id": r["schedule"]["id"],
                "case_id": r["schedule"]["case_id"],
                "answer_mode": r["schedule"]["answer_mode"],
                "stage": r["schedule"]["stage"],
                **endpoints(r),
                "error": r.get("error")
                or ((r.get("outcome") or {}).get("error") or {}).get("code"),
                "calls": len((r.get("outcome") or {}).get("attempts", [])),
                "tutor_question_present": bool(
                    (r.get("outcome") or {}).get("teaching_context", {}).get("tutor_question")
                ),
            }
            for r in rows
        ],
        "provider_attempts": len(attempts),
        "usage": {
            k: {
                "known_sum": sum(a.get("usage", {}).get(k) or 0 for a in attempts),
                "missing_attempts": sum(a.get("usage", {}).get(k) is None for a in attempts),
            }
            for k in [
                "input_tokens",
                "output_tokens",
                "cache_hit_input_tokens",
                "cache_miss_input_tokens",
            ]
        },
        "source_unchanged": all(r.get("source_unchanged", False) for r in rows),
        "human_ratings": 0,
        "monetary_cost": None,
        "interpretation": manifest["design"],
    }
    write(args.output / "public-results.json", summary)
    print(
        json.dumps(
            {
                "terminal": len(rows),
                "passed_contract": sum(
                    r["automatic_contract_success"] for r in summary["outcomes"]
                ),
                "provider_attempts": len(attempts),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
