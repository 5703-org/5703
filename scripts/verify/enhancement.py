"""Freeze and execute the Week 8 enhancement experiments with separate judging."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from evaluation.enhancement.catalogue import tasks
from evaluation.enhancement.protocol import (
    CONDITIONS,
    PROTOCOL_VERSION,
    RUBRIC,
    SEED,
    digest,
    freeze,
    hint_schedule,
    validate_tasks,
)
from evaluation.enhancement.sources import corpus_fingerprint, retrieve_task


def freeze_development(output: Path, *, split="development", previous_source=None):
    if output.exists():
        raise ValueError("Preserve previous frozen development material; choose a new path")
    output.mkdir(parents=True)
    if split == "formal":
        from evaluation.enhancement.formal_catalogue import formal_tasks

        task_rows = formal_tasks()
        if {t["family"] for t in task_rows} & {t["family"] for t in tasks()}:
            raise ValueError("Development and formal task families overlap")
    else:
        task_rows = tasks()
    validate_tasks(task_rows, split=split)
    dataset = freeze(
        output / "private-tasks.json",
        {
            "version": PROTOCOL_VERSION,
            "split": split,
            "tasks": task_rows,
            "rubric": RUBRIC,
            "author": "Codex",
            "human_review_count": 0,
        },
    )
    engine = create_engine(Settings().database_url, connect_args={"connect_timeout": 10})
    with Session(engine) as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        release = db.execute(text("select release_id from active_corpus where id=1")).scalar_one()
        before = corpus_fingerprint(db, release)
        model = dict(
            db.execute(
                text(
                    "select m.id,m.public_config,m.config_hash from active_model_configurations a join model_configurations m on m.id=a.configuration_id order by a.workspace_id limit 1"
                )
            )
            .mappings()
            .one()
        )
        rows = []
        for task in task_rows:
            started = time.monotonic()
            if previous_source:
                from evaluation.enhancement.runner import load
                from evaluation.enhancement.sources import source_map

                prior = load(previous_source / "retrieval" / (task["id"] + ".json"))
                result = {
                    **prior,
                    "source_map": source_map(db, prior["evidence"]),
                    "previous_retrieval_sha256": digest(prior),
                    "retrieval_reused": True,
                }
                old_clean = {
                    k: {
                        x: v[x]
                        for x in ("chunk_hash", "spans", "processing_id", "document_version_id")
                    }
                    for k, v in prior["source_map"].items()
                }
                new_clean = {
                    k: {
                        x: v[x]
                        for x in ("chunk_hash", "spans", "processing_id", "document_version_id")
                    }
                    for k, v in result["source_map"].items()
                }
                if old_clean != new_clean:
                    raise ValueError("Original frozen source identities changed")
            else:
                result = retrieve_task(db, task, release)
            row = {"id": task["id"], "retrieval_seconds": time.monotonic() - started, **result}
            rows.append(row)
            freeze(output / "retrieval" / (task["id"] + ".json"), row)
            print(
                json.dumps(
                    {
                        "id": task["id"],
                        "status": result["status"],
                        "evidence": len(result["evidence"]),
                    }
                ),
                flush=True,
            )
        after = corpus_fingerprint(db, release)
        if after != before:
            raise ValueError("Corpus identity changed during read-only retrieval")
        manifest = {
            "protocol": PROTOCOL_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "seed": SEED,
            "dataset_sha256": dataset["content_sha256"],
            "corpus": before,
            "model": model,
            "retrieval": [
                {
                    "task_id": r["id"],
                    "status": r["status"],
                    "evidence_count": len(r["evidence"]),
                    "sha256": digest(r),
                }
                for r in rows
            ],
            "conditions": CONDITIONS,
            "schedule": hint_schedule(task_rows),
            "paid_calls": 0,
            "reference_inputs_sent_to_retrieval": False,
            "corpus_unchanged": True,
        }
        freeze(output / "manifest.json", manifest)
    engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    task = sub.add_parser("freeze-development")
    task.add_argument("--output", type=Path, required=True)
    task.add_argument("--previous-source", type=Path)
    formal = sub.add_parser("freeze-formal")
    formal.add_argument("--output", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("--source", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--experiment", choices=["hints", "citations"], default="hints")
    run.add_argument("--tasks", nargs="+")
    run.add_argument("--conditions", nargs="+")
    run.add_argument("--workers", type=int, default=4)
    judge = sub.add_parser("judge")
    judge.add_argument("--run", type=Path, required=True)
    judge.add_argument("--workers", type=int, default=6)
    analyze = sub.add_parser("analyze")
    analyze.add_argument("--run", type=Path, required=True)
    review = sub.add_parser("export-review")
    review.add_argument("--run", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)
    imported = sub.add_parser("import-review")
    imported.add_argument("--materials", type=Path, required=True)
    imported.add_argument("--ratings", type=Path, required=True)
    imported.add_argument("--reviewer", required=True)
    summary = sub.add_parser("review-summary")
    summary.add_argument("--materials", type=Path, required=True)
    summary.add_argument("--run", type=Path)
    adjudicate = sub.add_parser("import-adjudication")
    adjudicate.add_argument("--materials", type=Path, required=True)
    adjudicate.add_argument("--ratings", type=Path, required=True)
    adjudicate.add_argument("--adjudicator", required=True)
    args = parser.parse_args()
    if args.operation == "freeze-development":
        freeze_development(args.output.resolve(), previous_source=args.previous_source)
    elif args.operation == "freeze-formal":
        freeze_development(args.output.resolve(), split="formal")
    elif args.operation == "run":
        from evaluation.enhancement.runner import run

        print(
            json.dumps(
                run(
                    args.source.resolve(),
                    args.output.resolve(),
                    experiment=args.experiment,
                    task_ids=args.tasks,
                    conditions=args.conditions,
                    workers=args.workers,
                )
            )
        )
    elif args.operation == "judge":
        from evaluation.enhancement.judge import run_judging

        run_judging(args.run.resolve(), workers=args.workers)
    elif args.operation == "analyze":
        from evaluation.enhancement.analysis import analyse

        result = analyse(args.run.resolve())
        print(
            json.dumps(
                {
                    "metrics": result["metrics"],
                    "paired_task_comparisons": result["paired_task_comparisons"],
                }
            )
        )
    elif args.operation == "export-review":
        from evaluation.enhancement.review import export_reviews

        print(json.dumps(export_reviews(args.run.resolve(), args.output.resolve())))
    elif args.operation == "import-review":
        from evaluation.enhancement.review import import_review

        print(
            json.dumps(
                import_review(args.materials.resolve(), args.ratings.resolve(), args.reviewer)
            )
        )
    elif args.operation == "review-summary":
        from evaluation.enhancement.review import agreement

        print(json.dumps(agreement(args.materials.resolve(), args.run)))
    elif args.operation == "import-adjudication":
        from evaluation.enhancement.review import import_adjudication

        print(
            json.dumps(
                import_adjudication(
                    args.materials.resolve(), args.ratings.resolve(), args.adjudicator
                )
            )
        )


if __name__ == "__main__":
    main()
