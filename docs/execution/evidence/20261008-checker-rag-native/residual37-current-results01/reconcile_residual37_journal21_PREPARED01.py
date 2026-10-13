"""Prepared settled-only, append-only J21 reconciliation. Root executes after review.

No imports of application code, credentials, DB, Gold, network, or process actions.
Any missing/unknown/conflicting evidence refuses both final writes. Prior UNKNOWN
holds and STOP records remain unchanged; returned content is not a qualification.
"""
import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

W = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2")
R = W / "5703-failure-strata-checker-pair-20261008-02"
D = W / "5703-overall-answer-latency-pilot-20261006-01/cross-provider-checker-adaptation04"
E = Path(r"E:\5703\learning-assistant")
BUDGET_SHA = "a14c5a9c37429bb6597365cfa79d84d92b899f699bb00f5b8447ff3077a1b8e8"
HELPER_SHA = "bc63d57d84f56e1a44a8b454de6e65321196d77da5191bf5341dfafe4cbe28ec"
J20_SHA = "87f2cee42a4ebda26564eea793b6b06419c451b581253368139804ba4ad0be28"
F20_SHA = "e2b71bb8e663c87e81e40aa8ea2b3695e1804aadcba623f78cf4d36205676732"
TRANSFER_SHA = "328aef96e1c80dac73945f132d6ae612e17590f688b815649cfa3db1d56c03ce"
PROVENANCE = "ONLY_ORIGINAL38_UNSTARTED37_NO_BASELINE_RETRY"
GROUPS = {
    "checker_pair": {"slots": [2], "upper": Decimal("0.04956160"), "cap": 4096,
                     "nonce": "root-residual-checker-20261008-01", "release": "ROOT-checker_pair-release03.json",
                     "release_sha": "ba0de4690fe2d3c3309f9dba39db36a993f56f7a19c54baaa315024812af2161"},
    "quality_openqa": {"slots": list(range(1, 37)), "upper": Decimal("0.04124160"), "cap": 768,
                       "nonce": "root-residual-quality-20261008-01", "release": "ROOT-quality_openqa-release02.json",
                       "release_sha": "6473cfbf056829dbf9396c29045c54a9f55ddaabeb15686e73f3fa40fc978f80"},
}
PIN_FIELDS = ("path", "bytes", "sha256")
CELL_FIELDS = ("group", "slot", "wire_sha256", "wire_bytes", "output_cap", "input_tokens_bound")


def need(ok, message):
    if not ok:
        raise ValueError("STOP_NO_FINAL_LEDGER: " + message)


def path_guard(path, source=False):
    p = Path(path).absolute()
    anchor = E if source else W
    need(p.is_relative_to(anchor) and ".." not in p.parts, "path outside authorized public anchor")
    need(not any(x.lower() in {".git", ".aws", ".codex", ".agents", ".secrets", "gold", "sessions", "config-keys"}
                 for x in p.parts), "private path forbidden")
    need(p.suffix.lower() == ".py" if source else p.suffix.lower() not in {".db", ".sqlite", ".sqlite3"},
         "only public Python sources or W evidence permitted")
    for q in (anchor, *reversed(p.parents[:len(p.relative_to(anchor).parts)-1]), p):
        if q.exists():
            info = q.lstat()
            need(not q.is_symlink() and not getattr(info, "st_file_attributes", 0) &
                 getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024), "reparse path forbidden")
    return p


def pin(path, source=False):
    p = path_guard(path, source)
    raw = p.read_bytes()
    return {"path": str(p), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(path):
    p = path_guard(path)
    raw = p.read_bytes()
    return json.loads(raw), {"path": str(p), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def pinned(expected, checks, source=False):
    expected = {k: expected[k] for k in PIN_FIELDS}
    if source:
        need(pin(expected["path"], True) == expected, "current public source changed: " + expected["path"])
        checks.append((expected, True))
        return None
    value, actual = read(expected["path"])
    need(actual == expected, "pinned evidence changed: " + expected["path"])
    checks.append((actual, False))
    return value


def tracked(path, checks):
    value, actual = read(path)
    checks.append((actual, False))
    return value, actual


def amount(value):
    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("STOP_NO_FINAL_LEDGER: missing/invalid known fee") from exc
    need(value.is_finite() and value >= 0, "nonfinite/negative fee")
    return value


def money(value):
    return format(value, "f")


def write_new(path, value):
    p = path_guard(path)
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with p.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    expected = {"path": str(p), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    need(pin(p) == expected, "new artifact readback mismatch; retain partial artifact")
    return expected


def verify_sources(release, terminal, checks, quality_inputs=None):
    if quality_inputs is not None:
        sources = quality_inputs["source_pins"]
        need(len(sources) == 13, "quality source13 contract changed")
    else:
        manifest = pinned(release["current_source_manifest_pin"], checks)
        validators = pinned(release["validator_replay_evidence_pin"], checks)
        need(len(manifest["source_pins"]) == 17 and len(validators["source_pins"]) == 10,
             "checker source17/validator10 contract changed")
        sources = manifest["source_pins"] + validators["source_pins"]
        expected = {str(Path(x["path"]).relative_to(E)).replace("\\", "/"): x["sha256"] for x in sources}
        need(terminal.get("focused_source_unchanged") is True and terminal.get("source_pins") == expected,
             "checker terminal source bindings changed")
    for expected in sources:
        pinned(expected, checks, True)


def settled_group(group, budget, budget_pin, checks):
    spec = GROUPS[group]
    release, release_pin = tracked(R / spec["release"], checks)
    need(release_pin["sha256"] == spec["release_sha"], "release changed")
    need(release.get("schema") == "5703_successor38_group_release_v1" and
         release.get("status") == "ROOT_FROZEN_SUCCESSOR38_RELEASE" and release.get("group") == group and
         release.get("execution_nonce") == spec["nonce"] and release.get("budget_pin") == budget_pin and
         release.get("residual37_provenance") == PROVENANCE, "release admission mismatch")
    for key in ("residual37_transfer_pin", "prior_journal20_pin", "prior_finance20_pin", "old38_budget_pin",
                "predecessor_failed_baseline_receipt_pin"):
        need(release[key] == budget[key], "release predecessor mismatch: " + key)
    need(release["helper_pin"]["sha256"] == HELPER_SHA, "wrong residual guard")
    for expected in [release["executable_pin"], release["helper_pin"], *release["source_pins"]]:
        # Executable/helper are pinned bytes only; never import them.
        need(pin(expected["path"]) == {k: expected[k] for k in PIN_FIELDS}, "released public input changed")
        checks.append(({k: expected[k] for k in PIN_FIELDS}, False))
    cells = release["allowed_cells"]
    need([x["slot"] for x in cells] == spec["slots"] and len(cells) == len(spec["slots"]), "released slots changed")
    need(all(x["group"] == group and type(x["slot"]) is int and x["output_cap"] == spec["cap"] and
             type(x["wire_bytes"]) is int and x["wire_bytes"] > 0 and
             type(x["input_tokens_bound"]) is int and 0 < x["input_tokens_bound"] <= budget["maximum_input_tokens_per_call"]
             for x in cells), "released cell caps invalid")
    closure, closure_pin = tracked(R / ("ROOT-owned-" + spec["nonce"]) / "closure.json", checks)
    need(all(closure.get(k) is True for k in ("own_job_active_zero_verified", "process_handle_closed",
                                            "job_handle_closed", "memory_key_cleared")) and
         closure.get("cleanup_errors") == [] and type(closure.get("exit_code")) is int and closure["exit_code"] == 0,
         "owned process closure not clean")
    need(closure.get("release_sha256") == release_pin["sha256"] and
         closure.get("runner_sha256") == release["executable_pin"]["sha256"] and
         closure.get("fixture_key_injected") is True, "closure binding mismatch")
    output = R / (("actual-checker-pair-" if group == "checker_pair" else "actual-public-openqa36-") + spec["nonce"])
    terminal, terminal_pin = tracked(output / "terminal-receipt01.json", checks)
    need(terminal.get("release_pin") == release_pin and terminal.get("exit_code") == 0 and
         terminal.get("engine_disposed") is True and terminal.get("memory_key_references_cleared") is True,
         "actual terminal binding/cleanup mismatch")
    inputs = pinned(release["inputs_pin"], checks) if group == "quality_openqa" else None
    if inputs is not None:
        need(terminal.get("inputs_pin") == release["inputs_pin"] and
             terminal.get("status") == "ACTUAL_PUBLIC_MATCHED_OPENQA36_TERMINAL" and
             inputs["planned_count"] == terminal.get("planned_count") == 36, "quality terminal/input mismatch")
        plans = inputs["plans"]
        need(len(plans) == len(cells), "quality frozen plan count changed")
        for plan, cell in zip(plans, cells):
            need(plan["slot"] == cell["slot"] and plan["wire_sha256"] == cell["wire_sha256"] and
                 plan["wire_bytes"] == cell["wire_bytes"] and
                 plan["estimated_input_allowance"] == cell["input_tokens_bound"], "quality frozen wire mismatch")
    else:
        need(terminal.get("baseline_not_replayed") is True and terminal.get("valid_paired_latency_comparison") is False and
             terminal.get("execution_allowed_original_slots") == [2] and
             terminal.get("planned_physical_requests") == 1 and terminal.get("cleanup_errors") == [],
             "checker residual-only contract changed")
    verify_sources(release, terminal, checks, inputs)
    claim_root = path_guard(R / "new-residual37-claims" / group)
    expected_starts = {claim_root / f"slot-{s:02d}-started01.json" for s in spec["slots"]}
    need(set(claim_root.glob("*-started01.json")) == expected_starts, "missing/extra started claim")
    expected_observations = {output / ("concise-wire-observed01.json" if group == "checker_pair" else
                                     f"slot-{s:02d}-wire-observed01.json") for s in spec["slots"]}
    need(set(output.glob("*-wire-observed01.json")) == expected_observations, "missing/extra POST observation")
    expected_rows = {output / ("concise-finished01.json" if group == "checker_pair" else
                             f"slot-{s:02d}-finished01.json") for s in spec["slots"]}
    need(set(output.glob("*-finished01.json")) == expected_rows, "missing/extra local outcome")
    expected_finishes = {claim_root / f"slot-{s:02d}-finished01.json" for s in spec["slots"]}
    need(set(claim_root.glob("*-finished01.json")) == expected_finishes, "missing/extra immutable finish")
    result_cells, total = [], Decimal(0)
    for cell in cells:
        slot = cell["slot"]
        start, start_pin = tracked(claim_root / f"slot-{slot:02d}-started01.json", checks)
        need({k: start.get(k) for k in CELL_FIELDS} == {k: cell[k] for k in CELL_FIELDS} and
             start.get("nonce") == spec["nonce"] and start.get("release_pin") == release_pin and
             start.get("budget_sha256") == budget_pin["sha256"] and
             start.get("status") == "MAY_BE_SUBMITTED_NEVER_RETRY" and
             start.get("cell_key") == start.get("original38_cell_key") == f"{group}:{slot:02d}" and
             start.get("residual37_transfer_pin") == budget["residual37_transfer_pin"] and
             amount(start.get("submitted_upper_USD")) == spec["upper"], "immutable started cell mismatch")
        finish, finish_pin = tracked(claim_root / f"slot-{slot:02d}-finished01.json", checks)
        row_name = "concise-finished01.json" if group == "checker_pair" else f"slot-{slot:02d}-finished01.json"
        obs_name = "concise-wire-observed01.json" if group == "checker_pair" else f"slot-{slot:02d}-wire-observed01.json"
        row, row_pin = tracked(output / row_name, checks)
        obs, obs_pin = tracked(output / obs_name, checks)
        need(finish.get("started_pin") == start_pin and finish.get("status") == "KNOWN_COST_RECORDED" and
             amount(finish.get("UNKNOWN_full_hold_USD")) == 0, "missing/UNKNOWN/nonsettled shared finish")
        cost = amount(finish.get("known_API_cost_USD"))
        need(cost <= spec["upper"] and amount(row.get("usage", {}).get("cost")) == cost and
             amount(finish.get("usage", {}).get("cost")) == cost, "fee missing/conflicting/above reserved upper")
        need(row.get("slot") == slot and type(row.get("physical_POSTs")) is int and row["physical_POSTs"] == 1 and
             row.get("request_submitted") is True and obs.get("physical_POST_observed_before_transport") is True,
             "local/observed POST mismatch")
        need((obs.get("arm") == "concise") if group == "checker_pair" else obs.get("slot") == slot,
             "observation slot mismatch")
        for witness in (row, obs):
            need(witness.get("wire_sha256") == cell["wire_sha256"] and witness.get("wire_bytes") == cell["wire_bytes"],
                 "actual wire mismatch")
        need(finish.get("outcome") == (row.get("outcome") if group == "checker_pair" else row.get("status")),
             "local/shared outcome mismatch")
        need([x for x in terminal.get("rows", []) if x.get("slot") == slot] == [row],
             "terminal row differs from immutable local outcome")
        total += cost
        result_cells.append({"group": group, "slot": slot, "classification": "OBSERVED_POST_KNOWN_COST",
                             "known_API_cost_USD": money(cost), "outcome": finish["outcome"],
                             "started_pin": start_pin, "shared_finished_pin": finish_pin,
                             "local_outcome_pin": row_pin, "physical_observation_pin": obs_pin})
    count = len(result_cells)
    need(terminal.get("physical_requests" if group == "checker_pair" else "physical_calls") == count and
         len(terminal.get("rows", [])) == count and terminal.get("unstarted_count") == 0 and
         amount(terminal.get("known_cost_USD")) == total and amount(terminal.get("unknown_holds_USD")) == 0,
         "terminal/immutable financial counts mismatch")
    return {"group": group, "nonce": spec["nonce"], "group_execution_status": "ACTUAL_SETTLED_CLOSED",
            "owned_closure_pin": closure_pin, "release_pin": release_pin, "actual_terminal_receipt_pin": terminal_pin,
            "started_consumed_claims": count, "observed_physical_POSTs": count,
            "known_actual_POST_cost_calls": count, "UNKNOWN_actual_POST_cost_calls": 0,
            "known_actual_POST_API_cost_USD": money(total), "UNKNOWN_full_hold_USD": "0",
            "started_submitted_upper_USD": money(count * spec["upper"]), "cells": result_cells,
            "source_inputs_verified_current": True, "financial_reconciliation_only_not_science_qualification": True,
            "valid_paired_latency_comparison": False if group == "checker_pair" else None}


def main():
    checks = []
    journal_path, finance_path = D / "actual-spend-journal21.json", R / "actual-finance-projection21.json"
    need(not finance_path.exists() or journal_path.exists(), "projection without journal")
    old, old_pin = tracked(D / "actual-spend-journal20.json", checks)
    prior_finance, prior_finance_pin = tracked(R / "actual-finance-projection20.json", checks)
    budget, budget_pin = tracked(R / "ROOT-residual37-budget01.json", checks)
    need(old_pin["sha256"] == J20_SHA and prior_finance_pin["sha256"] == F20_SHA and
         budget_pin["sha256"] == BUDGET_SHA and prior_finance["journal_pin"] == old_pin and
         budget["prior_journal20_pin"] == old_pin and budget["prior_finance20_pin"] == prior_finance_pin,
         "exact predecessor/budget anchors changed")
    need((old["entire_project_physical_calls"], old["known_cost_calls"], old["unknown_cost_calls"]) == (165, 151, 14) and
         amount(old["known_API_cost_USD"]) == Decimal("0.467741750"), "prior counters changed")
    need(budget["schema"] == "5703_residual37_bounded_allocation_v1" and
         budget["maximum_new_physical_calls"] == 37 and
         amount(budget["maximum_new_submitted_upper_USD"]) == Decimal("1.53425920"), "residual capacity changed")
    transfer = pinned(budget["residual37_transfer_pin"], checks)
    need(budget["residual37_transfer_pin"]["sha256"] == TRANSFER_SHA and
         transfer["provenance"] == PROVENANCE and transfer["transferred_unstarted_count"] == 37 and
         transfer["old_baseline_slot01_consumed_forever"] is True and
         transfer["old_UNKNOWN_holds_and_all_STOPs_preserved"] is True, "transfer history changed")
    for key in ("old38_budget_pin", "prior38_STOP_pin", "prior38_baseline_started_pin", "prior38_baseline_finished_pin",
                "prior38_owned_closure_pin", "predecessor_failed_baseline_receipt_pin"):
        pinned(budget[key], checks)
    prior_sets = []
    for prefix, expected_count in (("prior42", 34), ("prior38", 1)):
        root = path_guard(budget[prefix + "_shared_claims_root"])
        current = sorted((pin(p) for p in root.rglob("*-started01.json")), key=lambda x: x["path"])
        need(len(current) == expected_count and current == budget[prefix + "_started_claim_pins"], "old claim set changed")
        need(hashlib.sha256(json.dumps(current, sort_keys=True, separators=(",", ":")).encode()).hexdigest() ==
             budget[prefix + "_claim_set_sha256"], "old claim digest changed")
        checks.extend((x, False) for x in current)
        prior_sets.append((root, current))
    groups = [settled_group(group, budget, budget_pin, checks) for group in GROUPS]
    claim_root = path_guard(R / "new-residual37-claims")
    need(not (claim_root / "STOP-before-any-next-submission01.json").exists(), "new phase STOP exists; settled-only refuses")
    starts = sorted(str(p) for p in claim_root.rglob("*-started01.json"))
    expected_starts = sorted(c["started_pin"]["path"] for g in groups for c in g["cells"])
    need(starts == expected_starts, "unexpected residual group/slot activity")
    new_posts = sum(g["observed_physical_POSTs"] for g in groups)
    new_known = sum((amount(g["known_actual_POST_API_cost_USD"]) for g in groups), Decimal(0))
    submitted = sum((amount(g["started_submitted_upper_USD"]) for g in groups), Decimal(0))
    need(new_posts == 37 and submitted == Decimal("1.53425920"), "incomplete settled37; refuse final ledger")
    old_follow = old["followup_20261008_01"]
    need((old_follow["attempted"], old_follow["known"], old_follow["unknown"], old_follow["consumed_claims"]) ==
         (35, 31, 4, 35) and amount(old_follow["UNKNOWN_submitted_hold_USD"]) == Decimal("0.19824640"),
         "old followup/UNKNOWN changed")
    prior_known = amount(old_follow["known_API_cost_USD"])
    held = amount(old_follow["UNKNOWN_submitted_hold_USD"])
    reserve = amount(prior_finance["new_reserve_retained_USD"])
    used = prior_known + new_known + held
    remaining = reserve - used
    need(reserve == Decimal("1.94000000") and remaining >= 0 and
         amount(prior_finance["old_protected_USD"]) == Decimal("8.03128969") and
         amount(prior_finance["combined_protected_USD"]) == Decimal("9.97128969"), "retained protection changed/exceeded")
    status = "ACTUAL_RESIDUAL37_SETTLED_CLOSED_RECONCILED_PRIOR_UNKNOWN_RETAINED_NO_RESERVE_RELEASE"
    existing = read(journal_path)[0] if journal_path.exists() else None
    phase = {"status": status, "schema": "5703_residual37_actual_reconciliation_v1", "budget_pin": budget_pin,
             "prior_journal20_pin": old_pin, "prior_finance20_pin": prior_finance_pin,
             "transfer_pin": budget["residual37_transfer_pin"], "old38_STOP_pin": budget["prior38_STOP_pin"],
             "predecessor_failed_baseline_receipt_pin": budget["predecessor_failed_baseline_receipt_pin"],
             "reconciliation_script_pin": pin(Path(__file__)), "groups": groups,
             "new_started_consumed_claims": new_posts, "new_observed_physical_POSTs": new_posts,
             "new_known_actual_POST_cost_calls": new_posts, "new_UNKNOWN_actual_POST_cost_calls": 0,
             "new_known_API_cost_USD": money(new_known), "new_started_submitted_upper_USD": money(submitted),
             "new_UNKNOWN_full_hold_USD": "0", "all37_residual_transports_settled": True,
             "valid_paired_latency_comparison": False, "native_publication_or_model_qualification": False,
             "all_prior_UNKNOWN_holds_retained": True, "all_old_STOPs_preserved": True,
             "provider_calls_by_reconciliation": 0, "E_files_written": 0, "invoice_or_account_balance": None,
             "reserve_release_USD": "0", "internal_remaining_after_actual_costs_and_full_holds_USD": money(remaining)}
    ledger = dict(old)
    ledger.update(status=status, at_UTC=existing["at_UTC"] if existing else datetime.now(timezone.utc).isoformat(),
                  prior_journal=old_pin, entire_project_physical_calls=old["entire_project_physical_calls"] + new_posts,
                  known_cost_calls=old["known_cost_calls"] + new_posts, unknown_cost_calls=old["unknown_cost_calls"],
                  known_API_cost_USD=money(amount(old["known_API_cost_USD"]) + new_known),
                  cumulative_claim_exposure_count=old["cumulative_claim_exposure_count"] + new_posts,
                  new_provider_calls_in_this_receipt=new_posts, residual37_20261008_03=phase,
                  unused_capacity_released_USD="0", invoice_USD=None, account_balance_USD=None)
    follow = dict(old_follow)
    follow.update(attempted=old_follow["attempted"] + new_posts, known=old_follow["known"] + new_posts,
                  consumed_claims=old_follow["consumed_claims"] + new_posts,
                  known_API_cost_USD=money(prior_known + new_known),
                  residual37_phase_namespace="residual37_20261008_03", released_USD="0")
    ledger["followup_20261008_01"] = follow
    need(ledger["known_cost_calls"] + ledger["unknown_cost_calls"] == ledger["entire_project_physical_calls"] <= 202 and
         follow["attempted"] <= 72 and 1 + new_posts <= 38, "aggregate physical ceilings exceeded")
    projection = dict(prior_finance)
    projection.update(status=status, at_UTC=ledger["at_UTC"], prior_journal20_pin=old_pin,
                      prior_finance20_pin=prior_finance_pin, residual37_20261008_03=phase,
                      cumulative_physical_calls=ledger["entire_project_physical_calls"],
                      cumulative_known_calls=ledger["known_cost_calls"], cumulative_UNKNOWN_calls=ledger["unknown_cost_calls"],
                      cumulative_known_API_cost_USD=ledger["known_API_cost_USD"],
                      cumulative_claim_exposure_count=ledger["cumulative_claim_exposure_count"],
                      followup_physical_calls=follow["attempted"], followup_consumed_claims=follow["consumed_claims"],
                      followup_known_calls=follow["known"], followup_UNKNOWN_calls=follow["unknown"],
                      followup_known_API_cost_USD=follow["known_API_cost_USD"], followup_UNKNOWN_hold_USD=money(held),
                      actual_started_submitted_upper_USD=money(amount(prior_finance["actual_started_submitted_upper_USD"]) + submitted),
                      residual37_budget_pin=budget_pin,
                      actual_claim_group_counts={g["group"]: prior_finance["actual_claim_group_counts"][g["group"]] +
                                                 g["started_consumed_claims"] for g in groups},
                      actual_observed_POST_group_counts={g["group"]: prior_finance["actual_observed_POST_group_counts"][g["group"]] +
                                                         g["observed_physical_POSTs"] for g in groups},
                      groups=groups, groups_verified_unstarted_without_launch=[], all38_planned_calls_complete=True,
                      internal_remaining_after_actual_costs_and_full_holds_USD=money(remaining),
                      valid_paired_latency_comparison=False, original_failed_baseline_UNKNOWN_not_retried=True,
                      invoice_or_account_balance=None, reserve_release_USD="0")
    # Recheck all pinned bytes, current sources and claim sets before each final write.
    def final_check():
        for expected, source in checks:
            need(pin(expected["path"], source) == expected, "evidence changed during reconciliation")
        need(sorted(str(p) for p in claim_root.rglob("*-started01.json")) == expected_starts and
             not (claim_root / "STOP-before-any-next-submission01.json").exists(), "late residual activity/STOP")
        for root, previous in prior_sets:
            current = sorted((pin(p) for p in root.rglob("*-started01.json")), key=lambda x: x["path"])
            need(current == previous, "old claim set changed before final write")
    final_check()
    if existing is None:
        journal_pin = write_new(journal_path, ledger)
    else:
        need(existing == ledger, "existing immutable J21 differs; no overwrite/delete/rollback")
        journal_pin = pin(journal_path)
    projection["journal_pin"] = journal_pin
    final_check()
    if finance_path.exists():
        actual, finance_pin = read(finance_path)
        need(actual == projection, "existing immutable finance21 differs; retain both artifacts")
    else:
        finance_pin = write_new(finance_path, projection)
    print(json.dumps({"status": status, "journal_pin": journal_pin, "projection_pin": finance_pin,
                      "new_observed_POSTs": new_posts, "new_known_API_cost_USD": money(new_known),
                      "all_prior_UNKNOWN_holds_retained": True, "reserve_release_USD": "0"}))


if __name__ == "__main__":
    main()
