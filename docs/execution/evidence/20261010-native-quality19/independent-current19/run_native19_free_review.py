"""Audited, offline current-source identifier controls and immutable native18 replay."""
from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import types
import unittest

OWNED = Path(__file__).resolve().parent
MAIN = Path(r"E:\5703\learning-assistant")
SITE = MAIN / ".venv" / "Lib" / "site-packages"
RUNTIME = Path(sys.base_prefix).resolve()
PUBLIC = OWNED.parent / "5703-week10-native-pair-20261009-01" / "scientific-native-closure18" / "runtime" / "retained-provider-diagnostics"
INPUTS = [PUBLIC / "slot-02-model-output01.json", PUBLIC / "native-generation-outcome01.json"]
SOURCE_FILES = [MAIN / "generation" / f"reliability_v{i}.py" for i in (3, 4, 5)] + [MAIN / "contracts" / "__init__.py", MAIN / "contracts" / "models.py"]
EXPECTED_GUARD = "f883dc2a0665fb23a6b52b85eeb8c98a51fd80300928a5fefe35764f44c50523"
BASELINE = OWNED / "CURRENT_MAIN_PUBLIC_GUARD_CAPTURE19.py"
EXPECTED_BASELINE = "78a6e2ec89c817b488a0a81be95afcac77a9ac1245ef025a857372de1995bb0d"
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
os.environ["TMP"] = str(OWNED / "tmp")
os.environ["TEMP"] = str(OWNED / "tmp")
os.environ["XDG_CACHE_HOME"] = str(OWNED / "cache")
os.environ["HF_HOME"] = str(OWNED / "cache" / "hf")
sys.dont_write_bytecode = True
AUDIT_DENIALS = []
SOURCE_READS = []
exact_allowed = {str(path.resolve()).casefold() for path in INPUTS + SOURCE_FILES}


def within(path, parent):
    return path == parent or parent in path.parents


def audit(event, args):
    if event.startswith("socket.") or event.startswith("sqlite3.") or event in {"subprocess.Popen", "os.system", "os.startfile", "os.exec", "os.posix_spawn"}:
        AUDIT_DENIALS.append({"event": event, "target": "blocked offline operation"})
        raise PermissionError(f"Offline review prohibits {event}")
    if event in {"os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.link", "os.symlink", "os.chmod", "os.utime"}:
        mutation_paths = args[:2] if event in {"os.rename", "os.link", "os.symlink"} else args[:1]
        if any(not within(Path(os.fsdecode(value)).resolve(), OWNED) for value in mutation_paths):
            AUDIT_DENIALS.append({"event": event, "target": "write outside own review directory"})
            raise PermissionError(f"Review mutation boundary denied: {event}")
    if event != "open" or isinstance(args[0], int):
        return
    path = Path(os.fsdecode(args[0])).resolve()
    mode = args[1] or ""
    flags = args[2] if len(args) > 2 else 0
    write = any(char in mode for char in "wax+") or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
    allowed_write = within(path, OWNED)
    allowed_read = allowed_write or within(path, RUNTIME) or within(path, SITE) or str(path).casefold() in exact_allowed
    sensitive = any(part.casefold() == ".env" or part.casefold().startswith(".env.") or part.casefold().endswith((".pem", ".key")) or any(token in part.casefold() for token in ("binder", "credential", "secrets", "seed_receipt", "private-db")) for part in path.parts)
    if sensitive or (write and not allowed_write) or (not write and not allowed_read):
        AUDIT_DENIALS.append({"event": event, "target": str(path), "write": write})
        raise PermissionError(f"Review file boundary denied: {path}")
    if not write and str(path).casefold() in exact_allowed:
        SOURCE_READS.append(str(path))


sys.addaudithook(audit)


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write_json(name, data):
    (OWNED / ("RUN02_" + name)).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_module(name, path, package=False):
    # Compile the exact pinned public file; do not probe Main's bytecode caches.
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = name if package else name.rpartition(".")[0]
    if package:
        module.__path__ = [str(path.parent)]
    sys.modules[name] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def load_baseline_function():
    tree = ast.parse(BASELINE.read_text(encoding="utf-8-sig"), filename=str(BASELINE))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "evaluate_technical_entity_bindings")
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(BASELINE), "exec"), namespace)
    return namespace[function.name]


def rows(table):
    assert isinstance(table, dict) and set(table) == {"columns", "rows"}
    assert len(set(table["columns"])) == len(table["columns"])
    return [dict(zip(table["columns"], row, strict=True)) for row in table["rows"]]


def packet(reason="The selected source supports the claim.", claim="The system uses XTRP energy.", source="The system uses XTR energy.", extra=None, select_extra=False):
    fragments = [{"fragment_id": "F001", "evidence_id": "ev_001", "exact_text": source}]
    if extra is not None:
        fragments.append({"fragment_id": "F002", "evidence_id": "ev_001", "exact_text": extra})
    selected = ["F001"] + (["F002"] if extra is not None and select_extra else [])
    typed = {"claims": [{"claim_id": "claim_control", "basis": "textbook", "status": "supported", "reason": reason, "citations": [{"evidence_id": "ev_001", "fragment_ids": selected, "relation": "supporting"}]}]}
    claims = [{"claim_id": "claim_control", "answer_field": "answer_text", "text": claim}]
    bindings = [{"claim_id": "claim_control", "citations": [{"evidence_id": "ev_001", "allowed_fragment_ids": [fragment["fragment_id"] for fragment in fragments]}]}]
    return typed, claims, bindings, fragments


BEFORE = {str(path): pin(path) for path in SOURCE_FILES + INPUTS + [BASELINE]}
assert BEFORE[str(MAIN / "generation" / "reliability_v5.py")]["sha256"] == EXPECTED_GUARD, "Current Main guard changed; do not claim an unpinned current run"
assert BEFORE[str(BASELINE)]["sha256"] == EXPECTED_BASELINE
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(MAIN))
generation = types.ModuleType("generation")
generation.__path__ = [str(MAIN / "generation")]
sys.modules["generation"] = generation  # Avoid the service-exporting package initializer.
load_module("contracts", MAIN / "contracts" / "__init__.py", package=True)
load_module("contracts.models", MAIN / "contracts" / "models.py")
load_module("generation.reliability_v3", MAIN / "generation" / "reliability_v3.py")
load_module("generation.reliability_v4", MAIN / "generation" / "reliability_v4.py")
current = load_module("generation.reliability_v5", MAIN / "generation" / "reliability_v5.py")
from generation.reliability_v4 import TextbookClaim
from pydantic import ValidationError
baseline = load_baseline_function()
guard = current.evaluate_technical_entity_bindings
slot = json.loads(INPUTS[0].read_text(encoding="utf-8"))
outcome = json.loads(INPUTS[1].read_text(encoding="utf-8"))
data = slot["check_data"]
raw_judgment = json.loads(slot["raw"]["retained_raw_text"])
assert raw_judgment == outcome["checks"][0]["typed_judgment_raw_aliases"]
assert data["CHECKER_INPUT_ENCODING"]["version"] == "lossless_checker_tables_v1"
actual_claims, fragments = rows(data["CLAIMS"]), rows(data["SOURCE_FRAGMENTS"])
bank = {row["binding_id"]: row for row in rows(data["BINDING_BANK"])}
bindings = [{"claim_id": row["claim_id"], "citations": [{key: bank[bid][key] for key in ("evidence_id", "allowed_fragment_ids")} for bid in row["binding_ids"]]} for row in rows(data["ACTUAL_CITATION_BINDINGS"])]
assert bindings == outcome["checks"][0]["actual_citation_bindings"]
TARGET = "claim_37eb9395c8cbcb5721d36f6e_1"
target_row = next(row for row in raw_judgment["claims"] if row["claim_id"] == TARGET)
target_claim = next(row for row in actual_claims if row["claim_id"] == TARGET)
target_fragment = next(row for row in fragments if row["fragment_id"] == "F007")
ACTUAL_PACKET = (raw_judgment, actual_claims, bindings, fragments)
REPLAY = {}


class Controls(unittest.TestCase):
    def assert_guard(self, expected, **kwargs):
        value = packet(**kwargs)
        TextbookClaim.model_validate(value[0]["claims"][0])
        before = copy.deepcopy(value)
        issues = guard(*value)
        self.assertEqual(len(issues), expected)
        self.assertEqual(value, before)
        for issue in issues:
            self.assertFalse(issue["source_entailment_certified"])
            self.assertFalse(issue["publication_override"])
            self.assertEqual(issue["reason_source_identifiers"], ["XTR"])
            self.assertEqual(issue["source_identifiers"], ["XTR"])
        return issues

    def test_01_generic_reason_detects_previously_missed_collision(self):
        value = packet()
        self.assertEqual(baseline(*value), [])
        self.assert_guard(1)

    def test_02_claimed_identifier_only_reason_cannot_clear(self):
        value = packet(reason="The selected source supports XTRP energy.")
        self.assertEqual(baseline(*value), [])
        self.assert_guard(1, reason=value[0]["claims"][0]["reason"])

    def test_03_source_identifier_reason_remains_detected(self):
        self.assertEqual(len(baseline(*packet(reason="Source states XTR."))), 1)
        self.assert_guard(1, reason="Source states XTR.")

    def test_04_reason_with_both_identifiers_cannot_clear(self):
        self.assert_guard(1, reason="XTR and XTRP appear equivalent to the checker.")

    def test_05_reason_alone_cannot_create_selected_source_identifier(self):
        self.assert_guard(0, source="The system uses ordinary energy.", reason="Source states XTR.")

    def test_06_empty_reason_rejected_before_guard(self):
        value = packet(reason="")
        with self.assertRaises(ValidationError) as raised:
            TextbookClaim.model_validate(value[0]["claims"][0])
        self.assertTrue(any(error["loc"] == ("reason",) and error["type"] == "string_too_short" for error in raised.exception.errors()))

    def test_07_whitespace_reason_is_schema_valid_and_does_not_clear(self):
        self.assert_guard(1, reason=" ")

    def test_08_reason_invariance(self):
        reasons = ["A generic source reason.", "XTRP alone.", "XTR alone.", "XTRP and XTR.", " ", "No acronym is needed."]
        issues = [self.assert_guard(1, reason=reason) for reason in reasons]
        self.assertTrue(all(issue == issues[0] for issue in issues))

    def test_09_selected_literal_alias_exemption_preserved(self):
        self.assert_guard(0, extra="XTR is also called XTRP.", select_extra=True)

    def test_10_unselected_alias_cannot_clear(self):
        self.assert_guard(1, extra="XTR is also called XTRP.")

    def test_11_exact_selected_identifier_exemption(self):
        self.assert_guard(0, source="The system uses XTRP energy.")

    def test_12_unselected_exact_identifier_cannot_clear(self):
        self.assert_guard(1, extra="The system uses XTRP energy.")

    def test_13_comparison_in_different_role_abstains(self):
        self.assert_guard(0, source="The system compares XTR energy with another molecule rather than using it.")

    def test_14_negation_of_proposition_abstains(self):
        self.assert_guard(0, source="The system does not use XTR energy.")

    def test_15_fullname_paraphrase_abstains(self):
        self.assert_guard(0, source="The system uses extended transport receptor phosphate energy, unlike the neighbouring XTR molecule.")

    def test_16_selected_fullname_alias_abstains(self):
        self.assert_guard(0, source="The system uses extended transport receptor phosphate energy (XTRP).")

    def test_17_full_negative_copied_proposition_retains_diagnostic(self):
        self.assert_guard(1, claim="The system does not use XTRP energy.", source="The system does not use XTR energy.")

    def test_18_full_comparison_copied_proposition_retains_diagnostic(self):
        self.assert_guard(1, claim="The system compares XTRP energy with ordinary energy.", source="The system compares XTR energy with ordinary energy.")

    def test_19_fragment_window_must_not_span_selected_fragments(self):
        self.assert_guard(0, source="The system uses", extra="XTR energy.", select_extra=True)

    def test_20_complete_window_inside_longer_fragment(self):
        self.assert_guard(1, source="An introduction. The system uses XTR energy. An epilogue.")

    def test_21_short_three_word_claim_abstains(self):
        self.assert_guard(0, claim="Systems use XTRP.", source="Systems use XTR.")

    def test_22_minimum_four_word_claim_is_checked(self):
        self.assert_guard(1, claim="Systems use XTRP energy.", source="Systems use XTR energy.")

    def test_23_repeated_target_does_not_trigger_single_slot_rule(self):
        self.assert_guard(0, claim="The system uses XTRP and XTRP energy.", source="The system uses XTR and XTR energy.")

    def test_24_distant_identifier_abstains(self):
        self.assert_guard(0, claim="The system uses ABC energy.", source="The system uses XYZ energy.")

    def test_25_identifier_with_only_two_letters_abstains(self):
        self.assert_guard(0, claim="The system uses XY energy.", source="The system uses XYZ energy.")

    def test_26_lowercase_identifier_abstains(self):
        self.assert_guard(0, claim="The system uses xtrp energy.")

    def test_27_substring_is_not_exact_identifier_or_slot(self):
        self.assert_guard(0, source="The system uses MYXTR energy.")

    def test_28_non_supporting_relation_is_not_selected(self):
        value = packet()
        value[0]["claims"][0]["citations"][0]["relation"] = "irrelevant"
        self.assertEqual(guard(*value), [])

    def test_29_unsupported_verdict_is_not_rewritten(self):
        value = packet()
        value[0]["claims"][0]["status"] = "unsupported"
        before = copy.deepcopy(value)
        self.assertEqual(guard(*value), [])
        self.assertEqual(value, before)

    def test_30_partial_verdict_is_not_rewritten(self):
        value = packet()
        value[0]["claims"][0]["status"] = "partial"
        self.assertEqual(guard(*value), [])

    def test_31_general_knowledge_is_outside_guard_scope(self):
        value = packet()
        value[0]["claims"][0]["basis"] = "general_knowledge"
        self.assertEqual(guard(*value), [])

    def test_32_claim_identity_mismatch_deferred_to_identity_gate(self):
        value = packet()
        value[2][0]["claim_id"] = "foreign_claim"
        self.assertEqual(guard(*value), [])

    def test_33_duplicate_fragment_identity_deferred_to_identity_gate(self):
        value = packet()
        value[3].append(copy.deepcopy(value[3][0]))
        self.assertEqual(guard(*value), [])

    def test_34_unallowed_fragment_is_not_used(self):
        value = packet()
        value[2][0]["citations"][0]["allowed_fragment_ids"] = []
        self.assertEqual(guard(*value), [])

    def test_35_wrong_evidence_identity_is_not_used(self):
        value = packet()
        value[3][0]["evidence_id"] = "ev_002"
        self.assertEqual(guard(*value), [])

    def test_36_short_answer_field_has_same_identifier_scope(self):
        value = packet()
        value[1][0]["answer_field"] = "short_answer"
        self.assertEqual(len(guard(*value)), 1)

    def test_37_no_selected_proposition_does_not_create_diagnostic(self):
        self.assert_guard(0, source="The system contains another mechanism.", extra="The system uses XTR energy.")

    def test_38_citation_marker_does_not_hide_copied_proposition(self):
        self.assert_guard(1, claim="The system uses XTRP energy [ev_001].")

    def test_39_actual18_original_full_raw_schema_rejects_non_boolean_sentinel(self):
        before = copy.deepcopy(raw_judgment)
        with self.assertRaises(ValidationError) as raised:
            current.ReliableCheckV5.model_validate(raw_judgment)
        self.assertEqual([(error["loc"], error["type"]) for error in raised.exception.errors()], [(('attempt_evaluation_ok',), 'bool_type')])
        self.assertEqual(raw_judgment, before)

    def test_40_actual18_old_guard_misses_actual_selected_slot(self):
        self.assertEqual(baseline(*ACTUAL_PACKET), [])
        self.assertEqual(outcome["checks"][0]["technical_entity_binding_issues_raw_aliases"], [])

    def test_41_actual18_current_guard_detects_only_expected_collision(self):
        before = copy.deepcopy(ACTUAL_PACKET)
        issues = guard(*ACTUAL_PACKET)
        self.assertEqual(ACTUAL_PACKET, before)
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue["claim_id"], TARGET)
        self.assertEqual(issue["claimed_identifier"], "NADPH")
        self.assertEqual(issue["source_identifiers"], ["NADH"])
        self.assertEqual(issue["reason_source_identifiers"], ["NADH"])
        self.assertEqual(issue["selected_fragment_ids"], ["F007"])
        self.assertFalse(issue["publication_override"])
        self.assertFalse(issue["source_entailment_certified"])
        self.assertEqual(target_row["status"], "supported")
        self.assertIn("NADPH", target_row["reason"])
        self.assertNotIn("NADH", target_row["reason"])
        self.assertIn("NADH", target_fragment["exact_text"])
        self.assertNotIn("NADPH", target_fragment["exact_text"])
        REPLAY.update({"original_status": target_row["status"], "original_reason": target_row["reason"], "claim": target_claim, "selected_fragment": target_fragment, "old_guard_issues": [], "current_guard_issues": issues, "raw_judgment_unchanged": True})

    def test_42_actual18_target_claim_row_is_schema_valid(self):
        self.assertEqual(TextbookClaim.model_validate(target_row).model_dump(), target_row)

    def test_43_actual18_raw_contract_field_is_preserved(self):
        self.assertEqual(raw_judgment["attempt_evaluation_ok"], "not_applicable")
        REPLAY["full_raw_schema_observation"] = {"field": "attempt_evaluation_ok", "raw_value": "not_applicable", "expected_type": "bool", "direct_schema_result": "rejected", "target_claim_row_schema_valid": True, "contract_normalization_executed_by_this_review": False}

    def test_44_reverse_one_edit_insertion_retains_narrow_rule(self):
        value = packet(claim="The system uses XTR energy.", source="The system uses XTRP energy.")
        issues = guard(*value)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["source_identifiers"], ["XTRP"])

    def test_45_one_substitution_retains_narrow_rule(self):
        value = packet(source="The system uses XTRX energy.")
        issues = guard(*value)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["source_identifiers"], ["XTRX"])


for name in ("tmp", "cache"):
    (OWNED / name).mkdir(exist_ok=True)
buffer = io.StringIO()
suite = unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(suite)
(OWNED / "RUN02_ACTUAL_CURRENT19_CONTROL_LOG.txt").write_text(buffer.getvalue(), encoding="utf-8")
AFTER = {str(path): pin(path) for path in SOURCE_FILES + INPUTS + [BASELINE]}
unchanged = BEFORE == AFTER
write_json("ACTUAL_CURRENT19_SELECTED_SOURCE_REPLAY.json", REPLAY)
write_json("ACTUAL_CURRENT19_SOURCE_PINS.json", {"before": BEFORE, "after": AFTER, "all_pins_unchanged": unchanged})
summary = {"schema": "native19_independent_free_controls_v1", "run_scope": "Actual current Main guard read-only under strict offline audit; isolated tests and output only", "current_guard_sha256": EXPECTED_GUARD, "baseline_guard_sha256": EXPECTED_BASELINE, "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped), "was_successful": result.wasSuccessful() and unchanged and not AUDIT_DENIALS, "source_and_replay_inputs_unchanged": unchanged, "audit_denials": AUDIT_DENIALS, "allowed_public_source_reads": sorted(set(SOURCE_READS)), "boundaries": {"no_main_writes": True, "no_sensitive_files_read": True, "no_database_or_service_started": True, "network_and_subprocess_prohibited": True, "paid_calls": 0, "full_unit_repeated": False, "live_ui_or_model_retest": False}, "limitations": ["The narrow guard is a negative binding diagnostic, not a scientific truth verdict or positive entailment certificate.", "Identity-invalid fixtures defer to existing identity validation; guard abstention is not acceptance.", "The native18 target claim row is schema-valid, while its first full raw checker JSON fails direct boolean validation for attempt_evaluation_ok='not_applicable'; this review does not execute or certify the parent's contract normalization.", "This replay does not cure native18's later invalid-JSON final checker failure.", "These independent controls do not replace the parent's actual current service-path verification or live final-answer acceptance."], "failures_detail": [{"test": str(test), "traceback": trace} for test, trace in result.failures], "errors_detail": [{"test": str(test), "traceback": trace} for test, trace in result.errors]}
write_json("ACTUAL_CURRENT19_INDEPENDENT_CONTROL_SUMMARY.json", summary)
print(json.dumps({key: summary[key] for key in ("tests_run", "failures", "errors", "skipped", "was_successful", "source_and_replay_inputs_unchanged", "audit_denials")}))
sys.exit(0 if summary["was_successful"] else 1)
