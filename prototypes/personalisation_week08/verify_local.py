"""Read-only Week08 source checks. No adapters, models, storage, or network."""
from pathlib import Path
import ast
import argparse
import copy
import hashlib
import json
import re
import runpy
from datetime import datetime, timezone

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-root", required=True, type=Path, help="Root containing generation/ and personalisation/. Absolute or current-directory-relative path.")
parser.add_argument("--output", type=Path, default=Path(__file__).with_name("pure_function_results.json"))
args = parser.parse_args()
SOURCE = args.source_root.resolve()
OUT = args.output
paths = ["generation/joint_policy.py", "generation/teaching.py", "personalisation/memory.py", "personalisation/memory_extraction.py", "personalisation/memory_v2.py"]
sources = []
for name in paths:
    raw = (SOURCE/name).read_bytes()
    compile(raw, str(SOURCE/name), "exec")
    sources.append({"path":name, "sha256":hashlib.sha256(raw).hexdigest(), "syntax":"passed"})
j = runpy.run_path(str(SOURCE/paths[0]))
t = runpy.run_path(str(SOURCE/paths[1]))
v = runpy.run_path(str(SOURCE/paths[4]))
# Execute only original pure v1 eligibility declarations, not its missing imports.
tree = ast.parse((SOURCE/paths[2]).read_text(encoding="utf-8"))
nodes = [n for n in tree.body if (isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id in {"DURABLE", "TEMPORARY"} for x in n.targets)) or (isinstance(n, ast.FunctionDef) and n.name == "eligible")]
legacy = {"re":re}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE/paths[2]), "exec"), legacy)
checks=[]
observations=[]
def check(name, callback):
    try:
        value = callback()
        assert value is True, repr(value)
        checks.append({"name":name,"passed":True})
    except Exception as exc:
        checks.append({"name":name,"passed":False,"error":type(exc).__name__+": "+str(exc)})
def rejects(fn, *args, **kwargs):
    try: fn(*args, **kwargs)
    except ValueError: return True
    return False
def entry(identifier="m1", field="examples", scope="biology", content="I prefer examples for biology.", **extra):
    return {"id":identifier,"version":1,"category":"preference","field_key":field,"scope":scope,"content":content,"verification":"explicit_user_statement", **extra}
class SyntheticCharacterCounter:
    """Not a tokenizer; only a deliberately small synthetic count for branch tests."""
    def count(self, text): return (len(text)+3)//4
counter = SyntheticCharacterCounter()
check("policy rejects invalid condition", lambda: rejects(j["policy"], "T9"))
check("hint requires help level 1 to 3", lambda: rejects(j["policy"], "T2", {"teaching_mode":"hint","help_level":0}))
check("T2 hint enables evidence and cumulative controls", lambda: all(j["policy"]("T2",{"teaching_mode":"hint"})[x] for x in ("online_check","control_evidence","check_suggestions","check_cumulative")))
check("T0 hint skips online check while T0 direct checks", lambda: not j["policy"]("T0",{"teaching_mode":"hint"})["online_check"] and j["policy"]("T0")["online_check"])
answer = {"answer_text":"Plants make sugars. [ev_001] Water is required. [ev_002]", "short_answer":None}
claims = j["response_claims"](answer)
check("claim spans exactly slice source and preserve citation IDs", lambda: len(claims)==2 and all(answer[c["answer_field"]][c["start"]:c["end"]]==c["text"] for c in claims) and [c["evidence_ids"] for c in claims]==[["ev_001"],["ev_002"]])
context={"version":"query_conditioned_memory_v2","snapshot_id":"synthetic_snapshot","revision":1,"entries":[entry()]}
seg=j["memory_segment"](context)
redacted=j["sanitized_messages"]([seg],context)
check("exact memory segment redacted to metadata", lambda: "I prefer examples" not in redacted[0]["content"] and "segment_sha256" in redacted[0]["content"])
check("memory segment rejects missing required keys", lambda: rejects(j["memory_segment"], {"entries":[{"id":"x"}]}))
check("explicit simpler applies when profile off", lambda: t["teaching_plan"]("Explain in simpler terms",{"use_profile":False,"profile":{"level":"advanced"}})["level"]=="beginner")
check("hint request maps to hint plan", lambda: t["teaching_plan"]("Give me one hint") ["mode"]=="hint")
check("negated hint request not mapped to hint", lambda: t["teaching_plan"]("Do not give me hints") ["mode"]=="explanation")
check("misconception phrase maps to check plan", lambda: t["teaching_plan"]("I think plants do not respire") ["mode"]=="misconception_check")
check("v1 durable eligibility excludes temporary turn", lambda: legacy["eligible"]("I prefer brief answers") and not legacy["eligible"]("This time I prefer brief answers"))
check("v2 temporary statement produces no durable operation", lambda: v["deterministic_operations"]("This time use examples for biology.")==[])
check("v2 explicit preference becomes attributable ADD", lambda: v["deterministic_operations"]("I prefer examples for biology.")==[{"operation":"ADD","category":"preference","field_key":"examples","scope":"biology","content":"I prefer examples for biology.","source_quote":"I prefer examples for biology.","expires_at":None}])
check("v2 correction becomes UPDATE", lambda: v["deterministic_operations"]("From now on I prefer brief answers.")[0]["operation"]=="UPDATE")
check("v2 explicit erasure becomes DELETE", lambda: v["deterministic_operations"]("Forget my preference for examples.")[0]["operation"]=="DELETE")
check("topic aliases map photosynthesis to biology", lambda: "biology" in v["topics"]("How does photosynthesis work?"))
op=v["deterministic_operations"]("I prefer examples for biology.")[0]
check("validation accepts exact attributable typed operation", lambda: v["validate_operation"](op,op["source_quote"])==op)
bad=copy.deepcopy(op);bad["content"]="Invented preference"
check("validation rejects changed content", lambda: rejects(v["validate_operation"],bad,op["source_quote"]))
assessed=copy.deepcopy(op);assessed.update(category="assessment_performance",field_key="assessment_result")
check("extraction cannot create assessment record", lambda: rejects(v["validate_operation"],assessed,op["source_quote"]))
selected=v["learner_state"]([entry(),entry("m2",scope="chemistry")],"Explain photosynthesis",counter=counter)
check("query conditioned selection excludes irrelevant scope", lambda: [e["id"] for e in selected["entries"]]==["m1"] and any(x["reason"]=="scope_not_relevant" for x in selected["excluded"]))
overridden=v["learner_state"]([entry(field="detail_level",content="I prefer detailed answers for biology.")],"This time explain biology briefly",counter=counter)
check("briefly current instruction supersedes saved detail field (expected behaviour)", lambda: not overridden["entries"] and any(x["reason"]=="current_instruction" for x in overridden["excluded"]))
supported_override=v["learner_state"]([entry(field="detail_level",content="I prefer detailed answers for biology.")],"This time give a brief biology answer",counter=counter)
check("recognized brief current instruction supersedes same saved field", lambda: not supported_override["entries"] and any(x["reason"]=="current_instruction" for x in supported_override["excluded"]))
unverified=v["learner_state"]([entry(verification="recorded_unconfirmed")],"Explain biology",counter=counter)
check("unconfirmed record excluded",lambda: not unverified["entries"] and any(x["reason"]=="evidence_unverified" for x in unverified["excluded"]))
profile = {"use_profile":False,"profile":{"level":"advanced","style":"detailed"}}
off_plan=t["teaching_plan"]("Explain photosynthesis",profile)
observations.append({"id":"profile_off_still_uses_saved_style","observed":off_plan["style"]=="detailed","level":off_plan["level"],"style":off_plan["style"],"source":"generation/teaching.py:26-31"})
delete=copy.deepcopy(op);delete["operation"]="DELETE"
observations.append({"id":"validator_accepts_delete_without_erasure_request","observed":not rejects(v["validate_operation"],delete,op["source_quote"]),"source":"personalisation/memory_v2.py:379-420","boundary":"No database write was run; downstream enforcement unknown."})
expiry=v["learner_state"]([entry(expires_at="2000-01-01T00:00:00Z")],"Explain biology",counter=counter)
observations.append({"id":"selector_does_not_itself_filter_expired_entries","observed":bool(expiry["entries"]),"source":"personalisation/memory_v2.py:459-511","boundary":"Storage/read layer could filter before calling this function; absent in member package."})
off_state=v["learner_state"]([entry(field="detail_level",scope="global")],"Explain biology",profile=profile,counter=counter)
observations.append({"id":"selector_uses_profile_defaults_when_use_profile_false","observed":off_state["saved_profile_defaults"].get("style")=="detailed","saved_profile_defaults":off_state["saved_profile_defaults"],"source":"personalisation/memory_v2.py:458,485-486,561-563"})
observations.append({"id":"briefly_mismatch_between_teaching_and_memory_selection","teaching_style":t["teaching_plan"]("This time explain briefly")["style"],"memory_current_operations":v["deterministic_operations"]("This time explain briefly",current_turn=True),"source":"generation/teaching.py:35-36; personalisation/memory_v2.py:283-286"})
projection_response={"answer_text":"Plants make sugars. [ev_001]","short_answer":None,"citations":["ev_001"]}
projection_claims=j["response_claims"](projection_response)
evidence=[{"evidence_id":"ev_001","text":"Plants make sugars.","source_title":"Synthetic teaching passage","section":"Example","pages":[1],"source_url":"https://example.invalid/source"}]
fragments=[{"evidence_id":"ev_001","fragment_id":"fragment_1","exact_text":"Plants make sugars.","chunk_start":0,"chunk_end":19,"complete_block":True}]
projected=j["make_projection"](projection_response,evidence,fragments,projection_claims,True)
check("controlled projection suppresses source URL and preserves excerpt",lambda: projected["citation_views"][0]["source_url"] is None and projected["citation_views"][0]["preview"]=="Plants make sugars." and projected["citation_views"][0]["disclosure"]=="controlled_excerpt")
check("projection hash repeats for identical input",lambda: projected["content_hash"]==j["make_projection"](projection_response,evidence,fragments,projection_claims,True)["content_hash"])
for name, case_entries in [("default_byte_budget_empty",[]),("default_byte_budget_one_entry",[entry()])]:
    try:
        payload=v["learner_state"](case_entries,"Explain biology")
        observations.append({"id":name,"entries_retained":len(payload["entries"]),"token_counting":payload["token_counting"],"token_count":payload["token_count"],"limit":payload["token_limit"]})
    except Exception as exc:
        observations.append({"id":name,"exception":type(exc).__name__,"code":getattr(exc,"code",None)})
result={"executed_at_utc":datetime.now(timezone.utc).isoformat(),"scope":"Original stdlib-only modules; v1 eligible original AST only. Synthetic inputs. No extraction adapters, configured tokenizer, model, storage, API, database, or application integration executed.","synthetic_counter_note":"Selection/conflict tests use ceil(character_count/4) solely as a deterministic test double. It is NOT model token verification; default real byte fallback is separately observed.","source_root":"Caller-supplied --source-root; absolute local path omitted for privacy.","sources":sources,"checks":checks,"passed":sum(x["passed"] for x in checks),"total":len(checks),"risk_observations":observations,"dependencies_absent_in_delivery":["generation/adapters.py","generation/types.py","generation/token_counting.py","backend memory-state database, persistence/API, migration, expiry/revocation validation and integration tests"]}
OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
print(json.dumps({"passed":result["passed"],"total":result["total"],"failed":[x for x in checks if not x["passed"]],"risk_observations":observations,"result_path":str(OUT)},ensure_ascii=False,indent=2))
