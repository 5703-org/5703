"""Summarize closed, gold-free observations; scientific scoring remains blocked."""
import hashlib
import json
import os
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

R = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-failure-strata-checker-pair-20261008-02")
TERMINAL = R / "actual-public-openqa36-root-residual-quality-20261008-01/terminal-receipt01.json"
FROZEN = R / "public12-openqa36-frozen-inputs01.json"
OUT = R / "actual-openqa36-timings-only01"
ARMS = ("E0_none", "E1_dense", "hybrid_plus_rerank")

def read(path, expected=None):
    raw = path.read_bytes()
    item = {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    if expected and item["sha256"] != expected:
        raise ValueError("Input changed: " + str(path))
    return json.loads(raw), item

def percentile(values, q):
    values = sorted(values)
    index = (len(values) - 1) * q
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)

def save(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

def main():
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise ValueError("Use -I -B -S")
    if OUT.exists():
        raise ValueError("CreateNew outputs required")
    receipt, receipt_pin = read(TERMINAL, "f2712ed9ae60914374e4fc67e0ba2ce3931dce9be918dd61d0ccd8989d4db26e")
    frozen, frozen_pin = read(FROZEN, "17d0135cc0e348e3336c39b878078808ab9dfea0178f29f5a247335830e80e3e")
    closure_pins = []
    for group in ("checker", "quality"):
        closure, item = read(R / f"ROOT-owned-root-residual-{group}-20261008-01/closure.json")
        if closure.get("exit_code") != 0 or closure.get("cleanup_errors") != []:
            raise ValueError("Owned process cleanup failed")
        if not all(closure.get(key) is True for key in (
                "process_handle_closed", "job_handle_closed", "own_job_active_zero_verified", "memory_key_cleared")):
            raise ValueError("Owned process closure is incomplete")
        closure_pins.append(item)
    if (receipt.get("status") != "ACTUAL_PUBLIC_MATCHED_OPENQA36_TERMINAL" or
            receipt.get("exit_code") != 0 or receipt.get("physical_calls") != 36 or
            receipt.get("unstarted_count") != 0 or receipt.get("engine_disposed") is not True or
            receipt.get("memory_key_references_cleared") is not True or
            Decimal(receipt["unknown_holds_USD"]) != 0):
        raise ValueError("Complete settled terminal required")
    if (R / "new-residual37-claims/STOP-before-any-next-submission01.json").exists():
        raise ValueError("Unexpected current STOP")
    plans = {item["slot"]: item for item in frozen["plans"]}
    rows = receipt["rows"]
    if len(rows) != 36 or {row["slot"] for row in rows} != set(range(1, 37)):
        raise ValueError("Exactly 36 unique rows required")
    groups, observations, pins = defaultdict(list), [], []
    known = Decimal(0)
    for row in rows:
        slot = row["slot"]
        plan = plans[slot]
        for key in ("arm", "question_id", "protocol", "wire_sha256", "wire_bytes", "source_chunk_ids"):
            if row[key] != plan[key]:
                raise ValueError("Frozen plan mismatch")
        local, local_pin = read(TERMINAL.parent / f"slot-{slot:02d}-finished01.json")
        if local != row:
            raise ValueError("Immutable local result differs from terminal")
        shared, shared_pin = read(R / f"new-residual37-claims/quality_openqa/slot-{slot:02d}-finished01.json")
        fee = Decimal(str(row["usage"]["cost"]))
        if (shared.get("status") != "KNOWN_COST_RECORDED" or
                Decimal(shared["known_API_cost_USD"]) != fee or
                Decimal(shared["UNKNOWN_full_hold_USD"]) != 0 or
                fee < 0 or fee > Decimal("0.04124160")):
            raise ValueError("Shared fee mismatch")
        duration = row["observed_duration_ms"]
        if type(duration) not in (int, float) or not (0 < duration < 1800000):
            raise ValueError("Finite positive duration required")
        if (row.get("status") != "completed" or row.get("http_status") != 200 or
                row.get("physical_POSTs") != 1 or row.get("request_submitted") is not True):
            raise ValueError("Unexpected outcome; do not use success-only denominator")
        groups[row["arm"]].append(duration)
        observations.append({"slot": slot, "arm": row["arm"], "question_id": row["question_id"],
                             "completed": True, "observed_duration_ms": duration, "API_cost_USD": str(fee)})
        pins.extend((local_pin, shared_pin))
        known += fee
    if set(groups) != set(ARMS) or any(len(values) != 12 for values in groups.values()):
        raise ValueError("Three fixed n=12 arms required")
    if known != Decimal(receipt["known_cost_USD"]):
        raise ValueError("Aggregate fee mismatch")
    stats = {}
    for arm in ARMS:
        values = groups[arm]
        stats[arm] = {"scheduled_n": 12, "completed_n": 12, "median_ms": percentile(values, .5),
                      "p95_ms": percentile(values, .95), "min_ms": min(values), "max_ms": max(values),
                      "scientific_accuracy": None, "exact_match": None, "token_F1": None}
    report = {"status": "ACTUAL_GOLD_FREE_OPENQA36_TIMINGS_COMPLETE_QUALITY_SCORING_BLOCKED",
              "quality_scoring": "BLOCKED_AUTO_REVIEW_EVALUATOR_PRIVATE_REFERENCE_SOURCE",
              "no_Gold_or_reference_reads": True, "provider_calls_by_summary": 0,
              "scheduled_n": 36, "completed_n": 36, "known_API_cost_USD": str(known),
              "new_UNKNOWN_holds_USD": "0", "arm_statistics": stats, "observations": observations,
              "quantile_method": "linear interpolation at (n-1)*q",
              "duration_scope": "adapter.generate invocation to complete return, before local response validation",
              "native_full_answer_HTTP_retrieval_checker_or_UI_duration": None,
              "valid_paired_checker_latency_comparison": False,
              "held_out_confirmation": False, "human_scoring": None,
              "conditions": "same frozen policy, model, schema and 768-token output cap; rotated three-arm order; n=12 seen failure-strata development questions",
              "source_pins": {"terminal": receipt_pin, "frozen_inputs": frozen_pin,
                              "owned_closures": closure_pins, "finite_finished_receipts": pins},
              "project_complete": False}
    lines = ["# Unified-condition answer return durations", "",
             "All 36 scheduled requests completed and settled. No reference answers were read by this summary.", "",
             "| Arm | Completed / scheduled | Median (s) | p95 (s) | Scientific quality |",
             "| --- | ---: | ---: | ---: | --- |"]
    for arm in ARMS:
        item = stats[arm]
        lines.append(f"| {arm} | 12 / 12 | {item['median_ms']/1000:.4f} | {item['p95_ms']/1000:.4f} | Unscored: reference read blocked |")
    lines += ["", f"API-reported known cost: USD {known}; new UNKNOWN holds: USD 0.", "",
              "The timer covers adapter.generate through complete model return, before local validation. It excludes native HTTP, retrieval, checker, worker polling and UI rendering. These observations do not establish a warm native end-to-end p95 reduction or quality non-inferiority.", "",
              "Inputs are 12 previously seen failure-strata development questions, with identical frozen policy/model/schema/output limits and rotated arm order. No held-out, human or learning-effect result is claimed. The failed checker baseline prevents a valid paired checker speed comparison."]
    OUT.mkdir()
    save(OUT / "answer-return-duration-summary01.json", (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
    save(OUT / "answer-return-duration-summary01.md", ("\n".join(lines) + "\n").encode())
    print(json.dumps({"status": report["status"], "output_dir": str(OUT), "arm_statistics": stats,
                      "known_API_cost_USD": str(known), "Gold_reads": 0, "provider_calls": 0}))

if __name__ == "__main__":
    main()
