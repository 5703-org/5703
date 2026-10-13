"""Root-owned Phase89 static freeze/preparation; no credentials, service or model calls."""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import copy
import hashlib
import json
import os
import sys

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / "5703-checker88-runtime"
AUTH = "parent_dev89_independent32posts_2USD_quality_pages_20261012"
TEMPLATE_SHA256 = "8a92770cffda58f62d9fa3bd444eda9267255fcd6359a4c6f3208b9a4e42cd24"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def create(path, value):
    with Path(path).open("xb") as stream:
        stream.write((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


def _template():
    """Read only the exact public stable scope; historical records are not re-certified."""
    path = PREVIOUS / "scope88-case10b.json"
    assert path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    assert sha(raw) == TEMPLATE_SHA256
    return json.loads(raw)


def freeze_protocol(public_manifest_path):
    """Freeze one complete reviewed public manifest; rubrics are never read by this helper."""
    import budget88
    path = Path(public_manifest_path).absolute()
    assert path.is_file() and not path.is_symlink() and path.resolve() == path
    raw = path.read_bytes()
    protocol = budget88.validate_protocol(json.loads(raw))
    assert all(not (HERE / name).exists() and not (HERE / name).is_symlink()
               for name in ("protocol88.json", "runtime-freeze88.json", "cohort-ledger"))
    _template()
    with (HERE / "protocol88.json").open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    pin = sha(raw)
    create(HERE / "runtime-freeze88.json", {
        "schema": "dev89_runtime_freeze_v1", "authorization": AUTH,
        "protocol_sha256": pin, "shared_public_source_boundary_sha256": protocol["public_source_boundary_sha256"],
        "source_version_sha256": protocol["source_version_sha256"], "base_config_sha256": protocol["base_config_sha256"],
        "old_ledgers_mutated": False, "actual_claims": 0, "provider_posts": 0})
    return {"protocol_sha256": pin, "cases": [row["case_id"] for row in protocol["cases"]]}


def _protocol():
    import budget88
    path = HERE / "protocol88.json"
    assert path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    protocol = budget88.validate_protocol(json.loads(raw))
    freeze = json.loads((HERE / "runtime-freeze88.json").read_bytes())
    assert sha(raw) == freeze["protocol_sha256"] and freeze["authorization"] == AUTH
    assert freeze["source_version_sha256"] == protocol["source_version_sha256"]
    assert freeze["base_config_sha256"] == protocol["base_config_sha256"]
    return protocol, sha(raw)


def _build_scope(protocol, protocol_pin, row, case_id, *, source_pins=None):
    """Copy public fixture bindings, with only finite instance metadata and owned storage rebased."""
    scope = copy.deepcopy(_template())
    obsolete = {"supplement_descriptor_sha256", "checker_high_manifest_sha256", "checker_high8192_manifest_sha256",
        "fresh_validation_descriptor_sha256", "fresh_preparation_source_pins", "fresh_public_question_file_sha256",
        "zero_post_reconciliation_path", "zero_post_reconciliation_sha256", "page_base_checker_config_sha256",
        "page_answer_requires_independent_quality_review"}
    for key in list(scope):
        if key in obsolete or key.startswith("phase88_") or key.startswith("phase87_"):
            del scope[key]
    planned = next(item for item in protocol["planned_instances"] if item["instance_id"] == case_id)
    scope.update(case_id=case_id, question_id=row["question_id"], question_text=row["question_text"],
        question_sha256=row["question_sha256"], question_descriptor_sha256=row["question_sha256"],
        phase88_authorization=AUTH, phase88_case_execution_authorized=True,
        phase89_planned_kind=planned["kind"], phase89_frozen_profile_sha256=protocol["base_config_sha256"],
        cohort_protocol_sha256=protocol_pin, continuation_phase="dev89", api_origin="http://127.0.0.1:18029",
        started_at_UTC=datetime.now(timezone.utc).isoformat(),
        expected_model_config=copy.deepcopy(protocol["expected_model_config"]),
        expected_checker_config=copy.deepcopy(protocol["expected_checker_config"]),
        source_pins=copy.deepcopy(protocol["source_pins"] if source_pins is None else source_pins))
    scope["expected_settings"] = {**copy.deepcopy(protocol["frozen_settings"]),
        "storage_root": str(HERE / case_id / "storage"),
        "visual_catalog_staging_root": str(HERE / case_id / "visual-staging")}
    if protocol["default_output_policy"] == "single_selection_findings_v2":
        scope["phase88_checker_output_variant"] = "single_selection_findings_v2"
        scope["phase88_v2_execution_authorized"] = True
    scope["root_binding_targets"] = [
        "Original isolated synthetic fixture and normal API; memory-only credentials",
        "Same frozen stable teacher4096 and checker HIGH8192, full original source packet and release",
        "Original eight baseline cases retain one immutable sixteen-file Main source version",
        "Independent shared32POST/USD2; two pages retain eight POST headroom; each instance at most four calls",
        "No HTTP retry, old claim reuse, full-batch replay, checker LOW activation or automatic page entitlement"]
    return scope


def _write_scope(case_id, scope, protocol, protocol_pin):
    claim = HERE / "cohort-ledger" / f"{case_id}-claim.json"
    assert not claim.exists() and not claim.is_symlink()
    paths = [HERE / f"scope88-{case_id}.json", HERE / f"scope88-{case_id}-pin.json", HERE / case_id]
    assert all(not path.exists() and not path.is_symlink() for path in paths)
    create(paths[0], scope)
    pin = {"case_id": case_id, "scope_sha256": sha(paths[0].read_bytes()),
        "protocol_sha256": protocol_pin, "shared_public_source_boundary_sha256": protocol["public_source_boundary_sha256"]}
    create(paths[1], pin)
    paths[2].mkdir(exist_ok=False)
    return {**pin, "source_pin_count": len(scope["source_pins"]), "actual_claims": 0, "provider_posts": 0}


def prepare_case(case_id, *, output_policy=None, checker_high=False, checker_high8192=False):
    """Prepare one unclaimed baseline using the exact frozen source/profile, never re-snapshot Main."""
    import budget88
    assert case_id in budget88.BASE_CASES and not checker_high and not checker_high8192
    protocol, protocol_pin = _protocol()
    assert output_policy is None or output_policy == protocol["default_output_policy"]
    row = next(item for item in protocol["cases"] if item["case_id"] == case_id)
    scope = _build_scope(protocol, protocol_pin, row, case_id)
    return _write_scope(case_id, scope, protocol, protocol_pin)


def prepare_supplement(instance_id, base_case_id, qa_receipt_path=None, *, kind=None,
                       repair_review_sha256=None, output_policy=None, checker_high=False,
                       checker_high8192=False, zero_post_reconciliation_sha256=None):
    """Root selects one bounded affected/control run or a distinct QA-qualified page question."""
    import budget88
    assert instance_id in budget88.AUX_CASES | budget88.PAGE_CASES
    assert base_case_id in budget88.BASE_CASES | budget88.AUX_CASES and base_case_id != instance_id
    assert not checker_high and not checker_high8192 and zero_post_reconciliation_sha256 is None
    protocol, protocol_pin = _protocol()
    budget88._planned(protocol, instance_id)
    state = budget88.snapshot(HERE / "cohort-ledger")
    assert Decimal(state["unknown_full_hold_USD"]) == 0 and not state["cohort_stopped"]
    paths = [HERE / f"supplement88-{instance_id}.json", HERE / f"scope88-{instance_id}.json",
             HERE / f"scope88-{instance_id}-pin.json", HERE / instance_id]
    assert all(not path.exists() and not path.is_symlink() for path in paths)
    base, base_pin = budget88._pinned_record(HERE / f"scope88-{base_case_id}.json")
    assert base["cohort_protocol_sha256"] == protocol_pin and base["phase88_authorization"] == AUTH
    assert output_policy is None or output_policy == protocol["default_output_policy"]
    base_version = budget88.public_digest(base["source_pins"])
    repair_path = repair_pin = qa_pin = answer_pin = None
    if instance_id in budget88.AUX_CASES:
        assert base_case_id in budget88.BASE_CASES and kind in ("affected", "control") and qa_receipt_path is None
        plan, repair_pin = budget88._fix_plan(HERE / "cohort-ledger", protocol, protocol_pin)
        assert repair_review_sha256 == repair_pin
        repair_path = "common-fix-plan89.json"
        assert {"instance_id": instance_id, "kind": kind, "base_case_id": base_case_id,
                "question_sha256": base["question_sha256"]} in plan["instances"]
        source_pins = plan["source_pins_after"]
        nonpage = sum(count for key, count in state["case_posts"].items() if key not in budget88.PAGE_CASES)
        assert nonpage + 4 <= budget88.NONPAGE_POST_CAP
    else:
        assert kind in (None, "quality_qualified_page") and repair_review_sha256 is None
        kind = "quality_qualified_page"
        source_pins = base["source_pins"]
        assert state["claimed_physical_posts"] + 4 <= budget88.POST_CAP
    assert Decimal(state["known_cost_USD"]) + budget88.HOLD * 4 <= budget88.COST_CAP
    scope = _build_scope(protocol, protocol_pin, base, instance_id, source_pins=source_pins)
    instance_version = budget88.public_digest(scope["source_pins"])
    final_path = HERE / base_case_id / "native-provider70" / "final-receipt.json"
    closure_path = HERE / base_case_id / "api-closure77.json"
    journey_path = HERE / base_case_id / "journey-receipt88.json"
    final, final_pin = budget88._pinned_record(final_path)
    closure, closure_pin = budget88._pinned_record(closure_path)
    journey, journey_pin = budget88._pinned_record(journey_path)
    assert final["closure_status"] == "CLOSED_NUMERIC_NO_UNKNOWN" and final["actual_posts"] > 0
    assert final["settled_numeric_cost_observations"] == final["actual_posts"]
    assert closure["owned_threads_closed"] is True
    assert set(closure["old_metadata_unchanged"]) == budget88._OLD_METADATA_KEYS
    assert all(value is True for value in closure["old_metadata_unchanged"].values())
    if instance_id in budget88.PAGE_CASES:
        assert type(qa_receipt_path) is str and qa_receipt_path
        qa_path = budget88._public_relative(HERE, qa_receipt_path)
        qa, qa_pin = budget88._pinned_record(qa_path)
        assert journey["status"] == "API_COMPLETED" and journey["API_n"] == journey["completed_answer_n"] == 1
        response = journey["response"]
        answer_pin = budget88.public_digest(response)
        assert budget88.page_quality_matches(qa, base, response, base_scope_sha256=base_pin,
            source_version_sha256=instance_version, journey=journey, journey_sha256=journey_pin)
        assert base_version == instance_version
        if (HERE / "common-fix-plan89.json").exists():
            plan, _ = budget88._fix_plan(HERE / "cohort-ledger", protocol, protocol_pin)
            assert instance_version == plan["source_version_after_sha256"]
        else:
            assert instance_version == protocol["source_version_sha256"]
        scope.update(page_answer_requires_independent_quality_review=True,
            page_base_checker_config_sha256=budget88.public_digest(base["expected_checker_config"]),
            page_base_teacher_config_sha256=budget88.public_digest(base["expected_model_config"]),
            page_base_public_DTO_sha256=answer_pin)
        qa_receipt_path = Path(qa_receipt_path).as_posix()
    else:
        assert base_version == protocol["source_version_sha256"] and instance_version != base_version
    descriptor = {"schema": "dev89_planned_instance_descriptor_v1", "authorization": AUTH,
        "instance_id": instance_id, "kind": kind, "base_case_id": base_case_id, "protocol_sha256": protocol_pin,
        "question_id": base["question_id"], "question_sha256": base["question_sha256"],
        "base_scope_sha256": base_pin, "base_source_version_sha256": base_version,
        "instance_source_version_sha256": instance_version, "base_final_receipt_sha256": final_pin,
        "base_api_closure_sha256": closure_pin, "qa_receipt_path": qa_receipt_path, "qa_receipt_sha256": qa_pin,
        "actual_answer_sha256": answer_pin, "root_selected_authorized": True, "automatic_replay_or_reclaim": False,
        "repair_review_path": repair_path, "repair_review_sha256": repair_pin, "base_journey_receipt_sha256": journey_pin}
    raw = (json.dumps(descriptor, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    scope["supplement_descriptor_sha256"] = sha(raw)
    create(paths[0], descriptor)
    result = _write_scope(instance_id, scope, protocol, protocol_pin)
    budget88.validate_supplement(HERE / "cohort-ledger", instance_id, scope["supplement_descriptor_sha256"])
    return {**result, "supplement_descriptor_sha256": scope["supplement_descriptor_sha256"]}


def write_final_results():
    """Write one result once; all eight baseline questions remain visible, including unrun cases."""
    import budget88
    protocol, protocol_pin = _protocol()
    totals = budget88.snapshot(HERE / "cohort-ledger")
    cases = []
    for planned in protocol["planned_instances"]:
        case_id = planned["instance_id"]
        directory = HERE / case_id
        row = {**planned, "case_id": case_id, "status": "NOT_RUN_OR_NOT_SELECTED", "evidence": []}
        if case_id in budget88.BASE_CASES:
            row.update(next(item for item in protocol["cases"] if item["case_id"] == case_id))
        for path in sorted(directory.glob("native-provider70/*.json")):
            assert path.is_file() and not path.is_symlink()
            row["evidence"].append({"path": str(path.relative_to(HERE)), "bytes": path.stat().st_size,
                                    "sha256": sha(path.read_bytes())})
        for name, field in (("native-provider70/final-receipt.json", "financial_and_transport"),
                            ("journey-receipt88.json", "actual_journey"), ("api-closure77.json", "API_closure")):
            path = directory / name
            if path.is_file():
                assert not path.is_symlink()
                row[field] = json.loads(path.read_bytes())
                row["evidence"].append({"path": str(path.relative_to(HERE)), "bytes": path.stat().st_size,
                                        "sha256": sha(path.read_bytes())})
        if "actual_journey" in row:
            row["status"] = row["actual_journey"].get("status", "UNKNOWN_LOCAL_JOURNEY_STATE")
        cases.append(row)
    result = {"schema": "dev89_unified_results_v1", "authorization": AUTH, "protocol_sha256": protocol_pin,
        "finished_UTC": datetime.now(timezone.utc).isoformat(), "baseline_denominator": 8,
        "cohort_financial": totals, "cases": cases, "semantic_quality_independently_certified": False,
        "raw_text_not_duplicated_here": True, "old_runtime_or_ledgers_written": False, "auth_exported": False}
    create(HERE / "results89.json", result)
    return result


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--freeze":
        print(json.dumps(freeze_protocol(sys.argv[2])))
    elif len(sys.argv) == 2 and sys.argv[1] == "--results":
        print(json.dumps({"cases": len(write_final_results()["cases"]), "output": "results89.json"}))
    elif len(sys.argv) == 2 and sys.argv[1].startswith("case"):
        print(json.dumps(prepare_case(sys.argv[1])))
    else:
        raise SystemExit("EXACT_DEV89_PREPARATION_ACTION_REQUIRED")
