"""Offline source-subset audit. Not the project test suite or application integration."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timezone

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-root", required=True, type=Path)
parser.add_argument("--output", type=Path, default=Path(__file__).with_name("local_checks.json"))
args = parser.parse_args()
root = args.source_root.resolve()
output = args.output.resolve()
output.parent.mkdir(parents=True, exist_ok=True)
sys.dont_write_bytecode = True
sources = []
for path in sorted(root.rglob("*.py")):
    if path.name == Path(__file__).name or "__pycache__" in path.parts:
        continue
    relative = path.relative_to(root).as_posix()
    if not (relative.startswith("personalisation/") or relative == "tests/unit/test_profiles.py"):
        continue
    raw = path.read_bytes()
    item = {"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    try:
        compile(raw, relative, "exec")
        item["syntax"] = "passed"
    except SyntaxError as exc:
        item.update(syntax="failed", error=str(exc))
    sources.append(item)

# This namespace only permits imports BETWEEN DELIVERED ORIGINAL FILES.
# It intentionally skips personalisation/__init__.py, whose compiler requires
# absent contracts.models. No fake Profile, adapters, database, or retrieval module.
namespace = "_week09_source_subset"
package = types.ModuleType(namespace)
package.__path__ = [str(root / "personalisation")]
sys.modules[namespace] = package

def original_module(name):
    fullname = namespace + "." + name
    if fullname in sys.modules:
        return sys.modules[fullname]
    spec = importlib.util.spec_from_file_location(fullname, root / "personalisation" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[fullname] = module
    setattr(package, name, module)
    spec.loader.exec_module(module)
    return module

v2 = original_module("memory_v2")
v3 = original_module("memory_v3")
v4 = original_module("memory_v4")
v5 = original_module("memory_v5")
policy = original_module("memory_policy")
w4 = original_module("memory_writer_v4")
w5 = original_module("memory_writer_v5")
rubric = original_module("rubric")

# Original compiler AST, omitting ONLY the unavailable contracts.models import.
# Execute turn_override and compile_profile(use_profile=False) exclusively.
compiler_tree = ast.parse((root / "personalisation/compiler.py").read_text(encoding="utf-8"))
compiler_tree.body = [node for node in compiler_tree.body if not (isinstance(node, ast.ImportFrom) and node.module == "contracts.models")]
compiler = {}
exec(compile(compiler_tree, "personalisation/compiler.py (AST subset)", "exec"), compiler)

checks = []
observations = []
def check(group, name, fn):
    try:
        actual = fn()
        if actual is not True:
            raise AssertionError(repr(actual))
        checks.append({"group": group, "name": name, "passed": True})
    except Exception as exc:
        checks.append({"group": group, "name": name, "passed": False, "error": type(exc).__name__ + ": " + str(exc)})

def rejects(fn, *values, **kwargs):
    try:
        fn(*values, **kwargs)
    except ValueError:
        return True
    return False

class SyntheticCharacterCounter:
    """Only a fixture for selection branches, NOT an actual tokenizer."""
    def count(self, value):
        return (len(value) + 3) // 4

counter = SyntheticCharacterCounter()
def entry(**changes):
    value = {"id": "memory_fixture", "version": 1, "category": "preference", "field_key": "examples", "scope": "biology", "content": "I prefer examples for biology.", "verification": "explicit_user_statement", "status": "active", "source_message_id": "message_fixture", "source_event_sequence": 4}
    value.update(changes)
    value.setdefault("provenance", {"source_quote": value["content"], "source_hash": v2.digest(value["content"])})
    return value

def source_fixture(item):
    return {"owned": True, "memory_id": item["id"], "memory_version": item["version"], "source_message_id": item["source_message_id"], "content": item["content"], "source_hash": v2.digest(item["content"])}

def select5(items, question="Explain biology", **kwargs):
    return v5.select(items, question, source_reader=source_fixture, counter=counter, **kwargs)

def reason(result, expected):
    return any(row["reason"] == expected for row in result.state["excluded"])

check("compiler_subset", "simplification override", lambda: compiler["turn_override"]("Explain more simply")["level"] == "beginner")
check("compiler_subset", "detail override", lambda: compiler["turn_override"]("Explain in detail")["style"] == "detailed")
check("compiler_subset", "briefly override", lambda: compiler["turn_override"]("Explain briefly")["style"] == "concise")
check("compiler_subset", "ordinary question has no override", lambda: compiler["turn_override"]("What is photosynthesis?") is None)
saved = {"level": "advanced", "style": "detailed", "version": 3}
before = copy.deepcopy(saved)
disabled = compiler["compile_profile"](saved, use_profile=False)
check("compiler_subset", "profile-off branch has no saved profile or policy", lambda: disabled["profile"] is None and disabled["policy"] == "" and saved == before)
temporary = compiler["compile_profile"](saved, use_profile=False, turn_message="Explain more simply")
check("compiler_subset", "profile-off still permits explicit temporary override", lambda: temporary["profile"] is None and temporary["turn_override"]["level"] == "beginner" and bool(temporary["policy"]))
check("compiler_subset", "profile-off hash deterministic", lambda: disabled["policy_hash"] == compiler["compile_profile"](saved, use_profile=False)["policy_hash"])

sheet = rubric.rating_template("item_fixture", "rater_fixture")
check("rubric", "missing ratings are incomplete and unknown gates", lambda: rubric.validate_rating(sheet) == {"complete": False, "gates_passed": None})
filled = copy.deepcopy(sheet); filled["ratings"] = {key: 2 for key in filled["ratings"]}
check("rubric", "complete acceptable ratings pass gates", lambda: rubric.validate_rating(filled) == {"complete": True, "gates_passed": True})
failed_gate = copy.deepcopy(filled); failed_gate["ratings"]["correctness"] = 0
check("rubric", "incorrectness fails gate", lambda: rubric.validate_rating(failed_gate)["gates_passed"] is False)
invalid_rating = copy.deepcopy(filled); invalid_rating["ratings"]["clarity"] = True
check("rubric", "boolean score rejected", lambda: rejects(rubric.validate_rating, invalid_rating))
unit_tree = ast.parse((root / "tests/unit/test_profiles.py").read_text(encoding="utf-8"))
upstream_names = [node.name for node in unit_tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
rating_node = next(node for node in unit_tree.body if isinstance(node, ast.FunctionDef) and node.name == "test_missing_independent_ratings_are_not_zero_or_passed")
rating_namespace = {"rating_template": rubric.rating_template, "validate_rating": rubric.validate_rating}
exec(compile(ast.Module(body=[rating_node], type_ignores=[]), "tests/unit/test_profiles.py (one original AST test)", "exec"), rating_namespace)
def original_rating_test():
    rating_namespace[rating_node.name]()
    return True
check("original_test_function_ast", "one original rubric test function executed without pytest collection", original_rating_test)

check("policy", "default policy is v5 with semantics disabled", lambda: policy.load_policy() == v5.freeze_policy() and policy.load_policy()["enabled"] is False)
for version, module in (("v3", v3), ("v4", v4), ("v5", v5)):
    check("policy", version + " dispatch validates original policy", lambda module=module: policy.selector_for_policy(module.freeze_policy()) is module)
tampered = v5.freeze_policy(); tampered["enabled"] = True
check("policy", "modified v5 identity rejected", lambda: rejects(policy.selector_for_policy, tampered))
check("policy", "v3 semantic activation requires explicit calibration", lambda: rejects(v3.freeze_policy, enabled=True))
check("policy", "duplicate JSON keys rejected", lambda: rejects(policy._unique_object, [("x",1),("x",2)]))
check("policy", "non-finite JSON constant rejected", lambda: rejects(policy._reject_constant, "NaN"))
with tempfile.TemporaryDirectory(prefix="week09_policy_fixtures_", dir=output.parent) as directory:
    fixture_dir = Path(directory)
    def file_policy(content, expect_rejection):
        path = fixture_dir / "synthetic_policy.json"
        path.write_bytes(content)
        try:
            loaded = policy.load_policy(path)
        except v2.MemoryPreparationUnavailable as exc:
            return expect_rejection and exc.code == "MEMORY_POLICY_UNAVAILABLE"
        return not expect_rejection and loaded == v5.freeze_policy()
    check("policy_files", "valid finite policy file loads", lambda: file_policy(json.dumps(v5.freeze_policy()).encode(),False))
    check("policy_files", "duplicate-key file unavailable", lambda: file_policy(b'{"version":1,"version":2}',True))
    check("policy_files", "non-finite file unavailable", lambda: file_policy(b'{"threshold":NaN}',True))
    check("policy_files", "array root unavailable", lambda: file_policy(b'[]',True))
    check("policy_files", "oversized file unavailable", lambda: file_policy(b'x'*(policy.MAX_POLICY_BYTES+1),True))

detail = entry(field_key="detail_level", content="I prefer detailed answers for biology.")
brief = v3.select([detail], "This time explain biology briefly", counter=counter)
check("memory_rules", "Week08 briefly override issue fixed in delivered v2/v3", lambda: not brief.state["entries"] and reason(brief, "current_instruction"))
specific = entry(scope="calvin cycle", content="I prefer examples for calvin cycle.")
unrelated = v3.select([specific], "Explain plant respiration", counter=counter)
check("memory_rules", "v3 specific scope not applied to another biology concept", lambda: not unrelated.state["entries"] and reason(unrelated,"specific_scope_not_named"))
followup = v3.select([specific],"Explain it again",context={"recent_messages":[{"role":"user","content":"Explain the calvin cycle"}]},counter=counter)
check("memory_rules", "v3 short follow-up can inherit recent topic", lambda: bool(followup.state["entries"]))
inactive = v3.select([entry(status="deleted")],"Explain biology",counter=counter)
check("memory_rules", "inactive entry excluded", lambda: not inactive.state["entries"] and reason(inactive,"memory_inactive"))
check("memory_rules", "v3 conditional source absence withholds scope", lambda: v3.conditional_scope(entry(),None)[0] is None)
check("memory_rules", "v3 attributable conditional source reread", lambda: v3.conditional_scope(entry(),source_fixture)[0] == "biology")

trailing = "I prefer examples for biology."
leading = "For biology, I prefer examples."
for version, module in (("v4",v4),("v5",v5)):
    check("conditions", version + " accepts explicit trailing topic", lambda module=module: module.condition(trailing,trailing)[0] == "biology")
    check("conditions", version + " withholds ambiguous repeated quote", lambda module=module: module.condition(trailing,trailing+" "+trailing)[1] == "memory_source_quote_ambiguous")
    complex_quote = "I prefer examples except for biology."
    check("conditions", version + " withholds complex exception", lambda module=module: module.condition(complex_quote,complex_quote)[0] is None)
check("conditions", "v4 does not accept leading topic", lambda: v4.condition(leading,leading)[0] is None)
check("conditions", "v5 accepts leading known topic", lambda: v5.condition(leading,leading)[0] == "biology")
compound = "For biology, I prefer examples and analogies."
check("conditions", "v5 withholds compound leading preference", lambda: v5.condition(compound,compound)[0] is None)
check("conditions", "v5 rejects unattributed quoted speaker", lambda: v5.condition(trailing,"A tutor says " + trailing)[0] is None)

selected = select5([entry()])
check("selection", "v5 selects synthetic owned-source preference", lambda: [x["id"] for x in selected.state["entries"]] == ["memory_fixture"])
missing = v5.select([entry()],"Explain biology",counter=counter)
check("selection", "v5 source reader missing excludes preference", lambda: not missing.state["entries"] and reason(missing,"conditional_source_unavailable"))
wrong_owner = v5.select([entry()],"Explain biology",source_reader=lambda item: {**source_fixture(item),"owned":False},counter=counter)
check("selection", "v5 unowned synthetic source excluded", lambda: not wrong_owner.state["entries"] and reason(wrong_owner,"conditional_source_unavailable"))
wrong_hash = v5.select([entry()],"Explain biology",source_reader=lambda item: {**source_fixture(item),"source_hash":"0"*64},counter=counter)
check("selection", "v5 source-hash mismatch excluded", lambda: not wrong_hash.state["entries"] and reason(wrong_hash,"conditional_source_invalid"))
expired = select5([entry(expires_at="2000-01-01T00:00:00Z")])
check("selection", "v5 expired preference excluded", lambda: not expired.state["entries"] and reason(expired,"memory_expired"))
invalid_expiry = select5([entry(expires_at="not-a-date")])
check("selection", "v5 invalid preference expiry excluded", lambda: not invalid_expiry.state["entries"] and reason(invalid_expiry,"memory_expiry_invalid"))
unchanged = entry(); original = copy.deepcopy(unchanged); select5([unchanged])
check("selection", "selector does not mutate caller entry", lambda: unchanged == original)

corrected = entry(verification="user_corrected",provenance={"kind":"user_correction","recorded_by":"owner_fixture","event_id":"event_fixture","previous_source_message_id":"message_fixture"})
revisions=[{"id":"revision_fixture","entry_id":corrected["id"],"entry_version":1,"content":corrected["content"],"source_message_id":"message_fixture","action":"user_correction","details":{"source_event_sequence":4,"scope":"biology","verification":"user_corrected"}}]
events={4:{"id":"event_fixture","owner_id":"owner_fixture","status":"applied","sequence":4,"operations":[{"operation":"UPDATE","memory_id":corrected["id"],"version":1,"reason":"user_correction"}]}}
canonical = v2.canonical("preference","examples","biology")
check("correction_revision", "v5 accepts consistent synthetic owned revision chain", lambda: bool(v5.correction_source(corrected,"owner_fixture",revisions,events,canonical)))
check("correction_revision", "v5 wrong correction owner rejected", lambda: v5.correction_source(corrected,"different_owner",revisions,events,canonical) is None)
bad_revisions=copy.deepcopy(revisions); bad_revisions[0]["entry_version"]=2
check("correction_revision", "v5 stale correction version rejected", lambda: v5.correction_source(corrected,"owner_fixture",bad_revisions,events,canonical) is None)

check("writer", "v4 prepares exact-source trailing preference", lambda: len(w4.prepare_operations(trailing)["operations"]) == 1)
check("writer", "v5 prepares exact-source trailing preference", lambda: len(w5.prepare_operations(trailing)["operations"]) == 1)
check("writer", "v4 withholds leading preference", lambda: not w4.prepare_operations(leading)["operations"])
check("writer", "v5 prepares leading preference without broadening scope", lambda: w5.prepare_operations(leading)["operations"][0]["scope"] == "biology")
check("writer", "temporary preference not stored", lambda: not w5.prepare_operations("This time I prefer examples for biology.")["operations"])
check("writer", "more than five candidates rejected", lambda: rejects(w5.prepare_operations,trailing,[{}]*6))
bad_candidate = v2.deterministic_operations(trailing)[0]; bad_candidate["content"]="Not the source quote"
check("writer", "changed source content withheld", lambda: not w5.prepare_operations(trailing,[bad_candidate])["operations"])

# Deliberate safety expectations: retain failures instead of editing original code.
delete_candidate = v2.deterministic_operations(trailing)[0]; delete_candidate["operation"]="DELETE"
forged_delete = w5.prepare_operations(trailing,[delete_candidate])
check("safety_expectation", "v5 writer rejects DELETE without explicit erasure text", lambda: not forged_delete["operations"])
plain_if = "I prefer detailed explanations if I am tired."
if_condition = v5.condition(plain_if,plain_if)
if_write = w5.prepare_operations(plain_if)
check("safety_expectation", "ordinary if condition must not become global preference", lambda: if_condition[0] is None and not if_write["operations"])
observations.append({"id":"delete_action_source_mismatch","prepared_operations":[x["operation"] for x in forged_delete["operations"]],"scope":"Synthetic candidate only; no database write or extraction model ran.","source":"personalisation/memory_writer_v5.py:24-36; personalisation/memory_v2.py:380-421"})
observations.append({"id":"ordinary_if_condition_globalised","condition_scope":if_condition[0],"condition_reason":if_condition[1],"prepared_scopes":[x["scope"] for x in if_write["operations"]],"source":"personalisation/memory_v5.py:36-41,138-158"})
off_state = v3.select([],"Explain biology",profile={"use_profile":False,"profile":{"level":"advanced","style":"detailed"}},counter=counter)
observations.append({"id":"raw_selector_profile_off_defaults_retained","saved_profile_defaults":off_state.state["saved_profile_defaults"],"boundary":"Direct raw dict input; the tested compiler profile-off path instead outputs profile=null. Host caller contract was not tested.","source":"personalisation/memory_v3.py:363,396,473-475"})
old_goal = entry(category="goal",field_key="learning_goal",content="I am studying biology.",expires_at="2000-01-01T00:00:00Z")
old_goal_result = select5([old_goal])
observations.append({"id":"v5_expiry_guard_is_preference_only","expired_goal_retained":bool(old_goal_result.state["entries"]),"boundary":"Upstream storage may filter other categories; no storage layer was provided or tested.","source":"personalisation/memory_v5.py:322-334"})
for tag, items in (("empty",[]),("one_preference",[entry()])):
    result = v5.select(items,"Explain biology",source_reader=source_fixture)
    observations.append({"id":"original_default_byte_fallback_"+tag,"retained_entries":len(result.state["entries"]),"counting":result.state["token_counting"],"reported_count":result.state["token_count"],"reported_limit":result.state["token_limit"],"source":"personalisation/memory_v3.py:484-510"})

pytest_available = importlib.util.find_spec("pytest") is not None
suite = {"file":"tests/unit/test_profiles.py","declared_tests":len(upstream_names),"status":"not_collected_or_run_as_suite","pytest_available":pytest_available,"one_original_function_executed_via_ast":rating_node.name,"other_three_original_functions_not_executed": [x for x in upstream_names if x != rating_node.name]}
if not pytest_available:
    probe = subprocess.run([sys.executable,"-m","pytest","--version"],capture_output=True,text=True,timeout=15)
    suite.update(availability_probe_exit_code=probe.returncode,availability_probe_output=(probe.stdout+probe.stderr).replace(str(sys.executable),"[selected_python]").strip())

for item in sources:
    item["unchanged_after_checks"] = hashlib.sha256((root/item["path"]).read_bytes()).hexdigest() == item["sha256"]
result={"executed_at_utc":datetime.now(timezone.utc).isoformat(),"python_version":sys.version.split()[0],"source_location":"caller --source-root (absolute path omitted)","scope":"Original standard-library/within-delivery memory modules under an isolated namespace; compiler AST turn_override and profile-off branch only; one original rubric test AST function. Synthetic fixtures. No real model, embedding, tokenizer, database, API, learner dataset, or complete package integration executed.","loading_boundary":"personalisation/__init__.py bypassed because contracts.models is absent; no replacement contracts, Profile, adapters, storage, retrieval, or model modules were created.","synthetic_fixture_note":"Source-reader/ownership/revision records are authored dictionaries, not real database ownership verification. SyntheticCharacterCounter=ceil(character_count/4) is used only for branch coverage, not actual tokenizer/context-window validation. Original default UTF-8-byte fallback was separately exercised.","sources":sources,"syntax_passed":sum(x["syntax"]=="passed" for x in sources),"syntax_total":len(sources),"checks":checks,"passed":sum(x["passed"] for x in checks),"total":len(checks),"observations":observations,"original_test_suite":suite,"missing_or_unexecuted_dependencies":["contracts.models (Profile, TeachingStudyResponseV1, EvidenceSnapshot)","generation.adapters, parser, prompt_builder, types, token_counting and prompt assets","pytest in the selected bundled runtime","retrieval.embedding, huggingface_hub and pinned local E5 cache for the optional semantic path (not invoked)","application memory-state storage/API, source-reader ownership integration, live extraction, persistence/revocation, and end-to-end tests"],"not_executed":["compile_profile enabled-profile schema path","TeachingStudyService C0/C1/C2 model or mock workload","memory/memory_extraction/writer extract_operations adapter calls","scope_scores or any E5 model encoding","full original pytest collection/execution"]}
output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
print(json.dumps({"syntax":str(result["syntax_passed"])+"/"+str(result["syntax_total"]),"checks":str(result["passed"])+"/"+str(result["total"]),"failed":[x for x in checks if not x["passed"]],"observations":observations,"pytest_status":suite,"output":args.output.as_posix()},indent=2,ensure_ascii=False))
# Audit-report runner: failures remain explicit in JSON, not converted to passes.
