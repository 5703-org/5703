"""Small paired memory application pilot with preserved Week 8 generation code.

Preparation uses current selectors. Retrieval and generation use an extracted,
hash-checked baseline in a separate invocation. No reserved case is selected.
"""

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
from types import SimpleNamespace
import zipfile


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(args):
    from personalisation import memory_v2, memory_v3
    from scripts.verify.week09_memory import Counter, source_reader

    if args.output.exists():
        raise ValueError("Use a new pilot output directory")
    dataset = read(args.selection / "frozen-cases.json")
    selected = {c["id"]: c for c in dataset["cases"] if c["split"] == "development"}
    cases = [
        selected["development-01-scoped-positive"],
        selected["development-02-scoped-positive"],
        selected["development-03-conditional-positive"],
        selected["development-04-scoped-positive"],
        {
            **selected["development-01-scoped-negative"],
            "question": selected["development-02-scoped-positive"]["question"],
        },
        {
            **selected["development-02-conditional-negative"],
            "question": selected["development-01-scoped-positive"]["question"],
        },
        {
            **selected["development-01-scoped-positive"],
            "id": "development-01-current-override",
            "question": selected["development-01-scoped-positive"]["question"]
            + " For this answer, be concise.",
            "expected_selected": False,
            "expected_answer_preference": "concise",
        },
        {
            **selected["development-04-conditional-positive"],
            "id": "development-04-current-override",
            "question": selected["development-04-conditional-positive"]["question"]
            + " For this answer, be concise.",
            "expected_selected": False,
            "expected_answer_preference": "concise",
        },
    ]
    policy = read(args.selection / "experimental-policy.json")
    for case in cases:
        case["states"] = {}
        case["selection_traces"] = {}
        for arm, config in (("rules", memory_v3.freeze_policy()), ("semantic", policy)):
            result = memory_v3.select(
                [case["entry"]],
                case["question"],
                {"profile": {"style": "concise"}},
                policy=config,
                source_reader=source_reader,
                counter=Counter(),
            )
            # The frozen v3 generator already understands this typed prompt schema.
            # The experimental selector identity stays in the separate study trace.
            result.state["version"] = memory_v2.SELECTOR_VERSION
            case["states"][arm] = result.state
            case["selection_traces"][arm] = result.trace
    write(
        args.output / "planned-memory.json",
        {
            "study": "Week 9 development-only paired memory application pilot",
            "cases": cases,
            "selection_policy": policy,
            "applicability_labels": "authored fixtures; independent human ratings pending",
            "prompt_projection": "v2 typed schema, same precedence; arm selector identity recorded separately",
            "selection_sources": {
                str(Path(p)): sha(Path(p))
                for p in [
                    "personalisation/memory_v2.py",
                    "personalisation/memory_v3.py",
                    __file__,
                ]
            },
            "planned_outcomes": 16,
        },
    )


def baseline(args, extracting=False):
    root = args.output / "private" / "baseline-source"
    if extracting:
        if root.exists():
            raise ValueError("Preserve the existing baseline extraction")
        root.mkdir(parents=True)
        with zipfile.ZipFile(args.baseline) as archive:
            for item in archive.infolist():
                target = (root / item.filename).resolve()
                if not target.is_relative_to(root.resolve()):
                    raise ValueError("Unsafe baseline archive path")
                archive.extract(item, root)
        hashes = {p.relative_to(root).as_posix(): sha(p) for p in root.rglob("*") if p.is_file()}
        write(
            args.output / "baseline-receipt.json",
            {"archive_sha256": sha(args.baseline), "files": hashes},
        )
    receipt = read(args.output / "baseline-receipt.json")
    if not all(sha(root / p) == value for p, value in receipt["files"].items()):
        raise ValueError("Frozen baseline source drift")
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "backend"))
    return root


def freeze(args):
    root = baseline(args, extracting=True)
    from sqlalchemy import create_engine, select, text
    from sqlalchemy.orm import Session
    from app.core.config import Settings
    from app.modules.identity.models import User
    from app.modules.knowledge.models import ActiveCorpus
    from app.modules.knowledge.service import retrieve
    from app.modules.learning_state.sources import source_map
    from app.modules.model_settings.service import (
        resolve_active_model_config,
        resolve_active_checker_model_config,
    )
    from contracts.models import EvidenceSnapshot
    from conversation.query import prepare_query
    from retrieval.chat import load_policy, rerank_candidates

    plan = read(args.output / "planned-memory.json")
    settings = Settings()
    engine = create_engine(read(args.database_config)["database_url"])
    with Session(engine) as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        assert db.scalar(text("SHOW transaction_read_only")) == "on"
        pointer = db.get(ActiveCorpus, 1)
        assert pointer is not None
        release_id = pointer.release_id
        actor = db.scalar(select(User).where(User.email == "student@example.com"))
        assert actor is not None
        config = resolve_active_model_config(db, settings, actor.workspace_id)
        checker = resolve_active_checker_model_config(db, settings, actor.workspace_id) or replace(
            config, max_tokens=max(config.max_tokens, 4096)
        )
        assert config.provider != "mock" and config.model == "deepseek-flash"
        policy = load_policy(str(root / "configs/retrieval/chat_hybrid_minilm.json"))
        for case in plan["cases"]:
            prepared = prepare_query(case["question"], []).model_dump()
            query = prepared["standalone_query"]
            candidates = retrieve(
                db,
                query,
                release_id,
                variant="R2",
                top_k=20,
                runtime_device="cpu",
                cache_scope="week09-memory-pilot",
            )
            ranked, trace = rerank_candidates(query, candidates, policy, runtime_device="cpu")
            evidence = [
                EvidenceSnapshot.model_validate(
                    {
                        **{k: v for k, v in item.items() if k in EvidenceSnapshot.model_fields},
                        "evidence_id": f"ev_{i:03}",
                        "context_order": i,
                    }
                ).model_dump()
                for i, item in enumerate(ranked, 1)
            ]
            case["retrieval"] = {
                "prepared_query": prepared,
                "evidence": evidence,
                "source_map": source_map(db, SimpleNamespace(release_id=release_id), evidence),
                "trace": trace,
            }
            print(
                json.dumps(
                    {"phase": "frozen_retrieval", "id": case["id"], "chunks": len(evidence)}
                ),
                flush=True,
            )
        assert not db.new and not db.dirty and not db.deleted
    engine.dispose()
    plan.update(
        model_config=config.to_dict(),
        checker_config=checker.to_dict(),
        release_id=release_id,
        generation_policy="evidence_reliability_v3",
        budget={"max_calls": 4, "max_active_seconds": 180},
        baseline_sha256=sha(args.baseline),
        planned_memory_sha256=sha(args.output / "planned-memory.json"),
        execution="Sequential alternating paired order; identical retrieved evidence and baseline generation in both arms.",
    )
    write(args.output / "frozen-study.json", plan)
    write(
        args.output / "freeze-receipt.json",
        {
            "frozen_study_sha256": sha(args.output / "frozen-study.json"),
            "runner_sha256": sha(Path(__file__)),
        },
    )


def execute(args):
    baseline(args)
    from app.core.config import Settings
    from generation import GenerationRequest, GenerationService, ModelConfig, RequestBudget
    from personalisation.compiler import compile_profile

    receipt = read(args.output / "freeze-receipt.json")
    assert sha(args.output / "frozen-study.json") == receipt["frozen_study_sha256"]
    assert sha(Path(__file__)) == receipt["runner_sha256"]
    study = read(args.output / "frozen-study.json")
    key = Settings().llm_api_key
    assert key
    for index, case in enumerate(study["cases"]):
        arms = ("rules", "semantic") if index % 2 == 0 else ("semantic", "rules")
        for arm in arms:
            record_id = case["id"] + "-" + arm
            path = args.output / "private/outcomes" / (record_id + ".json")
            events = args.output / "private/attempt-events" / (record_id + ".jsonl")
            if path.exists():
                continue
            if events.exists():
                raise ValueError("Reconcile interrupted paid attempt before resuming")
            retrieval = case["retrieval"]
            request = GenerationRequest(
                request_id=record_id,
                mode="interactive_chat",
                condition="E1",
                question=case["question"],
                evidence=retrieval["evidence"],
                source_map=retrieval["source_map"],
                prepared_query=retrieval["prepared_query"],
                answer_mode="textbook",
                config=ModelConfig.from_dict(study["model_config"]),
                checker_config=ModelConfig.from_dict(study["checker_config"]),
                enhancement_version="learning_enhancement_v1",
                attribution_strategy="posthoc_spans",
                teaching_condition="T2",
                teaching_context={"mode": "direct", "action": "direct", "help_level": 0},
                reliability_policy="evidence_reliability_v3",
                generation_context_policy="complementary_context_v2",
                repair_policy="cause_specific_repair_v2",
                profile=compile_profile(
                    {"level": "intermediate", "style": "concise", "topics": [], "version": 1},
                    turn_message=case["question"],
                ),
                memory_context=case["states"][arm],
            )

            def on_attempt(value):
                events.parent.mkdir(parents=True, exist_ok=True)
                with events.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(value, ensure_ascii=False) + "\n")
                    stream.flush()

            start = time.perf_counter()
            try:
                outcome = GenerationService(api_key=key, checker_api_key=key).generate(
                    request, RequestBudget(**study["budget"]), on_attempt=on_attempt
                )
                record = {"outcome": outcome.to_dict(), "error": None}
            except Exception as exc:
                record = {"outcome": None, "error": type(exc).__name__}
            record.update(
                id=record_id,
                case_id=case["id"],
                arm=arm,
                request=asdict(request),
                elapsed_ms=(time.perf_counter() - start) * 1000,
            )
            write(path, record)
            print(
                json.dumps(
                    {
                        "id": record_id,
                        "success": bool((record["outcome"] or {}).get("response")),
                        "error": record["error"]
                        or ((record["outcome"] or {}).get("error") or {}).get("code"),
                    }
                ),
                flush=True,
            )
    summarize(args)


def summarize(args):
    study = read(args.output / "frozen-study.json")
    rows = []
    for path in sorted((args.output / "private/outcomes").glob("*.json")):
        record = read(path)
        out = record.get("outcome") or {}
        response = out.get("response") or {}
        text = response.get("answer_text", "")
        rows.append(
            {
                "id": record["id"],
                "case_id": record["case_id"],
                "arm": record["arm"],
                "delivered": bool(response) and not out.get("error"),
                "error": record["error"] or (out.get("error") or {}).get("code"),
                "word_count_proxy": len(text.split()) if response else None,
                "elapsed_ms": record["elapsed_ms"],
                "usage": out.get("usage"),
                "calls": out.get("budget", {}).get("consumed_calls"),
                "preference_application_human": None,
            }
        )
    write(
        args.output / "summary.json",
        {
            "planned": study["planned_outcomes"],
            "observed": len(rows),
            "generation_policy": study["generation_policy"],
            "baseline_sha256": study["baseline_sha256"],
            "human_ratings": 0,
            "interpretation": "Delivery and response length are automatic observations; preference compliance and scientific quality require independent review.",
            "arms": {
                arm: {
                    "delivered": sum(r["delivered"] for r in rows if r["arm"] == arm),
                    "all_latency_median_ms": statistics.median(
                        r["elapsed_ms"] for r in rows if r["arm"] == arm
                    ),
                    "calls": sum(r["calls"] or 0 for r in rows if r["arm"] == arm),
                }
                for arm in ("rules", "semantic")
            },
            "records": rows,
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "freeze", "run", "summarize"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--database-config", type=Path)
    args = parser.parse_args()
    {"prepare": prepare, "freeze": freeze, "run": execute, "summarize": summarize}[args.action](
        args
    )


if __name__ == "__main__":
    main()
