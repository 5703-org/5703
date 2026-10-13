"""Offline atomic-support preparation or saved-judgment validation, without a provider."""

import argparse
import json
from pathlib import Path

from generation.atomic_support_v1 import (
    AtomicContractError,
    execute_atomic_check,
    prepare_atomic_check,
    validate_bound_atomic_judgment,
)
from generation.parser import strict_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        type=Path,
        required=True,
        help="Local JSON containing cases with packet and source_snapshots.",
    )
    parser.add_argument("--case", required=True, help="Exact local case_id to prepare.")
    parser.add_argument(
        "--judgment", type=Path, help="Optional saved reported judgment; validated locally only."
    )
    parser.add_argument(
        "--bind-quotes",
        action="store_true",
        help="Opt in to unique literal quote-coordinate repair; opinions stay unchanged.",
    )
    args = parser.parse_args(argv)
    try:
        catalog = strict_json(args.cases.read_text(encoding="utf-8"))
        cases = [case for case in catalog["cases"] if case["case_id"] == args.case]
        if len(cases) != 1:
            raise ValueError("CASE_ID_NOT_UNIQUE_OR_FOUND")
        case = cases[0]
        if args.judgment is None:
            result = execute_atomic_check(
                case["packet"], case["source_snapshots"], bind_quotes=args.bind_quotes
            )
        else:
            prepared = prepare_atomic_check(case["packet"], case["source_snapshots"])
            result = {
                "status": "LOCAL_SAVED_REPORTED_JUDGMENT_VALIDATED_ONLY",
                "provider_invocations": 0,
                "physical_post_count": 0,
                "result": validate_bound_atomic_judgment(
                    prepared,
                    args.judgment.read_text(encoding="utf-8"),
                    bind_quotes=args.bind_quotes,
                ),
            }
        result["case_id"] = args.case
        result["external_execution_available"] = False
        result["fixture_provenance"] = catalog.get("provenance")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return (
            0
            if result["status"] in {"NOT_RUN", "LOCAL_SAVED_REPORTED_JUDGMENT_VALIDATED_ONLY"}
            else 1
        )
    except AtomicContractError as exc:
        print(
            json.dumps(
                {
                    "status": "LOCAL_CONTRACT_REJECTED",
                    "error": exc.code,
                    **({"quote_binding": exc.quote_binding_audit}
                       if exc.quote_binding_audit is not None else {}),
                    "provider_invocations": 0,
                    "physical_post_count": 0,
                }
            )
        )
    except (KeyError, TypeError, ValueError, OSError):
        print(
            json.dumps(
                {
                    "status": "LOCAL_INPUT_REJECTED",
                    "provider_invocations": 0,
                    "physical_post_count": 0,
                }
            )
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
