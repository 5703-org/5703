"""Small pure metadata/budget controls; no bootstrap or real journals."""
import ast
import copy
import hashlib
import importlib.util
import json
from decimal import Decimal
from pathlib import Path

C = Path(__file__).resolve().parent
R = C.parents[1] / "5703-dev89-runtime"
A = "parent_repair90_independent24posts_1USD_same_input_validation_20261012"
OLDSET = {"case10c", "case07", "case03r", "case03", "case08", "case05", "case09", "case01", "case06", "case04r", "case10b", "case05r", "case04", "case01r", "case10"}
NEWSET = "{'case01', 'case08', 'case06', 'case01r', 'case08r', 'case06r'}"


class Metadata(ast.NodeTransformer):
    def visit_Constant(self, node):
        if type(node.value) is str:
            value = node.value.replace("parent_dev89_independent32posts_2USD_quality_pages_20261012", A)
            value = value.replace("dev89", "repair90").replace("DEV89", "REPAIR90").replace("Phase89", "Repair90").replace("phase89_", "phase90_")
            value = value.replace("cohort32/$2 cap", "cohort24/$1 cap")
            value = value.replace("(?:case01|case0[3-9]|case01r|case03r|case04r|case05r|case10|case10b|case10c)", "(?:case01|case08|case06|case01r|case08r|case06r)")
            value = value.replace("case(?:01|0[3-9]|01r|03r|04r|05r|10|10b|10c)", "case(?:01|08|06|01r|08r|06r)")
            if value == "2.00":
                value = "1.00"
            node.value = value
        elif type(node.value) is int and node.value == 32:
            node.value = 24
        return node

    def visit_Set(self, node):
        if all(isinstance(v, ast.Constant) and type(v.value) is str for v in node.elts) and {v.value for v in node.elts} == OLDSET:
            return ast.parse(NEWSET, mode="eval").body
        return self.generic_visit(node)


def named(tree):
    return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def main():
    proof, groups = {}, []
    for name in ["normal_transport88.py", "targeted_answer88.py", "server88.py", "api_client88.py"]:
        before, after = (C / name.replace(".py", ".before.py")).read_bytes(), (C / name).read_bytes()
        assert before == (R / name).read_bytes()
        old, new = Metadata().visit(ast.parse(before.decode())), ast.parse(after.decode())
        old_functions, new_functions = named(old), named(new)
        if old_functions != new_functions:
            for key in old_functions:
                if old_functions[key] != new_functions[key]:
                    prior, current = old_functions[key], new_functions[key]
                    offset = next(i for i, (a, b) in enumerate(zip(prior, current)) if a != b)
                    raise AssertionError((name, key, prior[max(0, offset - 70):offset + 100], current[max(0, offset - 70):offset + 100]))
        proof[name] = {"before_sha256": hashlib.sha256(before).hexdigest(), "candidate_sha256": hashlib.sha256(after).hexdigest(), "functions_and_classes_identical_after_declared_metadata_literal_substitutions": True, "function_or_class_count": len(new_functions)}
    groups.append("four_proven_core_AST_equivalent_after_exact_metadata_literals")
    spec = importlib.util.spec_from_file_location("repair90_pure_budget_guard", C / "budget88.py")
    budget = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(budget)
    protocol = json.loads((C / "protocol90-public-candidate.json").read_bytes())
    assert budget.validate_protocol(protocol) == protocol
    groups.append("exact_new_B16_three_case_protocol_six_API_instances_five_disabled_diagnostics")
    for key, value in [("authorization", "old"), ("maximum_physical_posts", 32), ("cost_cap_USD", "2.00"), ("source_version_sha256", "0" * 64)]:
        other = copy.deepcopy(protocol)
        other[key] = value
        try:
            budget.validate_protocol(other)
        except budget.BudgetError:
            pass
        else:
            raise AssertionError(key)
    groups.append("old_authorization_budget_and_A_source_rejected")
    assert budget.POST_CAP == budget.NONPAGE_POST_CAP == 24 and budget.CASE_CAP == 3 and budget.CASE_POST_CAP == 4
    assert budget.COST_CAP == Decimal("1.00") and budget.HOLD == Decimal(".0714688")
    assert not budget.PAGE_CASES and budget._POST_FILE.fullmatch("post-24-claim.json") and not budget._POST_FILE.fullmatch("post-25-claim.json")
    groups.append("shared24_1dollar_unchanged_hold_and_four_calls_no_page_quota")
    assert budget.next_step_allowed([], "teacher", "generation") and not budget.next_step_allowed([], "checker", "diagnostic_check")
    steps = [{"role": "teacher", "purpose": "generation"}, {"role": "checker", "purpose": "joint_check"}, {"role": "checker", "purpose": "checker_contract_repair"}, {"role": "teacher", "purpose": "semantic_repair"}]
    assert not budget.next_step_allowed(steps, "checker", "joint_recheck")
    assert not budget.next_step_allowed([{"role": "teacher", "purpose": "generation"}], "teacher", "generation")
    groups.append("original_Main_finite_role_graph_and_no_automatic_retry")
    marker, fake, captured = {"protocol_sha256": "a" * 64}, Path("W_ONLY_SYNTHETIC_NO_DIRECTORY"), []
    budget._require_running = lambda root: None
    budget._root = lambda root, **kwargs: fake
    budget._create = lambda *args: captured.append(args)

    def state(count=0, unknown="0", known="0", casecount=0):
        claims = {i: {"case_id": "case08", "role": "checker", "purpose": "joint_check"} for i in range(1, count + 1)}
        return marker, {"case01": {}}, claims, {}, {}, {"case01": casecount}, Decimal(known), Decimal(unknown)

    for label, settings in [("global_cap", {"count": 24}), ("UNKNOWN", {"unknown": ".0714688"}), ("dollar_cap", {"known": ".94"}), ("case4", {"casecount": 4})]:
        budget._scan = lambda root, args=settings: state(**args)
        try:
            budget.reserve_post(fake, "case01", "teacher", "b" * 64, 100, purpose="generation")
        except budget.BudgetError:
            pass
        else:
            raise AssertionError(label)
    assert not captured
    groups.append("mocked_global_UNKNOWN_money_case4_boundaries_no_disk_claims")
    budget._scan = lambda root: state()
    assert budget.reserve_post(fake, "case01", "teacher", "b" * 64, 100, purpose="generation") == 1 and len(captured) == 1
    assert captured[0][1]["full_hold_USD"] == "0.0714688"
    groups.append("mocked_positive_serial_reservation_full_hold_preserved")
    for instance in budget.COMPONENT_CASES:
        try:
            budget.claim_case(fake, instance, "c" * 64, "a" * 64)
        except budget.BudgetError as error:
            assert error.code == "FUTURE_COMPONENT_REQUIRES_SEPARATE_FROZEN_CONTROLLER"
        else:
            raise AssertionError(instance)
    groups.append("future_diagnostic_metadata_cannot_claim_via_API")
    for name in ["budget88.py", "prepare88.py"]:
        assert (C / name.replace(".py", ".before.py")).read_bytes() == (R / name).read_bytes()
        ast.parse((C / name).read_text(encoding="utf-8"))
    record = {"schema": "repair90_initial_runtime_finite_static_proof_v1", "status": "PASS", "passed_groups": len(groups), "control_groups": groups, "core_AST_equivalence": proof, "B_source_version_sha256": protocol["source_version_sha256"], "source_pins_count": 16, "API_base_denominator": 3, "planned_API_instances": 6, "prospective_diagnostic_ids": 5, "prospective_diagnostic_entry_currently_disabled": True, "actual_ledger_claims_or_posts_created": 0, "auth_reads": 0, "DB_calls": 0, "model_calls": 0, "network_calls": 0, "Main_writes": 0, "old_R89_writes": 0, "controls_scope": "Pure protocol/AST and mocked in-memory budget boundaries; no bootstrap/app imports or real journal."}
    path = C / "proof-initial90.json"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "groups": len(groups), "proof_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
