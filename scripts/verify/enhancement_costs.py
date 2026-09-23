"""Reconcile measured provider attempts across retained studies and HTTP checks."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from evaluation.enhancement.analysis import TARIFF, cost_estimate
from evaluation.enhancement.runner import load, recovered_attempts


def collect(studies: Path, api_files: list[Path]):
    calls, inputs, seen = [], [], set()

    def add(scope, identity, attempt, timestamp, base_url):
        key = (scope, identity)
        if key in seen:
            raise ValueError("Duplicate provider attempt identity in cost inputs")
        seen.add(key)
        if attempt.get("provider") == "mock" or str(attempt.get("model", "")).startswith("mock"):
            return
        usage = attempt.get("usage") or {}
        estimated = (
            cost_estimate(usage, timestamp, model=attempt.get("model"), base_url=base_url)
            if timestamp
            else None
        )
        calls.append(
            {
                "scope": scope,
                "attempt_id": identity,
                "purpose": attempt.get("purpose", attempt.get("stage", "unrecorded")),
                "provider": attempt.get("provider"),
                "model": attempt.get("model"),
                "timestamp": timestamp,
                "usage": usage,
                "latency_ms": attempt.get("latency_ms", attempt.get("provider_latency_ms")),
                "error": attempt.get("error", attempt.get("error_code")),
                "estimated_cny": estimated,
            }
        )

    for run in sorted(studies.iterdir()):
        path = run / "run-manifest.json"
        if not path.exists():
            continue
        manifest = load(path)
        if "experiment" not in manifest:
            continue
        origin_path = run / "generation-origin.json"
        reuse = load(origin_path) if origin_path.exists() else None
        if reuse:
            origin = studies / reuse["run_directory"]
            if digest_file := reuse.get("run_manifest_file_sha256"):
                if (
                    hashlib.sha256((origin / "run-manifest.json").read_bytes()).hexdigest()
                    != digest_file
                ):
                    raise ValueError("Reused generation manifest differs")
        inputs.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for item in manifest["planned"]:
            result_path = run / "results" / (item["id"] + ".json")
            result = load(result_path) if result_path.exists() else {}
            attempts = result.get("outcome", {}).get("attempts", [])
            events = run / "events" / (item["id"] + ".jsonl")
            recovered = recovered_attempts(events) if events.exists() else []
            if len(recovered) > len(attempts):
                attempts = recovered
            if reuse:
                if (
                    hashlib.sha256(result_path.read_bytes()).hexdigest()
                    != reuse["result_file_sha256"][result_path.name]
                ):
                    raise ValueError("Reused generation result differs")
            else:
                for i, attempt in enumerate(attempts):
                    add(
                        run.name,
                        attempt.get("attempt_id", item["id"] + ":" + str(i)),
                        attempt,
                        result.get("completed_at", manifest["created_at"]),
                        manifest["model_config"]["base_url"],
                    )
            judged_path = run / "judgments" / (item["id"] + ".json")
            if judged_path.exists():
                judged = load(judged_path)
                for i, attempt in enumerate(judged.get("attempts", [])):
                    add(
                        run.name + ":offline_judge",
                        item["id"] + ":" + str(i),
                        attempt,
                        judged.get("completed_at"),
                        manifest["model_config"]["base_url"],
                    )
    for path in api_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        inputs.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for i, attempt in enumerate(payload["attempts"]):
            # These controlled local checks used the recorded official DeepSeek endpoint.
            identity = str(attempt.get("attempt_id", attempt.get("id", i)))
            if attempt.get("job_id"):
                identity = str(attempt["job_id"]) + ":" + identity
            add(
                path.stem,
                identity,
                attempt,
                attempt.get(
                    "completion_at", attempt.get("completed_at", payload.get("created_at"))
                ),
                attempt.get("base_url", "https://api.deepseek.com/v1"),
            )
    groups = defaultdict(
        lambda: {
            "attempts": 0,
            "input_tokens_known": 0,
            "output_tokens_known": 0,
            "missing_usage_calls": 0,
            "estimated_cny_known": 0.0,
            "unknown_cost_calls": 0,
        }
    )
    for row in calls:
        key = row["purpose"]
        group = groups[key]
        group["attempts"] += 1
        for dim in ("input_tokens", "output_tokens"):
            group[dim + "_known"] += row["usage"].get(dim) or 0
        group["missing_usage_calls"] += row["usage"].get("total_tokens") is None
        group["estimated_cny_known"] += row["estimated_cny"] or 0
        group["unknown_cost_calls"] += row["estimated_cny"] is None
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inputs": inputs,
        "tariff": TARIFF,
        "calls": calls,
        "by_purpose": dict(groups),
        "totals": {
            key: sum(g[key] for g in groups.values()) for key in next(iter(groups.values()), {})
        },
        "limits": [
            "Recorded provider attempts and supplied call-level usage are counted, including retained failures. Missing usage produces an unknown cost, not a zero charge.",
            "Study completion timestamps are tariff-period proxies where individual call timestamps were unavailable. All current calls fall on the recorded off-peak Sunday.",
            "Currency values are known-usage estimates at the dated published CNY tariff, not account invoices. Provider token usage differs from local context-window counting.",
            "Only explicitly supplied HTTP/memory accounting files are included; original unrelated learner activity is excluded.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--studies", type=Path, required=True)
    parser.add_argument("--api-usage", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve the earlier cost reconciliation")
    result = collect(args.studies.resolve(), args.api_usage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["totals"]))


if __name__ == "__main__":
    main()
