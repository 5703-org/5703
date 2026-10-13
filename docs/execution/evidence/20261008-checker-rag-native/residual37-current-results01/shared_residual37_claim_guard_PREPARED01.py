"""PREPARED residual37 claim guard; closed predecessor STOP and UNKNOWN preserved. Imports perform no writes or transport.

Root must adopt a hash-pinned group release before Guard can claim. A started
claim is an irreversible consumed physical slot, including after a crash.
"""
import hashlib
import json
import msvcrt
import os
import re
import stat
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

W = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2")
R = W / "5703-failure-strata-checker-pair-20261008-02"
GROUPS = {"checker_pair": (2, 4096, Decimal("0.04956160")),
          "quality_openqa": (36, 768, Decimal("0.04124160"))}
HEX = re.compile(r"^[0-9a-f]{64}$")


class GuardError(RuntimeError):
    pass


def _need(ok, message):
    if not ok:
        raise GuardError(message)


def _ordinary(path, *, must_exist=True):
    p = Path(path).absolute()
    _need(p.is_relative_to(W), "path outside authorized W")
    for part in p.relative_to(W).parts:
        _need(part != "..", "parent traversal forbidden")
        _need(part.lower() not in {".git", ".agents", ".codex", ".aws", "sessions", "sessionsdirs"},
              "private/session path forbidden")
    _need(p.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}, "database path forbidden")
    for ancestor in [W, *reversed(p.parents[:len(p.relative_to(W).parts)-1]), p]:
        if ancestor.exists():
            st = ancestor.lstat()
            _need(not ancestor.is_symlink() and not getattr(st, "st_file_attributes", 0) &
                  getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024), "reparse path forbidden")
    if must_exist:
        _need(p.exists(), "missing pinned path: " + str(p))
    return p


def _pin(path):
    p = _ordinary(path)
    _need(p.is_file(), "pin is not a file")
    b = p.read_bytes()
    return {"path": str(p), "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def _verify_pin(pin):
    _need(isinstance(pin, dict) and set(pin) >= {"path", "bytes", "sha256"}, "invalid pin")
    _need(type(pin["bytes"]) is int and pin["bytes"] >= 0 and
          HEX.fullmatch(str(pin["sha256"])), "invalid pin metadata")
    actual = _pin(pin["path"])
    _need(actual == {k: pin[k] for k in ("path", "bytes", "sha256")}, "changed pin: " + pin["path"])
    return Path(pin["path"])


def _read_pinned(pin):
    # Parse the same bytes whose metadata/hash were verified (no second read).
    p = _ordinary(pin["path"])
    raw = p.read_bytes()
    _need({"path": str(p), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} ==
          {k: pin[k] for k in ("path", "bytes", "sha256")}, "changed parsed pin")
    return json.loads(raw)


def _field(value, key):
    for part in key.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def _load(path):
    return json.loads(_ordinary(path).read_bytes())


def _decimal(value):
    try:
        n = Decimal(str(value))
    except InvalidOperation as exc:
        raise GuardError("invalid monetary value") from exc
    _need(n.is_finite() and n >= 0, "invalid monetary value")
    return n


def _money(n):
    return format(n, ".8f")


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _create_json(path, value):
    p = _ordinary(path, must_exist=False)
    _need(p.parent.is_dir(), "missing claim parent")
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    with p.open("xb") as stream:  # O_EXCL / CreateNew: never replace a claim.
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return _pin(p)


def _claim_set(root):
    return sorted((_pin(p) for p in _ordinary(root).rglob("*-started01.json")), key=lambda p: p["path"])


def _set_hash(pins):
    return hashlib.sha256(json.dumps(pins, sort_keys=True, separators=(",", ":")).encode()).hexdigest()



# Only original38 cells that journal20 proves unstarted can enter this phase.
GROUPS = {"checker_pair": (1, 4096, Decimal("0.04956160")),
          "quality_openqa": (36, 768, Decimal("0.04124160"))}
ALLOWED_SLOTS = {"checker_pair": (2,), "quality_openqa": tuple(range(1, 37))}
PROVENANCE = "ONLY_ORIGINAL38_UNSTARTED37_NO_BASELINE_RETRY"


class Guard:
    def __init__(self, budget_path, expected_budget_sha256, release_path, expected_release_sha256):
        self.budget_path, self.release_path = _ordinary(budget_path), _ordinary(release_path)
        self.budget_sha256, self.release_sha256 = str(expected_budget_sha256), str(expected_release_sha256)
        _need(HEX.fullmatch(self.budget_sha256) and HEX.fullmatch(self.release_sha256), "exact Root hashes required")
        self.budget = _read_pinned({**_pin(self.budget_path), "sha256": self.budget_sha256})
        self.root = _ordinary(self.budget["new_shared_claims_root"], must_exist=False)
        _need(self.root == R / "new-residual37-claims", "wrong residual claim root")
        self.stop_path = self.root / "STOP-before-any-next-submission01.json"
        self._verify_static()

    def _cells(self, release):
        _need(release["schema"] == "5703_successor38_group_release_v1" and
              release["status"] == "ROOT_FROZEN_SUCCESSOR38_RELEASE" and release["group"] in GROUPS,
              "exact adopted group release required")
        b = self.budget
        _need(release["residual37_provenance"] == PROVENANCE, "residual provenance required")
        for key in ("residual37_transfer_pin", "prior_journal20_pin", "prior_finance20_pin", "old38_budget_pin"):
            _need(release[key] == b[key], "release predecessor pin differs: " + key)
        _need(release["predecessor_failed_baseline_receipt_pin"] ==
              b["predecessor_failed_baseline_receipt_pin"], "failed baseline binding differs")
        _need(release["budget_pin"] == _pin(self.budget_path) and
              release["helper_pin"] == _pin(Path(__file__).absolute()), "release budget/helper differs")
        _need(isinstance(release["execution_nonce"], str) and
              re.fullmatch(r"[a-z0-9_-]{12,64}", release["execution_nonce"]), "fresh nonce required")
        group = release["group"]
        cells = release["allowed_cells"]
        _need(type(cells) is list and len(cells) == GROUPS[group][0], "exact group cell count required")
        result = {}
        for cell in cells:
            _need(type(cell) is dict and set(cell) == {"group", "slot", "wire_sha256", "wire_bytes",
                  "output_cap", "input_tokens_bound"}, "exact wire-bound cell shape required")
            slot = cell["slot"]
            _need(cell["group"] == group and type(slot) is int and slot in ALLOWED_SLOTS[group] and
                  slot not in result, "untransferred or duplicate cell")
            _need(HEX.fullmatch(str(cell["wire_sha256"])) and type(cell["wire_bytes"]) is int and
                  cell["wire_bytes"] > 0 and cell["output_cap"] == GROUPS[group][1] and
                  type(cell["input_tokens_bound"]) is int and 1 <= cell["input_tokens_bound"] and
                  cell["input_tokens_bound"] + cell["output_cap"] <= 131072, "changed wire/token cap")
            result[slot] = cell
        _need(set(result) == set(ALLOWED_SLOTS[group]), "only exact transferred cells permitted")
        return result

    def _verify_static(self):
        b = _read_pinned({**_pin(self.budget_path), "sha256": self.budget_sha256})
        _need(b == self.budget, "residual budget changed")
        _need(b["schema"] == "5703_residual37_bounded_allocation_v1" and
              b["status"] == "PREPARED_RESIDUAL37_REQUIRES_ROOT_RELEASE_NOT_EXECUTION", "wrong residual budget")
        _need((b["maximum_new_physical_calls"], b["original38_consumed_calls"],
               b["original38_total_physical_ceiling"], b["aggregate_followup_physical_ceiling"],
               b["aggregate_project_physical_ceiling"]) == (37, 1, 38, 72, 202), "changed physical caps")
        fixed_money = {"authorization_total_USD": "10.00000000", "new_reserve_retained_USD": "1.94000000",
                       "old_protected_USD": "8.03128969", "combined_protected_USD": "9.97128969",
                       "unallocated_USD": "0.02871031", "prior_known_API_cost_USD": "0.05677010",
                       "prior_UNKNOWN_full_hold_USD": "0.19824640",
                       "baseline_UNKNOWN_full_hold_USD": "0.04956160",
                       "maximum_new_submitted_upper_USD": "1.53425920",
                       "original38_maximum_submitted_upper_USD": "1.58382080",
                       "remaining_worst_case_USD": "0.15072430", "reserve_release_USD": "0"}
        _need(all(b[key] == value for key, value in fixed_money.items()), "changed protection or reserve")
        _need(b["model"] == "google/gemini-3.5-flash-lite" and b["provider_route"] == "google-vertex/global" and
              b["allow_fallbacks"] is False and b["require_parameters"] is True and
              b["maximum_input_tokens_per_call"] == 131072 and
              b["price_caps_USD_per_million"] == {"prompt": "0.30", "completion": "2.50"}, "changed route/caps")
        _need(set(b["groups"]) == set(GROUPS), "unapproved group")
        for group, (calls, output, upper) in GROUPS.items():
            _need(b["groups"][group] == {"maximum_calls": calls, "allowed_slots": list(ALLOWED_SLOTS[group]),
                  "output_cap": output, "upper_per_call_USD": _money(upper)}, "changed residual group")
        for pin in [b["old38_budget_pin"], b["prior_journal20_pin"], b["prior_finance20_pin"],
                    b["residual37_transfer_pin"], b["prior38_STOP_pin"], b["prior38_baseline_started_pin"],
                    b["prior38_baseline_finished_pin"], b["predecessor_failed_baseline_receipt_pin"],
                    b["prior38_owned_closure_pin"], *b["preserved_evidence_pins"], *b["local_source_pins"]]:
            _verify_pin(pin)
        old = _read_pinned(b["old38_budget_pin"])
        _need(old["schema"] == "5703_successor38_bounded_allocation_v1" and
              old["maximum_new_physical_calls"] == 38 and old["aggregate_project_physical_ceiling"] == 202 and
              old["prior_started_claim_pins"] == b["prior42_started_claim_pins"] and
              old["prior_claim_set_sha256"] == b["prior42_claim_set_sha256"] and
              old["required_old_worker_closure_checks"] == b["historical_worker_closure_checks"],
              "old38 immutable contract differs")
        _need(b["prior42_shared_claims_root"] == old["prior_shared_claims_root"] and
              b["prior42_global_lock_pin"] == old["prior_global_lock_pin"] and
              b["prior38_shared_claims_root"] == str(R / "new-batch38-claims") and
              b["prior38_global_lock_pin"]["path"] == str(R / "new-batch38-claims/global38-budget.lock") and
              b["prior38_started_claim_pins"] == [b["prior38_baseline_started_pin"]] and
              b["required_old_worker_closure_checks"] ==
              [*b["historical_worker_closure_checks"], b["baseline_worker_closure_check"]],
              "historical roots/locks/35 snapshots/closures differ")
        transfer = _read_pinned(b["residual37_transfer_pin"])
        _need(transfer["schema"] == "5703_prior38_unstarted37_transfer_v1" and
              transfer["status"] == "PREPARED_TRANSFER_ONLY_UNSTARTED37_REQUIRES_ROOT_RELEASE" and
              transfer["provenance"] == PROVENANCE and transfer["transferred_unstarted_count"] == 37 and
              transfer["new_shared_claims_root"] == str(self.root) and
              transfer["allowed_original_cells"] ==
              [{"group": g, "slot": s} for g in GROUPS for s in ALLOWED_SLOTS[g]], "changed transfer")
        for key in ("old38_budget_pin", "prior_journal20_pin", "prior_finance20_pin", "prior38_STOP_pin",
                    "prior38_baseline_started_pin", "prior38_baseline_finished_pin"):
            _need(transfer[key] == b[key], "transfer predecessor differs")
        j = _read_pinned(b["prior_journal20_pin"])
        _need((j["entire_project_physical_calls"], j["known_cost_calls"], j["unknown_cost_calls"],
               _decimal(j["known_API_cost_USD"]), j["cumulative_claim_exposure_count"],
               j["potential_unobserved_call_exposure_count"]) ==
              (165, 151, 14, Decimal("0.467741750"), 165, 0), "journal20 totals differ")
        f = j["followup_20261008_01"]
        _need((f["attempted"], f["known"], f["unknown"], f["consumed_claims"],
               _decimal(f["known_API_cost_USD"]), _decimal(f["UNKNOWN_submitted_hold_USD"])) ==
              (35, 31, 4, 35, Decimal("0.05677010"), Decimal("0.19824640")), "followup35 differs")
        finance = _read_pinned(b["prior_finance20_pin"])
        _need(finance["journal_pin"] == b["prior_journal20_pin"] and
              finance["actual_claim_group_counts"] == {"checker_pair": 1, "quality_openqa": 0} and
              finance["terminal_and_shared_finance_consistent"] is True and
              finance["actual_cost_bound_violation_requires_STOP"] is False and
              finance["old_UNKNOWN_and_STOP_preserved"] is True and
              _decimal(finance["internal_remaining_after_actual_costs_and_full_holds_USD"]) ==
              Decimal("1.68498350"), "finance20 safety differs")
        phase = j["successor38_20261008_02"]
        _need(phase["shared_STOP_pin"] == b["prior38_STOP_pin"] and
              phase["budget_pin"] == b["old38_budget_pin"] and
              phase["new_started_consumed_claims"] == 1 and
              phase["new_observed_physical_POSTs"] == 1 and
              phase["new_UNKNOWN_actual_POST_cost_calls"] == 1 and
              phase["potential_unobserved_call_exposure_count"] == 0 and
              phase["all_prior_UNKNOWN_holds_retained"] is True, "closed predecessor phase differs")
        checker = [g for g in phase["groups"] if g["group"] == "checker_pair"]
        quality = [g for g in phase["groups"] if g["group"] == "quality_openqa"]
        _need(len(checker) == 1 and len(quality) == 1 and
              checker[0]["owned_closure_pin"] == b["prior38_owned_closure_pin"] and
              checker[0]["cells"][0]["started_pin"] == b["prior38_baseline_started_pin"] and
              checker[0]["cells"][0]["shared_finished_pin"] == b["prior38_baseline_finished_pin"] and
              checker[0]["cells"][0]["local_outcome_pin"] == b["predecessor_failed_baseline_receipt_pin"] and
              quality[0]["started_consumed_claims"] == 0 and
              quality[0]["observed_physical_POSTs"] == 0 and
              quality[0]["unstarted_new_group_slots"] == 36, "only old concise+36 quality may transfer")
        stopped = _read_pinned(b["prior38_STOP_pin"])
        _need(stopped["status"] == "STOP_NO_NEXT_SUBMISSION" and
              stopped["budget_sha256"] == b["old38_budget_pin"]["sha256"] and
              stopped["UNKNOWN_holds_retained_in_full"] is True, "historical STOP must remain")
        baseline = _read_pinned(b["prior38_baseline_finished_pin"])
        _need(baseline["status"] == "UNKNOWN_FULL_HOLD_STOP" and baseline["known_API_cost_USD"] is None and
              baseline["started_pin"] == b["prior38_baseline_started_pin"] and
              _decimal(baseline["UNKNOWN_full_hold_USD"]) == Decimal("0.04956160"), "baseline UNKNOWN changed")
        release = _read_pinned({**_pin(self.release_path), "sha256": self.release_sha256})
        self.release_cells = self._cells(release)
        _verify_pin(release["executable_pin"])
        _need(Path(release["executable_pin"]["path"]) == Path(sys.argv[0]).absolute(), "wrong released executable")
        _need(release["source_pins"] and release["old_workers_closure_checks"], "source/closure pins required")
        for pin in release["source_pins"]:
            _verify_pin(pin)
        for check in b["required_old_worker_closure_checks"]:
            _need(check in release["old_workers_closure_checks"], "missing historical closure contract")
        for check in release["old_workers_closure_checks"]:
            receipt = _read_pinned(check["pin"])
            _need(check["expected_type"] == "bool" and check["expected_value"] is True and
                  _field(receipt, check["active_count_key"]) is True, "old job active-zero unproved")
            _need(all(_field(receipt, k) is True for k in check["required_true_keys"]), "old handles not closed")
            _need(all(type(_field(receipt, k)) is list and not _field(receipt, k)
                      for k in check["required_empty_keys"]), "old cleanup error")
        self.release = release

    @contextmanager
    def _locks(self):
        self.root.mkdir(exist_ok=True)
        _ordinary(self.root)
        new_lock = self.root / "global37-budget.lock"
        try:
            with new_lock.open("xb") as stream:
                stream.write(b"0")
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            pass
        _need(_ordinary(new_lock).read_bytes() == b"0", "invalid new37 lock")
        pins = [self.budget["prior42_global_lock_pin"], self.budget["prior38_global_lock_pin"]]
        paths = [_verify_pin(pin) for pin in pins] + [new_lock]
        opened = []
        try:
            for path in paths:  # One invariant order: old42 -> old38 -> new37.
                stream = path.open("r+b")
                try:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                except Exception:
                    stream.close()
                    raise GuardError("exclusive global lock unavailable")
                opened.append(stream)
            # Mandatory Windows locks: hash held streams, never reopen a locked byte.
            for stream, expected in zip(opened[:2], pins):
                stream.seek(0)
                raw = stream.read(2)
                _need(raw == b"0" and os.fstat(stream.fileno()).st_size == 1 and
                      hashlib.sha256(raw).hexdigest() == expected["sha256"], "old lock bytes changed")
            yield
        finally:
            for stream in reversed(opened):
                try:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                finally:
                    stream.close()

    def _verify_prior(self):
        for label in ("prior42", "prior38"):
            expected = self.budget[label + "_started_claim_pins"]
            root = _ordinary(self.budget[label + "_shared_claims_root"])
            paths = sorted(str(p) for p in root.rglob("*-started01.json"))
            _need(paths == sorted(pin["path"] for pin in expected), "historical consumed set changed")
            pins = sorted((_pin(path) for path in paths), key=lambda p: p["path"])
            _need(pins == expected and _set_hash(pins) == self.budget[label + "_claim_set_sha256"],
                  "historical started snapshot changed")
        _verify_pin(self.budget["prior38_STOP_pin"])
        _verify_pin(self.budget["prior38_baseline_finished_pin"])

    def _tally(self):
        counts = {group: 0 for group in GROUPS}
        bound = actual = unknown = Decimal(0)
        open_claims, stop_receipts = [], 0
        allowed_paths = {self.root / g / f"slot-{s:02d}-started01.json"
                         for g in GROUPS for s in ALLOWED_SLOTS[g]}
        paths = sorted(self.root.rglob("*-started01.json"))
        _need(len(paths) <= 37 and all(p in allowed_paths for p in paths), "foreign or baseline cell")
        for path in paths:
            start = _load(path)
            group, slot = start["group"], start["slot"]
            _need(group in GROUPS and type(slot) is int and slot in ALLOWED_SLOTS[group] and
                  start["budget_sha256"] == self.budget_sha256 and
                  path == self.root / group / f"slot-{slot:02d}-started01.json", "foreign started claim")
            upper = GROUPS[group][2]
            _need(start["original38_cell_key"] == f"{group}:{slot:02d}" and
                  start["cell_key"] == start["original38_cell_key"] and
                  start["residual37_transfer_pin"] == self.budget["residual37_transfer_pin"] and
                  _decimal(start["submitted_upper_USD"]) == upper, "altered transferred identity/bound")
            claimed_release = _read_pinned(start["release_pin"])
            cell = self._cells(claimed_release)[slot]
            _need(claimed_release["group"] == group and claimed_release["execution_nonce"] == start["nonce"] and
                  all(start[k] == cell[k] for k in cell), "claim wire differs from frozen release")
            counts[group] += 1
            bound += upper
            finished = path.with_name(f"slot-{slot:02d}-finished01.json")
            if not finished.exists():
                open_claims.append(start)
                unknown += upper
            else:
                finish = _load(finished)
                _need(finish["started_pin"] == _pin(path), "finish does not bind start")
                cost = finish["known_API_cost_USD"]
                if cost is None:
                    unknown += upper
                    stop_receipts += 1
                else:
                    observed = _decimal(cost)
                    actual += observed  # Preserve a true reported cost even above its bound.
                    if observed > upper or str(finish["outcome"]).startswith("STOP_"):
                        stop_receipts += 1
        _need(all(counts[g] <= GROUPS[g][0] for g in GROUPS), "residual cap exceeded")
        unstarted = sum((GROUPS[g][0] - counts[g]) * GROUPS[g][2] for g in GROUPS)
        planned_worst = Decimal("0.25501650") + bound + unstarted
        _need(planned_worst == Decimal("1.78927570"), "remaining allocation changed")
        current_worst = Decimal("0.25501650") + actual + unknown + unstarted
        return {"counts": counts, "new_started_calls": sum(counts.values()),
                "new_started_full_bounds_USD": _money(bound), "unstarted_maximum_USD": _money(unstarted),
                "prior_known_plus_UNKNOWN_USD": "0.25501650",
                "worst_with_unstarted_USD": _money(current_worst),
                "maximum_planned_with_unstarted_USD": _money(planned_worst),
                "retained_reserve_USD": "1.94000000",
                "remaining_worst_case_USD": _money(Decimal("1.94000000") - current_worst),
                "new_known_receipt_cost_USD": _money(actual),
                "new_UNKNOWN_or_inflight_hold_USD": _money(unknown),
                "open_claims": open_claims, "stop_receipts": stop_receipts,
                "actual_cost_exceeds_retained_reserve": current_worst > Decimal("1.94000000")}

    def _stop_locked(self, reason):
        if not self.stop_path.exists():
            _create_json(self.stop_path, {"status": "STOP_NO_NEXT_SUBMISSION", "at_UTC": _utc(),
                         "reason": str(reason), "budget_sha256": self.budget_sha256,
                         "UNKNOWN_holds_retained_in_full": True, "old_files_written": 0})

    def stop(self, reason):
        with self._locks():
            self._stop_locked(reason)
        return _pin(self.stop_path)

    def claim(self, group, slot, nonce, *, wire_sha256, wire_bytes, output_cap, input_tokens_bound):
        with self._locks():
            self._verify_static()
            self._verify_prior()
            _need(not self.stop_path.exists(), "residual phase STOP already exists")
            _need(group == self.release["group"] and nonce == self.release["execution_nonce"], "wrong released group")
            candidate = {"group": group, "slot": slot, "wire_sha256": wire_sha256, "wire_bytes": wire_bytes,
                         "output_cap": output_cap, "input_tokens_bound": input_tokens_bound}
            _need(type(slot) is int and candidate == self.release_cells.get(slot), "unreleased wire/cell; baseline forbidden")
            before = self._tally()
            _need(not before["open_claims"] and before["stop_receipts"] == 0 and
                  not before["actual_cost_exceeds_retained_reserve"], "unfinished/STOP receipt forbids next submission")
            _need(before["new_started_calls"] < 37 and
                  35 + before["new_started_calls"] + 1 <= 72 and
                  165 + before["new_started_calls"] + 1 <= 202 and
                  1 + before["new_started_calls"] + 1 <= 38, "aggregate physical ceiling")
            parent = self.root / group
            parent.mkdir(exist_ok=True)
            _ordinary(parent)
            path = parent / f"slot-{slot:02d}-started01.json"
            _need(not path.exists(), "original cell consumed forever")
            start = {**candidate, "status": "MAY_BE_SUBMITTED_NEVER_RETRY", "at_UTC": _utc(),
                     "cell_key": f"{group}:{slot:02d}", "original38_cell_key": f"{group}:{slot:02d}",
                     "nonce": nonce, "budget_sha256": self.budget_sha256,
                     "release_pin": _pin(self.release_path),
                     "residual37_transfer_pin": self.budget["residual37_transfer_pin"],
                     "submitted_upper_USD": _money(GROUPS[group][2]), "provider_route": "google-vertex/global",
                     "before_hold_tally": {k: v for k, v in before.items() if k != "open_claims"},
                     "old35_and_all_STOPs_preserved": True}
            start_pin = _create_json(path, start)
            after = self._tally()
            _need(after["new_started_calls"] == before["new_started_calls"] + 1, "claim readback mismatch")
            return {**start, "started_pin": start_pin}

    def finish(self, start, *, known_cost_USD, outcome, usage=None):
        with self._locks():
            self._verify_static()
            self._verify_prior()
            path = _verify_pin(start["started_pin"])
            saved = _read_pinned(start["started_pin"])
            _need(saved == {k: v for k, v in start.items() if k != "started_pin"}, "start mismatch")
            _need(saved["group"] == self.release["group"] and saved["nonce"] == self.release["execution_nonce"] and
                  saved["budget_sha256"] == self.budget_sha256 and
                  saved["slot"] in ALLOWED_SLOTS[saved["group"]] and
                  path == self.root / saved["group"] / f"slot-{saved['slot']:02d}-started01.json" and
                  saved["release_pin"] == _pin(self.release_path), "foreign finish")
            upper = _decimal(saved["submitted_upper_USD"])
            cost = None if known_cost_USD is None else _decimal(known_cost_USD)
            over = cost is not None and cost > upper
            finish_path = path.with_name(f"slot-{saved['slot']:02d}-finished01.json")
            _need(not finish_path.exists(), "finish is immutable")
            receipt = {"status": "UNKNOWN_FULL_HOLD_STOP" if cost is None else
                       "KNOWN_COST_EXCEEDS_BOUND_STOP" if over else "KNOWN_COST_RECORDED",
                       "at_UTC": _utc(), "started_pin": start["started_pin"], "outcome": str(outcome),
                       "known_API_cost_USD": None if cost is None else str(cost),
                       "UNKNOWN_full_hold_USD": _money(upper) if cost is None else "0.00000000",
                       "usage": usage, "invoice_or_account_balance": None}
            finish_pin = _create_json(finish_path, receipt)  # Persist actual cost BEFORE any STOP/throw.
            if cost is None or over or str(outcome).startswith("STOP_"):
                self._stop_locked(receipt["status"] + ":" + str(outcome))
            tally = self._tally()
            if tally["actual_cost_exceeds_retained_reserve"]:
                self._stop_locked("ACTUAL_COST_EXCEEDS_RETAINED_RESERVE")
            result = {**receipt, "finished_pin": finish_pin,
                      "immediate_tally": {k: v for k, v in tally.items() if k != "open_claims"},
                      "must_stop": self.stop_path.exists()}
            if over:
                raise GuardError("known cost exceeds bound; receipt retained and residual phase stopped")
            return result


