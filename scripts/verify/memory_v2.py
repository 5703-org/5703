"""Prepare and execute the registered Week 8 Memory V2 study."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output", type=Path, required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--source", type=Path, required=True)
    pilot = sub.add_parser("pilot")
    pilot.add_argument("--output", type=Path, required=True)
    pilot.add_argument("--allow-live", action="store_true")
    run = sub.add_parser("run")
    run.add_argument("--source", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument(
        "--studies", nargs="+", choices=["A", "B", "C", "T"], default=["A", "B", "C", "T"]
    )
    run.add_argument("--allow-live", action="store_true")
    review = sub.add_parser("export-review")
    review.add_argument("--run", type=Path, required=True)
    review.add_argument("--memory-run", type=Path)
    review.add_argument("--source", type=Path)
    review.add_argument("--output", type=Path, required=True)
    imported = sub.add_parser("import-review")
    imported.add_argument("--materials", type=Path, required=True)
    imported.add_argument("--ratings", type=Path, required=True)
    imported.add_argument("--reviewer", required=True)
    imported.add_argument("--slot", type=int, choices=[1, 2], required=True)
    imported.add_argument("--independent-human", action="store_true")
    agreement = sub.add_parser("review-summary")
    agreement.add_argument("--materials", type=Path, required=True)
    adjudicate = sub.add_parser("import-adjudication")
    adjudicate.add_argument("--materials", type=Path, required=True)
    adjudicate.add_argument("--ratings", type=Path, required=True)
    adjudicate.add_argument("--adjudicator", required=True)
    adjudicate.add_argument("--human-attestation", action="store_true")
    oracle = sub.add_parser("confirm-oracle")
    oracle.add_argument("--source", type=Path, required=True)
    oracle.add_argument("--case-id", required=True)
    oracle.add_argument("--retrieval", type=Path, required=True)
    oracle.add_argument("--attestation", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "prepare":
        from evaluation.memory_v2.sources import prepare

        result = prepare(args.output.resolve())
        print(
            json.dumps({"corpus": result["corpus"], "retrievals": len(result["retrieval_hashes"])})
        )
    elif args.operation == "freeze":
        from evaluation.memory_v2.sources import finalize

        result = finalize(args.source.resolve())
        print(json.dumps({"sha256": result["content_sha256"], "planned": len(result["schedule"])}))
    elif args.operation == "pilot":
        from evaluation.memory_v2.pilot import run_pilot

        print(json.dumps(run_pilot(args.output.resolve(), allow_live=args.allow_live)))
    elif args.operation == "export-review":
        from evaluation.memory_v2.review import export_reviews

        print(
            json.dumps(
                export_reviews(
                    args.run, args.output, memory_run=args.memory_run, source=args.source
                )
            )
        )
    elif args.operation == "import-review":
        from evaluation.memory_v2.review import import_review

        print(
            json.dumps(
                import_review(
                    args.materials,
                    args.ratings,
                    args.reviewer,
                    slot=args.slot,
                    independent_human=args.independent_human,
                )
            )
        )
    elif args.operation == "review-summary":
        from evaluation.memory_v2.review import agreement

        print(json.dumps(agreement(args.materials)))
    elif args.operation == "import-adjudication":
        from evaluation.memory_v2.review import import_adjudication

        print(
            json.dumps(
                import_adjudication(
                    args.materials,
                    args.ratings,
                    args.adjudicator,
                    human_attestation=args.human_attestation,
                )
            )
        )
    elif args.operation == "confirm-oracle":
        from evaluation.memory_v2.review import confirm_oracle

        print(
            json.dumps(confirm_oracle(args.source, args.case_id, args.retrieval, args.attestation))
        )
    else:
        from evaluation.memory_v2.runner import run

        print(
            json.dumps(
                run(
                    args.source.resolve(),
                    args.output.resolve(),
                    studies=args.studies,
                    allow_live=args.allow_live,
                )
            )
        )


if __name__ == "__main__":
    main()
