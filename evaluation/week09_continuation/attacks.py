"""Bounded adaptive-attack scheduler with normal-task preservation metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json

from .protocol import canonical


@dataclass(frozen=True)
class AttackLimits:
    max_attempts: int
    max_attacker_tokens: int

    def __post_init__(self):
        if not 1 <= self.max_attempts <= 20 or not 1 <= self.max_attacker_tokens <= 200_000:
            raise ValueError("Adaptive attacks need bounded attempts and attacker tokens")


def run_adaptive_attack(
    scenario: dict,
    limits: AttackLimits,
    generate_attack,
    execute_target,
    output: Path,
) -> dict:
    """Generator sees only previous public outcomes; target uses an isolated study account."""
    if output.exists():
        raise ValueError("Use a new attack directory; do not repeat paid or stateful attempts")
    if scenario.get("environment") != "isolated_evaluation" or not scenario.get(
        "frozen_defense_hash"
    ):
        raise ValueError("Adaptive attack requires an isolated frozen defender")
    output.mkdir(parents=True)
    history, token_count = [], 0
    for attempt_number in range(1, limits.max_attempts + 1):
        suggestion = generate_attack(
            scenario["public_task"], list(history), limits.max_attacker_tokens - token_count
        )
        if not isinstance(suggestion, dict) or not isinstance(suggestion.get("payload"), str):
            raise ValueError("Attacker must return a concrete payload and measured token use")
        used = suggestion.get("attacker_tokens")
        if type(used) is not int or used < 0 or token_count + used > limits.max_attacker_tokens:
            raise ValueError("Adaptive attacker exceeded its frozen token budget")
        token_count += used
        reservation = output / "reservations" / f"attempt-{attempt_number:02d}.json"
        reservation.parent.mkdir(parents=True, exist_ok=True)
        with reservation.open("xb") as stream:
            stream.write(
                canonical(
                    {
                        "attempt": attempt_number,
                        "reserved_at_utc": datetime.now(timezone.utc).isoformat(),
                        "frozen_defense_hash": scenario["frozen_defense_hash"],
                        "attacker_tokens_cumulative": token_count,
                        "payload": suggestion["payload"],
                    }
                )
            )
        observed = execute_target(scenario["public_task"], suggestion["payload"])
        if (
            not isinstance(observed, dict)
            or type(observed.get("attack_success")) is not bool
            or type(observed.get("safe_task_completed")) is not bool
        ):
            raise ValueError("A target attempt needs both attack and legitimate-task outcomes")
        record = {
            "attempt": attempt_number,
            "attack_success": observed["attack_success"],
            "safe_task_completed": observed["safe_task_completed"],
            "attacker_tokens": used,
            "public_observation": observed.get("public_observation"),
            "defender_error": observed.get("defender_error"),
        }
        destination = output / "outcomes" / f"attempt-{attempt_number:02d}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(canonical(record))
        history.append(
            {
                "attempt": attempt_number,
                "attack_success": record["attack_success"],
                "safe_task_completed": record["safe_task_completed"],
                "public_observation": record["public_observation"],
            }
        )
        if observed["attack_success"]:
            break
    summary = {
        "attempts": len(history),
        "max_attempts": limits.max_attempts,
        "attacker_tokens_used": token_count,
        "attacker_token_limit": limits.max_attacker_tokens,
        "attack_success_observed": any(row["attack_success"] for row in history),
        "safe_legitimate_tasks_completed": sum(row["safe_task_completed"] for row in history),
        "safe_task_denominator": len(history),
        "scope": "Isolated bounded adaptive attack against one frozen defense. This is not a general security guarantee.",
    }
    (output / "summary.json").write_bytes(canonical(summary))
    return summary
