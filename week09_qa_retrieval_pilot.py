"""Freeze and run a read-only, four-book E0/E1/interactive retrieval pilot."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from evaluation.week09_continuation.qa_retrieval_pilot import execute, freeze  # noqa: E402
from evaluation.week09_continuation.protocol import canonical  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    frozen = actions.add_parser("freeze")
    frozen.add_argument("--catalogue", type=Path, required=True)
    frozen.add_argument("--reserved-catalogue", type=Path, required=True)
    frozen.add_argument("--policy", type=Path, required=True)
    frozen.add_argument("--output", type=Path, required=True)
    frozen.add_argument("--public-receipt", type=Path, required=True)
    run = actions.add_parser("run")
    run.add_argument("--study", type=Path, required=True)
    run.add_argument("--isolated-stage-dotenv", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--public-receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.public_receipt.exists():
        raise ValueError("Preserve the previous public pilot receipt")
    if args.action == "freeze":
        receipt = freeze(
            args.catalogue,
            args.reserved_catalogue,
            args.policy,
            args.output,
            root=ROOT,
        )
    else:
        receipt = execute(args.study, args.isolated_stage_dotenv, args.output)
    args.public_receipt.parent.mkdir(parents=True, exist_ok=True)
    args.public_receipt.write_bytes(canonical(receipt))
    sys.stdout.write(canonical(receipt).decode("utf-8"))


if __name__ == "__main__":
    main()
