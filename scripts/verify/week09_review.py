"""Export exact draft review or import actual independent Week 9 ratings."""

import argparse
import json
from pathlib import Path

from evaluation.week09.diagnostics import summarize
from evaluation.week09.review import export, import_reviews, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("export")
    prepare.add_argument("--study", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--summary", type=Path, required=True)
    collect = commands.add_parser("import")
    collect.add_argument("--review", type=Path, required=True)
    collect.add_argument("--forms", type=Path, nargs="+", required=True)
    collect.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "export":
        manifest = json.loads((args.study / "frozen-study.json").read_text(encoding="utf-8"))
        records = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((args.study / "outcomes").glob("*.json"))
        ]
        report = {
            **summarize(records),
            "review_export": export(records, manifest["cases"], args.output),
        }
        write(args.summary, report)
        print(json.dumps(report))
    else:
        if args.output.exists():
            raise ValueError("Select a new import result; retain earlier ratings")
        report = import_reviews(args.review, args.forms)
        write(args.output, report)
        print(json.dumps({key: value for key, value in report.items() if key != "rows"}))


if __name__ == "__main__":
    main()
