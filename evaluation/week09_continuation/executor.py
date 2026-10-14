"""Application-backed study scheduler with durable pre-call reservations."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Callable

from .protocol import canonical, load_frozen
from .outcomes import write_terminal


def execute(
    folder: Path,
    dispatch: Callable[[dict, str, str], dict],
    *,
    current_source_sha256: str,
    limit: int | None = None,
    allowed_arms: set[str] | None = None,
    allowed_families: set[str] | None = None,
) -> dict:
    """Dispatch only a public task; private labels never enter the answer backend.

    A reservation survives a crash. Such an item is not called a second time
    until its application receipt is independently reconciled.
    """
    manifest = load_frozen(folder)
    if manifest["candidate"]["candidate_source_sha256"] != current_source_sha256:
        raise ValueError("The executable candidate differs from the frozen study")
    if limit is not None and (type(limit) is not int or limit <= 0):
        raise ValueError("A dry-run limit must be a positive integer")
    cases = {case["id"]: case for case in manifest["cases"]}
    executed = skipped = uncertain = deferred_arm = deferred_family = 0
    for item in manifest["schedule"]:
        if allowed_families is not None and item["family"] not in allowed_families:
            deferred_family += 1
            continue
        if allowed_arms is not None and item["arm"] not in allowed_arms:
            deferred_arm += 1
            continue
        identity = item["id"]
        filename = identity.replace("::", "--") + ".json"
        outcome = folder / "outcomes" / filename
        reservation = folder / "reservations" / filename
        if outcome.exists():
            skipped += 1
            continue
        if reservation.exists():
            uncertain += 1
            continue
        if limit is not None and executed >= limit:
            continue
        task = cases[item["case_id"]]["task"]
        reservation.parent.mkdir(parents=True, exist_ok=True)
        reserved_at = datetime.now(timezone.utc).isoformat()
        with reservation.open("xb") as stream:
            stream.write(
                canonical(
                    {
                        "schedule_id": identity,
                        "reserved_at_utc": reserved_at,
                        "task_sha256": hashlib.sha256(canonical(task)).hexdigest(),
                        "candidate_source_sha256": current_source_sha256,
                    }
                )
            )
        started = time.perf_counter()
        try:
            observed = dispatch(task, item["arm"], identity)
            if not isinstance(observed, dict):
                raise TypeError("Study backend must return a terminal record")
        except Exception as exc:
            observed = {
                "state": "execution_failure",
                "provider_calls": None,
                "usage": {},
                "learner_visible_output": None,
                "error": {"type": type(exc).__name__, "message": str(exc)[:500]},
            }
        observed = {
            **observed,
            "schedule_id": identity,
            "reserved_at_utc": reserved_at,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": (time.perf_counter() - started) * 1000,
        }
        write_terminal(folder, observed)
        executed += 1
    return {
        "planned": len(manifest["schedule"]),
        "new_terminal": executed,
        "previous_terminal": skipped,
        "unreconciled_reservations": uncertain,
        "deferred_to_other_arm_runner": deferred_arm,
        "deferred_to_other_family_runner": deferred_family,
        "remaining_unscheduled_execution": len(manifest["schedule"])
        - executed
        - skipped
        - uncertain
        - deferred_arm
        - deferred_family,
        "private_labels_sent_to_backend": False,
    }
