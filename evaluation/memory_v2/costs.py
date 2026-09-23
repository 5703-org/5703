"""Offline, content-free accounting for explicitly selected Memory V2 executions.

No database, provider or model calls are made. Journals and saved outcomes are
two observations of the same attempt, never two charges. Missing usage and
unfinished reservations remain unknown. Estimates are not provider invoices.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from evaluation.enhancement.analysis import TARIFF, cost_estimate
from evaluation.enhancement.protocol import digest, verify_frozen

VERSION = "memory_v2_accounting_v1"
TARIFF_VERIFICATION = {
    **TARIFF,
    "retrieved_date": "2026-09-21",
    "verification_method": "Official Chinese pricing page indexed search result; direct open timed out.",
    "verified_values_unchanged_from_historical_function": True,
    "billing_timestamp_rule": "Attempt completion, otherwise start, otherwise explicitly labelled result-completion proxy. Billing-time selection is an estimate.",
}
TOKENS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "reasoning_tokens",
    "cache_hit_input_tokens",
    "cache_miss_input_tokens",
)
IDENTIFIER = re.compile(r"[A-Za-z0-9_.:/-]{1,200}\Z")


def safe_id(value):
    if value is None:
        return None
    value = str(value)
    return value if IDENTIFIER.fullmatch(value) else "sha256:" + digest(value)


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.isoformat() if parsed.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def usage(value):
    value = value if isinstance(value, dict) else {}
    return {k: value[k] if type(value.get(k)) is int and value[k] >= 0 else None for k in TOKENS}


def endpoint(value):
    try:
        parsed = urlsplit(value or "")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            return None
        return f"{parsed.scheme}://{parsed.hostname}" if parsed.hostname else None
    except ValueError:
        return None


class Collector:
    def __init__(self):
        self.rows = {}
        self.inputs = {}
        self.requests = []
        self.warnings = []
        self._roots = set()
        self._configurations = {}
        self._request_scopes = set()

    def read(self, path):
        raw = path.read_bytes()
        self.inputs[str(path.resolve())] = hashlib.sha256(raw).hexdigest()
        value = json.loads(raw)
        return (
            verify_frozen(value) if isinstance(value, dict) and "content_sha256" in value else value
        )

    def events(self, path):
        if not path.exists():
            return []
        raw = path.read_bytes()
        self.inputs[str(path.resolve())] = hashlib.sha256(raw).hexdigest()
        # A truncated journal is not silently interpreted as a completed run.
        try:
            return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        except ValueError as exc:
            raise ValueError("Malformed accounting journal; preserve it and investigate") from exc

    def add(
        self,
        scope,
        identity,
        attempt,
        config,
        *,
        origin,
        request,
        status,
        phase=None,
        proxy_time=None,
        role="product",
    ):
        config_id = attempt.get("configuration_id", attempt.get("model_configuration_id"))
        if config_id in self._configurations:
            config = self._configurations[config_id]
        elif config_id and config.get("configuration_id") not in {None, config_id}:
            config = {}  # Never price a different checker using the answer endpoint.
        key = digest([scope, str(identity)])
        row = self.rows.setdefault(
            key,
            {
                "accounting_id": key,
                "attempt_id": safe_id(identity),
                "request_id": safe_id(request),
                "role": safe_id(role),
                "request_status": safe_id(status),
                "purpose": None,
                "provider": None,
                "model": None,
                "configuration_id": None,
                "endpoint": None,
                "provider_request_id": None,
                "request_submitted": None,
                "error_code": None,
                "finish_reason": None,
                "usage": usage({}),
                "latency_ms": None,
                "started_at": None,
                "completed_at": None,
                "result_time_proxy": timestamp(proxy_time),
                "has_start": False,
                "has_finish": False,
                "observations": [],
            },
        )
        row["observations"].append(origin)
        error = attempt.get("error") or {}
        if isinstance(error, str):
            error = {"code": error}
        diag = attempt.get("diagnostic") or attempt.get("provider_diagnostic") or {}
        purpose = attempt.get("purpose", attempt.get("stage"))
        current = {
            "purpose": safe_id(purpose),
            "provider": safe_id(attempt.get("provider", config.get("provider"))),
            "model": safe_id(attempt.get("model", config.get("model"))),
            "configuration_id": safe_id(
                attempt.get(
                    "configuration_id",
                    attempt.get("model_configuration_id", config.get("configuration_id")),
                )
            ),
            "endpoint": endpoint(attempt.get("base_url", config.get("base_url"))),
            "provider_request_id": safe_id(
                attempt.get("provider_request_id", diag.get("provider_request_id"))
            ),
            "request_submitted": attempt.get("request_submitted", diag.get("request_submitted")),
            "error_code": safe_id(error.get("code", attempt.get("error_code"))),
            "finish_reason": safe_id(attempt.get("finish_reason", diag.get("finish_reason"))),
        }
        if type(current["request_submitted"]) is not bool:
            current["request_submitted"] = None
        for name, value in current.items():
            if value is not None:
                if row[name] is not None and row[name] != value:
                    # Recovery placeholders do not replace a subsequently retained receipt.
                    if name == "error_code" and "UNCERTAIN" in str(row[name]):
                        row[name] = value
                        continue
                    raise ValueError("Conflicting saved attempt observations: " + name)
                row[name] = value
        for name, value in usage(attempt.get("usage")).items():
            if value is not None:
                if row["usage"][name] is not None and row["usage"][name] != value:
                    raise ValueError("Conflicting usage for the same attempt")
                row["usage"][name] = value
        latency = attempt.get("latency_ms")
        if type(latency) in (int, float) and 0 <= latency < float("inf"):
            row["latency_ms"] = latency
        if phase in {"start", "started"}:
            row["has_start"] = True
            row["started_at"] = (
                timestamp(attempt.get("started_at", attempt.get("recorded_at")))
                or row["started_at"]
            )
        if phase in {"finish", "finished"}:
            row["has_finish"] = True
            row["completed_at"] = (
                timestamp(attempt.get("completed_at", attempt.get("recorded_at")))
                or row["completed_at"]
            )
        row["started_at"] = timestamp(attempt.get("started_at")) or row["started_at"]
        row["completed_at"] = timestamp(attempt.get("completed_at")) or row["completed_at"]
        row["has_start"] = row["has_start"] or row["started_at"] is not None
        return row

    def request(self, root, identity, saved, event_file, config, *, role="product", scope=None):
        scope = scope or str(root.resolve()) + ":" + str(identity)
        outcome = saved.get("outcome") or saved
        attempts = outcome.get("attempts") or saved.get("recovered_attempts") or []
        status = saved.get("status", saved.get("state"))
        if status is None:
            status = "error" if outcome.get("error") else "recorded"
        event_values = self.events(event_file) if event_file else []
        pending, automatic = [], 0
        observed = set()
        for index, event in enumerate(event_values):
            phase = event.get("phase")
            if phase not in {"start", "started", "finish", "finished"}:
                continue
            attempt_id = event.get("attempt_id", event.get("sequence"))
            if attempt_id is None:
                if phase in {"start", "started"}:
                    automatic += 1
                    attempt_id = f"journal-{automatic}"
                    pending.append(attempt_id)
                elif pending:
                    attempt_id = pending.pop(0)
                else:
                    raise ValueError("Anonymous finish has no matching reservation")
            observation = (str(attempt_id), phase in {"finish", "finished"})
            if observation in observed:
                raise ValueError("Repeated journal phase for the same attempt")
            observed.add(observation)
            self.add(
                scope,
                attempt_id,
                event,
                config,
                origin=f"journal:{index + 1}",
                request=identity,
                status=status,
                phase=phase,
                proxy_time=saved.get("completed_at"),
                role=role,
            )
        attempt_ids = {a for a, _ in observed}
        for index, attempt in enumerate(attempts):
            attempt_id = attempt.get("attempt_id", attempt.get("sequence", f"saved-{index + 1}"))
            if event_values and "attempt_id" not in attempt and "sequence" not in attempt:
                raise ValueError(
                    "Cannot safely deduplicate an unidentified saved attempt and journal"
                )
            attempt_ids.add(str(attempt_id))
            uncertain = "UNCERTAIN" in str(
                (attempt.get("error") or {}).get("code", "")
            ) or attempt.get("status") in {"started", "uncertain"}
            self.add(
                scope,
                attempt_id,
                attempt,
                config,
                origin=f"saved:{index + 1}",
                request=identity,
                status=status,
                phase=None if uncertain else "finish",
                proxy_time=saved.get("completed_at"),
                role=role,
            )
        reserved = (outcome.get("budget") or {}).get("consumed_calls", len(attempt_ids))
        if type(reserved) is not int or reserved < len(attempt_ids):
            raise ValueError("Consumed reservations conflict with retained attempt identities")
        uncertainty = str(saved.get("reason", "")) + str(outcome.get("error") or "")
        if not reserved and "uncertain" in uncertainty.lower():
            self.warnings.append(
                "An uncertain request has no retained call receipts; call count and cost completeness are unknown."
            )
        for missing in range(reserved - len(attempt_ids)):
            self.add(
                scope,
                f"unresolved-{missing + 1}",
                {"error_code": "UNCERTAIN_MISSING_RECEIPT"},
                config,
                origin="budget_reservation_without_receipt",
                request=identity,
                status=status,
                proxy_time=saved.get("completed_at"),
                role=role,
            )
        if scope in self._request_scopes:
            return scope
        self._request_scopes.add(scope)
        self.requests.append(
            {
                "request_id": safe_id(identity),
                "role": safe_id(role),
                "status": safe_id(status),
                "attempt_records": reserved,
            }
        )
        return scope

    def run(self, root, sources=()):
        root = root.resolve()
        if root in self._roots:
            return
        self._roots.add(root)
        checkpoint = {}
        manifests = {}
        for name in (
            "pilot.json",
            "run-manifest.json",
            "answer-manifest.json",
            "state-manifest.json",
            "extraction-manifest.json",
        ):
            if (root / name).exists():
                manifests[name] = self.read(root / name)
        if not manifests:
            raise ValueError("Run has no recognized accounting manifest")
        for manifest in manifests.values():
            checkpoint.update(manifest.get("checkpoint", {}))
            candidates = list(sources)
            if manifest.get("source_directory"):
                candidates.append(Path(manifest["source_directory"]))
            for source in candidates:
                path = source / "study.json"
                if path.exists():
                    study = self.read(path)
                    if manifest.get("study_hash") == digest(study):
                        checkpoint.update(study["checkpoint"])
        config = (
            checkpoint.get("model_config")
            or manifests.get("extraction-manifest.json", {}).get("configuration")
            or manifests.get("state-manifest.json", {}).get("worker_alias", {})
        )
        for selected in [*checkpoint.values(), config]:
            if isinstance(selected, dict) and selected.get("configuration_id"):
                self._configurations[selected["configuration_id"]] = selected
        for folder, role in (("results", "product"), ("extraction", "memory_extraction_v2")):
            files = {p.stem: p for p in (root / folder).glob("*.json")}
            for identity, path in sorted(files.items()):
                saved = self.read(path)
                if str(saved.get("id", identity)) != identity:
                    raise ValueError("Result filename differs from its identity")
                self.request(
                    root,
                    identity,
                    saved,
                    root / "events" / (identity + ".jsonl"),
                    saved.get("configuration", config),
                    role=role,
                )
        # Events without result files still represent possible consumed calls.
        handled = {
            p.stem for folder in ("results", "extraction") for p in (root / folder).glob("*.json")
        }
        for path in sorted((root / "events").glob("*.jsonl")):
            if path.stem not in handled and not path.stem.endswith(("-state", "-legacy")):
                self.request(root, path.stem, {"status": "unfinished"}, path, config)
        for path in sorted((root / "reservations").glob("*.json")):
            self.read(path)
            finished = any(
                (root / folder / path.name).exists()
                for folder in ("results", "extraction", "states")
            )
            if path.stem.endswith("-state"):
                finished = (
                    finished
                    or (root / "states" / (path.stem.removesuffix("-state") + ".json")).exists()
                )
            if not finished:
                self.warnings.append(
                    "A durable request reservation lacks a terminal record; unknown completion may have incurred additional calls."
                )
        for path in sorted((root / "states").glob("*.json")):
            saved = self.read(path)
            identity = str(saved.get("id", path.stem))
            events = root / "events" / (identity + "-state.jsonl")
            if events.exists():
                summary_accounting = (saved.get("accounting") or {}).get("summary") or {}
                summary_saved = {
                    "status": saved.get("status"),
                    "completed_at": saved.get("completed_at"),
                }
                if "consumed_call_reservations" in summary_accounting:
                    summary_saved["budget"] = {
                        "consumed_calls": summary_accounting["consumed_call_reservations"]
                    }
                if summary_accounting.get("records_readable") is False:
                    self.warnings.append(
                        "M1 summary journal was unreadable; completeness cannot be established."
                    )
                self.request(
                    root,
                    identity + ":summary",
                    summary_saved,
                    events,
                    config,
                    role="memory_summary_M1",
                )
            elif saved.get("summary_updates"):
                for i, result in enumerate(saved["summary_updates"]):
                    attempts = [
                        {"purpose": "rolling_summary", "usage": u} for u in result.get("usage", [])
                    ]
                    self.request(
                        root,
                        f"{identity}:summary:{i}",
                        {
                            "attempts": attempts,
                            "budget": {"consumed_calls": result.get("calls", len(attempts))},
                            "completed_at": saved.get("completed_at"),
                        },
                        None,
                        config,
                        role="memory_summary_M1",
                    )
            # Summary copies in provider_outcomes have no attempt identity. M1 is
            # already accounted above; M2 actual worker receipts have a phase.
            counted = 0
            for i, outcome in enumerate(saved.get("provider_outcomes", [])):
                attempts = [
                    a
                    for a in outcome.get("attempts", [])
                    if a.get("phase") in {"finish", "finished"}
                ]
                if attempts:
                    counted += len(attempts)
                    self.request(
                        root,
                        f"{identity}:M2:{i}",
                        {
                            "attempts": attempts,
                            "completed_at": saved.get("completed_at"),
                            "error": outcome.get("error"),
                        },
                        None,
                        manifests.get("state-manifest.json", {}).get("worker_alias", config),
                        role="memory_writer_M2",
                    )
            accounting = (saved.get("accounting") or {}).get("M2") or {}
            expected = accounting.get("consumed_call_reservations", counted)
            if type(expected) is not int or expected < counted:
                raise ValueError("M2 reservation total conflicts with saved receipts")
            for i in range(expected - counted):
                self.request(
                    root,
                    f"{identity}:M2:unresolved:{i}",
                    {
                        "status": "uncertain",
                        "attempts": [
                            {
                                "attempt_id": "unknown",
                                "purpose": "memory_extraction",
                                "error": {"code": "UNCERTAIN_M2_RESERVATION"},
                            }
                        ],
                    },
                    None,
                    config,
                    role="memory_writer_M2",
                )
            if accounting.get("records_readable") is False:
                self.warnings.append(
                    "M2 database accounting was unreadable; completeness cannot be established."
                )

    def judge(self, root):
        root = root.resolve()
        if root in self._roots:
            raise ValueError("A run root was also supplied as a judge root")
        self._roots.add(root)
        plan = self.read(root / "judge-plan.json")
        self._configurations[plan["model_config"].get("configuration_id")] = plan["model_config"]
        identities = {str(r["id"]) for r in plan["rows"]}
        if len(identities) != len(plan["rows"]):
            raise ValueError("Duplicate judge schedule")
        for identity in sorted(identities):
            path = root / "judgments" / (identity + ".json")
            saved = self.read(path) if path.exists() else {"state": "not_run"}
            if path.exists() and saved.get("plan_sha256") != digest(plan):
                raise ValueError("Judgment belongs to a different plan")
            self.request(
                root,
                identity,
                saved,
                root / "judge-events" / (identity + ".jsonl"),
                plan["model_config"],
                role="offline_judge",
            )
            reservation = root / "judge-reservations" / (identity + ".json")
            if reservation.exists():
                self.read(reservation)
                if not path.exists():
                    self.warnings.append(
                        "A durable judge reservation lacks a terminal record; call count and cost completeness are unknown."
                    )

    def accounting(self, path):
        """Read an explicit safe attempt export, or a provider diagnostic folder.

        Generic exports contain rows[{execution_id,request_id,attempt_id,...}].
        Stable execution_id is mandatory so several exports of the same attempt
        deduplicate; supplied prompts/extra fields never enter this projection.
        """
        if path.is_dir():
            plan = self.read(path / "plan.json")
            config = plan["candidate_config"]
            for entry in sorted(path.glob("attempt-*.json")):
                row = self.read(entry)
                if row.get("plan_hash") != digest(plan):
                    raise ValueError("Diagnostic receipt differs from its frozen plan")
                if row.get("status") == "not_run":
                    self.requests.append(
                        {
                            "request_id": safe_id(row["stage_id"]),
                            "role": "provider_diagnostic",
                            "status": "not_run",
                            "attempt_records": 0,
                        }
                    )
                    continue
                self.request(
                    path,
                    row["stage_id"],
                    {
                        "status": row.get("status"),
                        "attempts": [
                            {
                                **row,
                                "attempt_id": row["stage_id"],
                                "purpose": "provider_diagnostic:" + row["role"] + ":" + row["tier"],
                            }
                        ],
                    },
                    None,
                    config,
                    role="provider_diagnostic",
                )
            return
        value = self.read(path)
        if isinstance(value, dict) and isinstance(value.get("stages"), list):
            # Exact public ModelCompatibilityRun DTO; aggregate usage repeats
            # stage totals and must never become a seventh call.
            for stage in value["stages"]:
                identity = stage["id"]
                config_id = (stage.get("metadata") or {}).get(
                    "configuration_id", value.get("configuration_id")
                )
                config = self._configurations.get(config_id, {})
                if stage.get("status") == "not_run":
                    continue
                self.request(
                    path.parent,
                    value["id"],
                    {
                        "status": value.get("status"),
                        "attempts": [
                            {
                                **stage,
                                "attempt_id": identity,
                                "configuration_id": config_id,
                                "purpose": "provider_diagnostic:"
                                + value["role"]
                                + ":"
                                + stage["tier"],
                                "error_code": stage.get("diagnostic_code")
                                if stage.get("status") != "passed"
                                else None,
                            }
                        ],
                    },
                    None,
                    config,
                    role="provider_diagnostic",
                    scope="compatibility:" + value["id"],
                )
            return
        if isinstance(value, dict) and "actual_generate_calls" in value:
            if value["actual_generate_calls"] != 1:
                raise ValueError(
                    "A diagnostic summary without individual receipts must contain exactly one actual call"
                )
            metadata = value["metadata"]
            config_id = metadata.get("configuration_id")
            config = self._configurations.get(config_id, {})
            # No raw-response file is read. The single-call diagnosis contains
            # already sanitized numeric usage and typed transport diagnostics.
            attempt = {
                "attempt_id": "diagnostic-1",
                "purpose": "provider_diagnostic:checker:project_debug",
                "configuration_id": config_id,
                "usage": value.get("usage"),
                "diagnostic": value.get("diagnostic"),
                "error": value.get("error"),
            }
            self.request(
                path.parent,
                "project_debug",
                {"attempts": [attempt], "completed_at": value.get("completed_at")},
                None,
                config,
                role="provider_diagnostic",
            )
            return
        rows = value.get("rows", value.get("attempts")) if isinstance(value, dict) else value
        if not isinstance(rows, list):
            raise ValueError("Accounting input requires an explicit attempt list")
        for row in rows:
            if not all(row.get(k) for k in ("execution_id", "request_id", "attempt_id")):
                raise ValueError("Export requires execution, request and attempt identities")
            self.request(
                path.parent,
                row["request_id"],
                {"status": row.get("request_outcome"), "attempts": [row]},
                None,
                row,
                role=row.get("role", "runtime"),
                scope="export:" + str(row["execution_id"]) + ":" + str(row["request_id"]),
            )

    def report(self):
        for path, expected in self.inputs.items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
                raise ValueError(
                    "Accounting inputs changed while being collected; retain a new snapshot"
                )
        rows, provider_ids = [], {}
        for row in self.rows.values():
            known = row["usage"]
            invalid = (
                all(
                    known[k] is not None
                    for k in ("input_tokens", "cache_hit_input_tokens", "cache_miss_input_tokens")
                )
                and known["input_tokens"]
                != known["cache_hit_input_tokens"] + known["cache_miss_input_tokens"]
            ) or (
                all(known[k] is not None for k in ("input_tokens", "output_tokens", "total_tokens"))
                and known["total_tokens"] != known["input_tokens"] + known["output_tokens"]
            )
            at = row["completed_at"] or row["started_at"] or row["result_time_proxy"]
            row["pricing_timestamp"] = at
            row["timestamp_basis"] = (
                "attempt_completion"
                if row["completed_at"]
                else "attempt_start"
                if row["started_at"]
                else "result_completion_proxy"
                if at
                else "unknown"
            )
            row["usage_consistent"] = not invalid
            row["submission_status"] = (
                "not_submitted"
                if row["request_submitted"] is False
                else "submitted"
                if row["request_submitted"] is True
                else "uncertain"
            )
            nonzero_unsubmitted = row["request_submitted"] is False and any(
                v for v in known.values()
            )
            if row["request_submitted"] is False and not nonzero_unsubmitted:
                estimated, reason = 0.0, "explicitly_not_submitted"
            elif invalid or nonzero_unsubmitted:
                estimated, reason = None, "inconsistent_usage_or_submission"
            else:
                estimated = (
                    cost_estimate(known, at, model=row["model"], base_url=row["endpoint"])
                    if at
                    else None
                )
                reason = (
                    "published_tariff_estimate"
                    if estimated is not None
                    else "missing_usage_time_or_supported_tariff"
                )
            row["estimated_cny"], row["pricing_status"] = estimated, reason
            pid = (row["endpoint"], row["provider_request_id"])
            if pid[0] and pid[1] and pid in provider_ids:
                old = provider_ids[pid]
                if any(
                    old[k] != row[k] for k in ("model", "purpose", "usage", "request_submitted")
                ):
                    raise ValueError("Conflicting duplicate provider request ID")
                old["observations"].append("duplicate_provider_receipt:" + row["accounting_id"])
                continue
            if pid[0] and pid[1]:
                provider_ids[pid] = row
            rows.append(row)

        def summarize(items):
            unknown = sum(r["estimated_cny"] is None for r in items)
            subtotal = sum(r["estimated_cny"] for r in items if r["estimated_cny"] is not None)
            totals = {
                k: {
                    "known_subtotal": sum(
                        r["usage"][k] for r in items if r["usage"][k] is not None
                    ),
                    "unknown_attempts": sum(r["usage"][k] is None for r in items),
                }
                for k in TOKENS
            }
            return {
                "attempts": len(items),
                "submission_counts": dict(Counter(r["submission_status"] for r in items)),
                "unfinished_attempts": sum(not r["has_finish"] for r in items),
                "known_estimated_cny_subtotal": subtotal,
                "unknown_cost_attempts": unknown,
                "estimated_cny_complete": None if unknown or self.warnings else subtotal,
                "completeness_established": not unknown and not self.warnings,
                "tokens": totals,
            }

        purposes, roles = defaultdict(list), defaultdict(list)
        for row in rows:
            purposes[row["purpose"] or "unknown"].append(row)
            roles[row["role"]].append(row)
        return {
            "version": VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "implementation": {
                "evaluation/memory_v2/costs.py": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
                "evaluation/enhancement/analysis.py": hashlib.sha256(
                    (Path(__file__).resolve().parents[1] / "enhancement/analysis.py").read_bytes()
                ).hexdigest(),
            },
            "tariff": TARIFF_VERIFICATION,
            "scope": "Read-only snapshot of retained attempts in explicitly supplied executions, not a forecast of all future scheduled calls. No provider invoice reconciliation. Reservations do not prove submission. Unknown usage/cost remains null. Request-level completion timestamps are labelled proxies. M1 journal copies and M2 saved receipts are counted once; missing reservations stay uncertain.",
            "total": summarize(rows),
            "by_purpose": {k: summarize(v) for k, v in sorted(purposes.items())},
            "by_role": {k: summarize(v) for k, v in sorted(roles.items())},
            "rows": rows,
            "request_status_counts": dict(Counter(r["status"] or "unknown" for r in self.requests)),
            "warnings": sorted(set(self.warnings)),
            "inputs": [
                {"path_sha256": digest(k), "sha256": v} for k, v in sorted(self.inputs.items())
            ],
            "privacy": "Allowlisted identifiers, numbers, statuses, timestamps and input hashes only; no prompts, answers, source text, memory content, credentials or local paths.",
        }


def collect(*, runs=(), judges=(), accounting=(), sources=()):
    collector = Collector()
    for path in runs:
        collector.run(Path(path), [Path(p) for p in sources])
    for path in judges:
        collector.judge(Path(path))
    for path in accounting:
        collector.accounting(Path(path))
    return collector.report()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "judge", "accounting", "source"):
        parser.add_argument("--" + name, action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not (args.run or args.judge or args.accounting):
        parser.error("At least one explicit run, judge or accounting input is required")
    result = collect(
        runs=args.run, judges=args.judge, accounting=args.accounting, sources=args.source
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result["total"]))


if __name__ == "__main__":
    main()
