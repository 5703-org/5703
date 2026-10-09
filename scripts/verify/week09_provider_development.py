"""Bounded development-only provider checks on inspected historical task families."""

from dataclasses import asdict, replace
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from app.core.config import Settings
from generation import GenerationRequest, GenerationService, ModelConfig, RequestBudget
from generation.probes import description, run as run_probe
from generation.teaching_plan import freeze_generation_policy

PRIVATE = ROOT / "evidence/week09-generation/20260926/private/provider-development-01"
PUBLIC = ROOT / "evidence/week09-generation/20260926/generation/provider-development-01.json"
OLD = ROOT / "evidence/teaching-performance/20260926/private/live-contracts-corrected"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    global PRIVATE, PUBLIC
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase", choices=["initial", "coverage-successor", "routing-successor"], default="initial"
    )
    args = parser.parse_args()
    if args.phase == "coverage-successor":
        PRIVATE = PRIVATE.with_name("provider-development-02")
        PUBLIC = PUBLIC.with_name("provider-development-02.json")
    elif args.phase == "routing-successor":
        PRIVATE = PRIVATE.with_name("provider-development-03")
        PUBLIC = PUBLIC.with_name("provider-development-03.json")
    if PRIVATE.exists() or PUBLIC.exists():
        raise ValueError("Development receipt exists; choose a distinct successor schedule")
    settings = Settings()
    if not settings.llm_api_key:
        raise ValueError("Configured local provider credential is unavailable")
    prior = read(OLD / "frozen-study.json")
    answer_cfg = ModelConfig.from_dict(prior["model_config"])
    checker_cfg = ModelConfig.from_dict(prior["checker_config"])
    requests = []
    previous = read(OLD / "outcomes/C066.json")
    for family in (
        "previous_empty_general_photosynthesis",
        "previous_inconsistent_isotope_calculation",
    ):
        for output_policy in ("strict_v1", "json_example_once_v1"):
            identity = f"D{len(requests) + 1:02d}"
            values = {**previous["request"]}
            if family == "previous_empty_general_photosynthesis":
                values.update(
                    question="What is photosynthesis?",
                    answer_mode="general_knowledge",
                    evidence=[],
                    source_map={},
                    history=[],
                    summary=None,
                    teaching_context={
                        "teaching_mode": "direct",
                        "help_level": 0,
                        "current_step": 1,
                    },
                )
            else:
                values["teaching_context"] = {
                    **(values.get("teaching_context") or {}),
                    "current_step": 1,
                }
            values.update(
                request_id="week09-development-" + identity,
                reliability_policy="evidence_reliability_v4",
                generation_policy=freeze_generation_policy("D"),
                provider_output_policy=output_policy,
                prepared_query={"intent": "factual", "needs_clarification": False},
                understanding=None,
                memory_context=None,
            )
            requests.append({"id": identity, "family": family, "request": values})
    probes = []
    for mode in ("json_object", "prompt"):
        for role, config in (("answer", answer_cfg), ("checker", checker_cfg)):
            prepared = description(replace(config, structured_output_mode=mode), "project", role)
            probes.append(
                {
                    "id": f"P{len(probes) + 1:02d}",
                    "role": role,
                    "mode": mode,
                    "description": {**prepared, "config": prepared["config"].to_dict()},
                }
            )
    if args.phase in {"coverage-successor", "routing-successor"}:
        probes = []
        requests = [
            item
            for item in requests
            if item["family"] == "previous_inconsistent_isotope_calculation"
        ]
        if args.phase == "routing-successor":
            requests = [
                item
                for item in requests
                if item["request"]["provider_output_policy"] == "strict_v1"
            ]
    paths = sorted(
        list((ROOT / "generation").glob("*.py"))
        + list((ROOT / "generation/prompts").glob("*.txt"))
        + [Path(__file__)]
    )
    source_hashes = {
        str(p.relative_to(ROOT)).replace("\\", "/"): sha(p.read_bytes()) for p in paths
    }
    manifest = {
        "schema": "week09_provider_development_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "partition": "development_only",
        "source_hashes": source_hashes,
        "probes": probes,
        "requests": requests,
        "max_calls": len(probes) + 4 * len(requests),
        "per_request_budget": {"max_calls": 4, "max_active_seconds": 180},
        "design": "Four actual-schema transport probes (answer/checker by configured JSON/prompt modes), then two previously inspected failure families paired strict versus one-example empty recovery. All v4 generation prompts contain a legal JSON shape example. Historical general-knowledge empty case is repeated as the same question with fresh direct context; no historical prompt identity is claimed. This is not a pilot, holdout, quality effect estimate, or automatic activation decision.",
        "historical_empty_request_id": "f4ee0c17-348f-4a84-ba55-894a7411f42c",
        "historical_inconsistent_outcome": str((OLD / "outcomes/C066.json").relative_to(ROOT)),
        "human_ratings": None,
        "monetary_cost": None,
    }
    if args.phase == "coverage-successor":
        predecessor = PRIVATE.with_name("provider-development-01") / "schedule.json"
        manifest.update(
            predecessor_sha256=sha(predecessor.read_bytes()),
            design="Separate post-development metadata-transport successor: rerun the two inspected isotope failures after removing repeated lexical debug metadata from transport. Every original source byte, required point, missing-group cue and complete audit remains. The initial failures remain recorded. No holdout or quality effect inference.",
        )
    elif args.phase == "routing-successor":
        predecessor = PRIVATE.with_name("provider-development-02") / "schedule.json"
        manifest.update(
            predecessor_sha256=sha(predecessor.read_bytes()),
            design="One strict development rerun after routing missing actual draft citations to bounded answer repair. Exact support, proof and final publication gates remain required. Previous failures and source snapshots remain unchanged; no holdout or quality effect inference.",
        )
    write(PRIVATE / "schedule.json", manifest)
    for path in paths:
        target = PRIVATE / "frozen-source" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    rows = []
    for item in probes:
        prepared = {
            **item["description"],
            "config": ModelConfig.from_dict(item["description"]["config"]),
        }
        raw = []
        started = time.monotonic()
        result = run_probe(
            prepared,
            api_key=settings.llm_api_key,
            timeout_seconds=60,
            on_private_result=lambda value: raw.append(asdict(value)),
        )
        receipt = {
            "id": item["id"],
            "result": asdict(result),
            "raw_receipt": raw,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        }
        write(PRIVATE / "probes" / (item["id"] + ".json"), receipt)
        rows.append(
            {
                "id": item["id"],
                "kind": "actual_schema_probe",
                "mode": item["mode"],
                "role": item["role"],
                "passed": result.error is None,
                "calls": 1,
                "error_code": (result.error or {}).get("code"),
                "diagnostic_code": result.diagnostic.get("provider_error_code"),
                "usage": result.usage,
                "elapsed_ms": receipt["elapsed_ms"],
            }
        )
        print(json.dumps(rows[-1]), flush=True)
    for item in requests:
        values = {**item["request"], "config": answer_cfg, "checker_config": checker_cfg}
        events = []
        started = time.monotonic()

        def record(event):
            events.append(event)
            write(PRIVATE / "attempts" / (item["id"] + ".json"), events)

        result = GenerationService(
            api_key=settings.llm_api_key, checker_api_key=settings.llm_api_key
        ).generate(
            GenerationRequest(**values), RequestBudget(max_calls=4, max_active_seconds=180), record
        )
        write(PRIVATE / "outcomes" / (item["id"] + ".json"), result.to_dict())
        rows.append(
            {
                "id": item["id"],
                "kind": "inspected_failure_family",
                "family": item["family"],
                "policy": values["provider_output_policy"],
                "passed": result.succeeded,
                "calls": len(result.attempts),
                "error_code": (result.error or {}).get("code"),
                "usage": result.usage,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "empty_recovery_count": len(result.token_budget.get("empty_output_recoveries", [])),
            }
        )
        print(json.dumps(rows[-1]), flush=True)
    keys = (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cache_hit_input_tokens",
        "cache_miss_input_tokens",
    )
    unchanged = all(
        sha((ROOT / path).read_bytes()) == value for path, value in source_hashes.items()
    )
    public = {
        "schema": "week09_provider_development_result_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "schedule_sha256": sha((PRIVATE / "schedule.json").read_bytes()),
        "rows": rows,
        "calls": sum(r["calls"] for r in rows),
        "passed_outcomes": sum(r["passed"] for r in rows),
        "usage": {
            key: sum(r["usage"][key] for r in rows)
            if all(r["usage"].get(key) is not None for r in rows)
            else None
            for key in keys
        },
        "source_unchanged": unchanged,
        "human_ratings": None,
        "monetary_cost": None,
        "interpretation": "Development compatibility and delivery receipts only. Recovery effectiveness is unmeasured when no new empty output occurs; strict remains the default. All failures remain in the denominator.",
    }
    write(PUBLIC, public)
    if not unchanged:
        raise ValueError("Development source changed; all receipts are retained")


if __name__ == "__main__":
    main()
