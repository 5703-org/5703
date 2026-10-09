"""Prepare and execute the registered Week 9 teaching comparison."""

import argparse
import json
from pathlib import Path

from app.core.config import Settings
from evaluation.week09.prepare import prepare
from evaluation.week09.study import freeze, execute, summarize, sample_decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--catalogue", type=Path, required=True)
    prep.add_argument("--connection-file", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    frozen = commands.add_parser("freeze")
    frozen.add_argument("--preparation", type=Path, required=True)
    frozen.add_argument("--output", type=Path, required=True)
    frozen.add_argument("--split", choices=["pilot", "reserved"], default="pilot")
    frozen.add_argument("--repeats", type=int, choices=[1, 2, 3], default=1)
    frozen.add_argument("--sample-decision", type=Path)
    for command in ("run", "summarize"):
        child = commands.add_parser(command)
        child.add_argument("--study", type=Path, required=True)
    decision = commands.add_parser("sample-size")
    decision.add_argument("--pilot", type=Path, required=True)
    decision.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.catalogue, args.connection_file, args.output)
        print(
            json.dumps(
                {"cases": len(result["cases"]), "corpus_unchanged": result["corpus_unchanged"]}
            )
        )
    elif args.command == "freeze":
        decision = (
            json.loads(args.sample_decision.read_text(encoding="utf-8"))
            if args.sample_decision
            else None
        )
        print(
            json.dumps(
                freeze(
                    args.preparation,
                    args.output,
                    split=args.split,
                    repeats=args.repeats,
                    sample_decision=decision,
                )
            )
        )
    elif args.command == "run":
        print(json.dumps(execute(args.study, Settings().llm_api_key)))
    elif args.command == "summarize":
        print(json.dumps(summarize(args.study)))
    else:
        print(json.dumps(sample_decision(args.pilot, args.output)))


if __name__ == "__main__":
    main()
