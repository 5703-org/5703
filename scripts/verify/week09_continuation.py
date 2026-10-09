"""Freeze and inspect the expanded Week 9 evaluation without relabelling old studies."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx

from evaluation.week09_continuation import PROTOCOL_VERSION
from evaluation.week09_continuation.blinding import export, import_human_ratings
from evaluation.week09_continuation.calibration import make_packets, compare
from evaluation.week09_continuation.executor import execute
from evaluation.week09_continuation.family_backend import (
    InteractivePilotBackend,
    MemorySelectorPilotBackend,
    PracticeProposalPilotBackend,
    VisualStructurePilotBackend,
)
from evaluation.week09_continuation.http_backend import IsolatedTraceUsage, TextbookQAHttpBackend
from evaluation.conversations.http_backend import HttpChatBackend
from evaluation.week09_continuation.judge import import_ai_ratings, run_blind_judge
from evaluation.week09_continuation.outcomes import summarize, write_terminal
from evaluation.week09_continuation.pilot import sample_decision
from evaluation.week09_continuation.protocol import (
    canonical,
    digest_bytes,
    freeze,
    load_frozen,
    validate_catalogue,
    verify_official_anchors,
)
from evaluation.week09_continuation.source_catalogue import build_development_anchor_catalogue
from evaluation.week09_continuation.simulator_pilot import run_one_turn_calibration
from evaluation.week09_continuation.teaching_backend import TeachingPreparedBackend


def _private_chat(client, path: Path, role: str):
    credentials = json.loads(path.read_text(encoding="utf-8"))[role]
    return HttpChatBackend(client, email=credentials["email"], password=credentials["password"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    children = parser.add_subparsers(dest="command", required=True)
    seed = children.add_parser("development-anchors")
    seed.add_argument("--retrieval-record", type=Path, required=True)
    seed.add_argument("--output", type=Path, required=True)
    validate = children.add_parser("validate-catalogue")
    validate.add_argument("--catalogue", type=Path, required=True)
    anchors = children.add_parser("verify-anchors")
    anchors.add_argument("--catalogue", type=Path, required=True)
    anchors.add_argument("--database-url-env", required=True)
    frozen = children.add_parser("freeze")
    frozen.add_argument("--catalogue", type=Path, required=True)
    frozen.add_argument("--candidate", type=Path, required=True)
    frozen.add_argument("--output", type=Path, required=True)
    frozen.add_argument("--split", choices=["development", "pilot", "reserved"], required=True)
    frozen.add_argument("--pilot-decision", type=Path)
    frozen.add_argument("--connection-file", type=Path)
    frozen.add_argument("--database-url-env")
    frozen.add_argument("--qa-preparation", type=Path)
    frozen.add_argument("--teaching-preparation", type=Path)
    record = children.add_parser("record-terminal")
    record.add_argument("--study", type=Path, required=True)
    record.add_argument("--record", type=Path, required=True)
    summary = children.add_parser("summarize")
    summary.add_argument("--study", type=Path, required=True)
    summary.add_argument("--ratings", type=Path)
    blind = children.add_parser("blind-export")
    blind.add_argument("--study", type=Path, required=True)
    blind.add_argument("--output", type=Path, required=True)
    judge = children.add_parser("judge")
    judge.add_argument("--blind", type=Path, required=True)
    judge.add_argument("--config", type=Path, required=True)
    judge.add_argument("--output", type=Path, required=True)
    judge.add_argument("--resume", action="store_true")
    imported = children.add_parser("import-ai")
    imported.add_argument("--blind", type=Path, required=True)
    imported.add_argument("--judge", type=Path, required=True)
    imported.add_argument("--output", type=Path, required=True)
    human = children.add_parser("import-human")
    human.add_argument("--blind", type=Path, required=True)
    human.add_argument("--ratings", type=Path, required=True)
    human.add_argument("--output", type=Path, required=True)
    decision = children.add_parser("pilot-decision")
    decision.add_argument("--pilot", type=Path, required=True)
    decision.add_argument("--ratings", type=Path, required=True)
    decision.add_argument("--thresholds", type=Path, required=True)
    decision.add_argument("--calibration-result", type=Path, required=True)
    decision.add_argument("--output", type=Path, required=True)
    calibration = children.add_parser("judge-calibration-packets")
    calibration.add_argument("--blind", type=Path, required=True)
    calibration.add_argument("--output", type=Path, required=True)
    calibration.add_argument("--limit", type=int, default=12)
    calibration_summary = children.add_parser("judge-calibration-summary")
    calibration_summary.add_argument("--calibration", type=Path, required=True)
    calibration_summary.add_argument("--judge", type=Path, required=True)
    calibration_summary.add_argument("--output", type=Path, required=True)
    qa = children.add_parser("run-qa-candidate")
    qa.add_argument("--study", type=Path, required=True)
    qa.add_argument("--base-url", default="http://127.0.0.1:18830")
    qa.add_argument("--email", required=True)
    qa.add_argument("--password-env", default="EVALUATION_ACCOUNT_PASSWORD")
    qa.add_argument("--candidate-source-sha256", required=True)
    qa.add_argument("--limit", type=int)
    qa.add_argument("--allow-live", action="store_true")
    qa.add_argument("--trace-database-url-env")
    teaching = children.add_parser("run-teaching-factorial")
    teaching.add_argument("--study", type=Path, required=True)
    teaching.add_argument("--preparation", type=Path, required=True)
    teaching.add_argument("--candidate-source-sha256", required=True)
    teaching.add_argument("--key-env", default="LLM_API_KEY")
    teaching.add_argument("--dotenv", type=Path)
    teaching.add_argument("--limit", type=int)
    teaching.add_argument("--allow-live", action="store_true")
    memory = children.add_parser("run-memory-selectors")
    memory.add_argument("--study", type=Path, required=True)
    memory.add_argument("--candidate-source-sha256", required=True)
    visual = children.add_parser("run-visual-structure")
    visual.add_argument("--study", type=Path, required=True)
    visual.add_argument("--candidate-source-sha256", required=True)
    visual.add_argument("--base-url", default="http://127.0.0.1:18830")
    visual.add_argument("--credentials", type=Path, required=True)
    practice = children.add_parser("run-practice-proposals")
    practice.add_argument("--study", type=Path, required=True)
    practice.add_argument("--candidate-source-sha256", required=True)
    practice.add_argument("--base-url", default="http://127.0.0.1:18830")
    practice.add_argument("--credentials", type=Path, required=True)
    practice.add_argument("--allow-live", action="store_true")
    interactive = children.add_parser("run-interactive-probes")
    interactive.add_argument("--study", type=Path, required=True)
    interactive.add_argument("--candidate-source-sha256", required=True)
    interactive.add_argument("--base-url", default="http://127.0.0.1:18830")
    interactive.add_argument("--credentials", type=Path, required=True)
    interactive.add_argument("--trace-database-url-env")
    interactive.add_argument("--allow-live", action="store_true")
    simulator = children.add_parser("run-simulator-calibration")
    simulator.add_argument("--study", type=Path, required=True)
    simulator.add_argument("--preparation", type=Path, required=True)
    simulator.add_argument("--output", type=Path, required=True)
    simulator.add_argument("--candidate-source-sha256", required=True)
    simulator.add_argument("--key-env", default="LLM_API_KEY")
    simulator.add_argument("--dotenv", type=Path)
    simulator.add_argument("--allow-live", action="store_true")
    args = parser.parse_args()
    if args.command == "development-anchors":
        result = build_development_anchor_catalogue(args.retrieval_record, args.output)
    elif args.command == "validate-catalogue":
        result = validate_catalogue(json.loads(args.catalogue.read_text(encoding="utf-8")))
    elif args.command == "verify-anchors":
        catalogue = json.loads(args.catalogue.read_text(encoding="utf-8"))
        validate_catalogue(catalogue)
        result = verify_official_anchors(
            catalogue["cases"],
            catalogue["source_release_id"],
            database_url_env=args.database_url_env,
        )
    elif args.command == "freeze":
        result = freeze(
            args.catalogue,
            args.candidate,
            args.output,
            split=args.split,
            pilot_decision_path=args.pilot_decision,
            connection_file=args.connection_file,
            database_url_env=args.database_url_env,
            qa_preparation_path=args.qa_preparation,
            teaching_preparation_path=args.teaching_preparation,
        )
    elif args.command == "record-terminal":
        destination = write_terminal(
            args.study, json.loads(args.record.read_text(encoding="utf-8"))
        )
        result = {"saved": str(destination)}
    elif args.command == "summarize":
        result = summarize(args.study, ratings_path=args.ratings)
    elif args.command == "blind-export":
        result = export(args.study, args.output)
    elif args.command == "judge":
        result = run_blind_judge(args.blind, args.config, args.output, resume=args.resume)
    elif args.command == "import-ai":
        result = import_ai_ratings(args.blind, args.judge, output=args.output)
    elif args.command == "pilot-decision":
        result = sample_decision(
            args.pilot,
            args.output,
            independent_ratings=args.ratings,
            quality_thresholds=args.thresholds,
            calibration_result=args.calibration_result,
        )
    elif args.command == "judge-calibration-packets":
        result = make_packets(args.blind, args.output, limit=args.limit)
    elif args.command == "judge-calibration-summary":
        result = compare(args.calibration, args.judge)
        if args.output.exists():
            raise ValueError("Use a fresh calibration summary path")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical(result))
    elif args.command == "run-qa-candidate":
        password = os.environ.get(args.password_env)
        if not password or not args.allow_live:
            raise ValueError("A local account credential and explicit live-study flag are required")
        with httpx.Client(base_url=args.base_url, timeout=30) as client:
            chat = HttpChatBackend(client, email=args.email, password=password)
            if chat.capabilities().get("model_mode") != "live":
                raise ValueError("This formal candidate runner requires live model mode")
            trace = None
            try:
                if args.trace_database_url_env:
                    manifest = load_frozen(args.study)
                    trace = IsolatedTraceUsage(
                        database_url_env=args.trace_database_url_env,
                        expected_release_id=manifest["candidate"]["corpus_release_id"],
                    )
                result = execute(
                    args.study,
                    TextbookQAHttpBackend(chat, trace),
                    current_source_sha256=args.candidate_source_sha256,
                    limit=args.limit,
                    allowed_arms={"candidate"},
                    allowed_families={"textbook_qa"},
                )
            finally:
                if trace is not None:
                    trace.close()
    elif args.command == "run-teaching-factorial":
        from dotenv import dotenv_values

        key = os.environ.get(args.key_env)
        if not key and args.dotenv is not None:
            key = dotenv_values(args.dotenv).get(args.key_env)
        if not key or not args.allow_live:
            raise ValueError("A local model key and explicit live-study flag are required")
        result = execute(
            args.study,
            TeachingPreparedBackend(args.study, args.preparation, api_key=key),
            current_source_sha256=args.candidate_source_sha256,
            limit=args.limit,
            allowed_arms={"A", "B", "C", "D"},
            allowed_families={"joint_tutoring"},
        )
    elif args.command == "run-memory-selectors":
        from generation.token_counting import TokenCounter
        from generation.types import ModelConfig

        frozen_manifest = load_frozen(args.study)
        model = ModelConfig.from_dict(frozen_manifest["candidate"]["model_roles"]["generation"])
        result = execute(
            args.study,
            MemorySelectorPilotBackend(counter=TokenCounter(model)),
            current_source_sha256=args.candidate_source_sha256,
            allowed_arms={"candidate"},
            allowed_families={"learning_memory"},
        )
    elif args.command in {"run-visual-structure", "run-practice-proposals"}:
        if args.command == "run-practice-proposals" and not args.allow_live:
            raise ValueError("Live source-pinned practice generation needs explicit --allow-live")
        frozen_manifest = load_frozen(args.study)
        with httpx.Client(base_url=args.base_url, timeout=90) as client:
            admin = _private_chat(client, args.credentials, "admin")
            backend = (
                VisualStructurePilotBackend(admin)
                if args.command == "run-visual-structure"
                else PracticeProposalPilotBackend(
                    admin,
                    frozen_manifest_sha256=digest_bytes(canonical(frozen_manifest)),
                    candidate_source_sha256=frozen_manifest["candidate"]["candidate_source_sha256"],
                )
            )
            result = execute(
                args.study,
                backend,
                current_source_sha256=args.candidate_source_sha256,
                allowed_arms={"candidate"},
                allowed_families={
                    "visual_structure"
                    if args.command == "run-visual-structure"
                    else "practice_feedback"
                },
            )
    elif args.command == "run-interactive-probes":
        if not args.allow_live:
            raise ValueError("Live interactive safety and performance probes need --allow-live")
        with httpx.Client(base_url=args.base_url, timeout=30) as client:
            owner = _private_chat(client, args.credentials, "owner")
            other = _private_chat(client, args.credentials, "other")
            if owner.capabilities().get("model_mode") != "live":
                raise ValueError("Interactive pilot requires the live model configuration")
            trace = None
            try:
                if args.trace_database_url_env:
                    manifest = load_frozen(args.study)
                    trace = IsolatedTraceUsage(
                        database_url_env=args.trace_database_url_env,
                        expected_release_id=manifest["candidate"]["corpus_release_id"],
                    )
                result = execute(
                    args.study,
                    InteractivePilotBackend(args.study, owner, other, trace_usage=trace),
                    current_source_sha256=args.candidate_source_sha256,
                    allowed_arms={"candidate"},
                    allowed_families={"safety_robustness", "performance_recovery"},
                )
            finally:
                if trace is not None:
                    trace.close()
    elif args.command == "run-simulator-calibration":
        from dotenv import dotenv_values

        key = os.environ.get(args.key_env)
        if not key and args.dotenv is not None:
            key = dotenv_values(args.dotenv).get(args.key_env)
        if not key or not args.allow_live:
            raise ValueError("Simulator calibration needs a local model key and --allow-live")
        result = run_one_turn_calibration(
            args.study,
            args.preparation,
            args.output,
            candidate_source_sha256=args.candidate_source_sha256,
            api_key=key,
        )
    else:
        result = import_human_ratings(args.blind, args.ratings, output=args.output)
    print(json.dumps({"protocol": PROTOCOL_VERSION, "result": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
