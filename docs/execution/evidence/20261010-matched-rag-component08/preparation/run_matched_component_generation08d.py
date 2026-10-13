"""Matched current GenerationService pair08; default is zero-call payload capture."""
from __future__ import annotations
import argparse,copy,hashlib,importlib.util,json,math,os,sys,time
from dataclasses import asdict
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from urllib import error as urlerror
from uuid import uuid5,NAMESPACE_URL
sys.dont_write_bytecode=True
W=Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2")
MAIN=Path(r"E:\5703\learning-assistant")
D=W/"5703-week10-native-pair-20261009-01/diagnostic-preparation"
ROOT=D/"component-rag-quality08"
CONTEXT=D/"offline-rag-predicate-comparison06/review07/component-context-preparation07/ACTUAL_COMPONENT_CONTEXTS07.json"
INPUT_SHA="16ebc3514f02eb8b6e69d2384ecdc8d00d75d74000000dc17e39b88c27059e1b"
CRED=D/"haiku_json_object_full_checker_probe_PREPARED08.py"
CRED_SHA="b19fdfd53bfccb64e617a8203ed7947bc73ae2c2897a22908de7380dd5e29b6c"
DIAG=D/"attempt-evaluation-conditional-preparation01/retained-checker-diagnostic-preparation01/diagnostics01.py"
DIAG_SHA="e2f06c40dd0b703fd63bbd3248b436a79864290149ca515a4ac81d2822c3942b"
WORKSPACE="5ef0e22c-45f2-4c72-9ff8-acfee1e6b655"
QUESTION="What is homeostasis?"
ARMS=("Dense5","Hybrid5")
CODE_PINS={
"5703-current-native-checker26-20261008-01/serve_current_fixture_native_API_PREPARED08.py":"d8d3ec29dc11cd4fa3d0b5ea636412d840dc4177300b77a3ee1703ac1b15d2b6",
"5703-current-native-checker26-20261008-01/run_generic_current_checker_smoke_PREPARED02.py":"6f60379648020ce19ae38483220537f26fa34c7abdb956ac5b8d9034c7499b70",
"5703-checker-schema-compact-repair-20261008-01/run_single_selected_schema_probe_PREPARED03.py":"33d129b2159d280bb7f9ded9306ca0b2eb12a452ea4b195269f279b3cb7b9522",
"5703-checker-schema-compact-repair-20261008-01/run_current_fixture_qualification_PREPARED01.py":"53ff7ac810326e6c221249b2b73cd25ee3438db94a3491d07cf8053413184ddd"}
CONFIG={"provider":"openai_compatible","model":"google/gemini-3.5-flash-lite",
"base_url":"https://openrouter.ai/api/v1","api_key_env":None,"window_tokens":131072,
"max_tokens":4096,"timeout_seconds":60.0,"temperature":None,"seed":None,
"token_limit_parameter":"max_tokens","structured_output_mode":"json_object",
"reasoning_effort":None,"configuration_id":"component-rag-quality08-gemini35-v1",
"api_version":None,"auth_header":"Authorization","tokenizer_provider":"estimate",
"token_count_fallback":"estimate","thinking_enabled":None,"capability_version":None,
"capabilities":None,"openrouter_route_profile":"gemini35_google_vertex_v1"}
POLICY={"mode":"interactive_chat","condition":"E1","answer_mode":"textbook",
"enhancement_version":"learning_enhancement_v1","reliability_policy":"evidence_reliability_v5",
"generation_context_policy":"complementary_context_v2","source_block_policy":"raw_definition_block_partition_v2",
"repair_policy":"cause_specific_repair_v2","source_relation_policy":None,"joint_checker_policy":"typed_joint_v5",
"provider_output_policy":"json_field_contract_v2","checker_payload_policy":"lossless_checker_tables_v1",
"checker_contract_policy":"single_contract_correction_v1","attribution_strategy":"posthoc_spans",
"teaching_condition":"T2","teaching_context":{"teaching_mode":"direct","task_type":"process_reasoning",
"help_level":0,"turn_role":"user_question"}}
URL="https://openrouter.ai/api/v1/chat/completions"
MAX_BODY=60000
PER=Decimal("0.03")
TOTAL=Decimal("0.12")
phase="startup";active=None;credential_paths=set()
p=argparse.ArgumentParser()
p.add_argument("--execute",action="store_true")
p.add_argument("--manifest-sha256")
args=p.parse_args()
if args.execute and not args.manifest_sha256:raise SystemExit("Reviewed manifest pin required")
ROOT.mkdir(parents=True,exist_ok=True)
OUT=ROOT/("actual08d" if args.execute else "preflight08d")
if OUT.exists():raise SystemExit("Attempt exists; preserve it and prepare a reviewed successor")
OUT.mkdir();TEMP=OUT/"temporary";TEMP.mkdir()
for k,v in {"PYTHONDONTWRITEBYTECODE":"1","HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1",
"HF_HUB_DISABLE_TELEMETRY":"1","TEMP":str(TEMP),"TMP":str(TEMP)}.items():os.environ[k]=v
sys.path[:0]=[str(MAIN),str(MAIN/"backend"),str(MAIN/".venv/Lib/site-packages")]
os.chdir(MAIN)
def inside(path,root):
 try:Path(path).resolve().relative_to(root.resolve());return True
 except (ValueError,TypeError,OSError):return False
def audit(event,a):
 if event in {"subprocess.Popen","os.system","os.posix_spawn"}:raise PermissionError("No child processes")
 if event=="socket.getaddrinfo":
  if phase=="credentials" and a[0]=="127.0.0.1":return
  if active is not None and a[0]=="openrouter.ai":return
  raise PermissionError("Network phase forbidden")
 if event=="socket.connect":
  dest=a[1]
  if isinstance(dest,tuple) and len(dest)>1:
   if phase=="credentials" and dest[:2]==("127.0.0.1",15433):return
   if active is not None and dest[1]==443:return
  raise PermissionError("Network destination forbidden")
 if event=="open" and isinstance(a[0],(str,bytes,os.PathLike)):
  path=Path(os.fsdecode(a[0]));mode=a[1] if isinstance(a[1],str) else "";flags=a[2] if len(a)>2 and isinstance(a[2],int) else 0
  writing=any(c in mode for c in "wax+") or bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
  if writing and not inside(path,OUT):raise PermissionError("Write outside own attempt")
  low=str(path).replace("/","\\").casefold()
  if "\\.codex\\sessions\\" in low or "\\.codex\\archived_sessions\\" in low:raise PermissionError("Forbidden sessions")
  if path.name.casefold()==".env" or path.name.casefold().startswith(".env."):raise PermissionError("No dotenv")
  allowed={CONTEXT.resolve(),CRED.resolve(),DIAG.resolve(),Path(__file__).resolve(),
  (ROOT/"preflight08d/PREFLIGHT_MANIFEST08.json").resolve(),*((W/s).resolve() for s in CODE_PINS)}
  if phase=="credentials":allowed|=credential_paths
  if inside(path,W) and not inside(path,OUT) and path.resolve() not in allowed:raise PermissionError("No extra W/native/auth/binder input")
 if event in {"os.mkdir","os.remove","os.rmdir","os.chmod"} and a and isinstance(a[0],(str,bytes,os.PathLike)):
  if not inside(os.fsdecode(a[0]),OUT):raise PermissionError("Mutation outside own attempt")
 if event in {"os.rename","os.replace"} and not all(inside(os.fsdecode(q),OUT) for q in a[:2]):raise PermissionError("Mutation outside own attempt")
sys.addaudithook(audit)
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def load(name,path,sha):
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError("CODE pin changed")
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
 sys.modules[name]=m;spec.loader.exec_module(m);return m
def production_sources():
 paths={Path(m.__file__).resolve() for m in tuple(sys.modules.values()) if getattr(m,"__file__",None)
 and str(m.__file__).endswith(".py") and inside(m.__file__,MAIN) and not inside(m.__file__,MAIN/".venv")}
 # Pin this exact component's public package, including any later lazy check/transport helper.
 for component in ("generation","conversation","contracts","retrieval"):
  paths|={q for q in (MAIN/component).rglob("*.py") if "__pycache__" not in q.parts}
 paths|=set((MAIN/"generation/prompts").glob("*.txt"))
 return {str(q.relative_to(MAIN)):{"bytes":q.stat().st_size,"sha256":hashlib.sha256(q.read_bytes()).hexdigest()} for q in sorted(paths)}
class GuardDenied(RuntimeError):pass
def main():
 global phase,active,credential_paths
 ledger={"scheduled_arms":2,"POST_attempts":0,"known_cost_usd":"0","new_UNKNOWN":0,
 "stopped":False,"stop_reason":None,"posts":[],"per_POST_cap_usd":str(PER),"total_cap_usd":str(TOTAL)}
 result={"schema":"matched_component_generation08","mode":"execute" if args.execute else "capture_only",
 "question":QUESTION,"context_sha256":INPUT_SHA,"scheduled_arms":2,
 "arms":[{"arm":s,"status":"NOT_STARTED","outcome":None,"component_generation_elapsed_ms":None} for s in ARMS],
 "human_gold":None,"EM_F1":None,"native_Send_to_DOM_ms":None,"default_RAG_promotion":False,
 "historical_UNKNOWN_changed":False,"scope":"single development question; checker observations, not model accuracy or human gold",
 "audit_scope":"Python socket events do not count libpq C-native connections"}
 redactor=None;original=None;key=None;captures={};reviewed=None
 try:
  phase="public_preparation"
  from generation.types import GenerationRequest,ModelConfig,RequestBudget,ProviderResult,failure
  from generation.service import GenerationService
  from generation.adapters import LLMAdapter
  from generation import adapters as am
  from generation import checked,provider_diagnostics,network_policy
  from generation.providers import payload
  from generation.openrouter_routes import prepare_schema_wire
  from generation.teaching_plan_v10 import freeze_generation_policy
  from conversation.query import prepare_query
  from contracts.models import EvidenceSnapshot
  diag=load("matched_component_diagnostics08",DIAG,DIAG_SHA);redactor=diag.Redactor()
  def save(name,value):return diag.save(OUT/name,value,redactor)
  b=CONTEXT.read_bytes()
  if len(b)>16*1024*1024 or hashlib.sha256(b).hexdigest()!=INPUT_SHA:raise ValueError("Actual context pin changed")
  ctx=json.loads(b)
  if ctx.get("status")!="PASS" or ctx.get("question")!=QUESTION or ctx.get("provider_calls")!=0 or ctx.get("actual_execution_device")!="cpu":raise ValueError("Actual context prerequisite failed")
  by={r["arm"]:r for r in ctx["arms"]}
  if set(by)!=set(ARMS) or len(ctx["arms"])!=2:raise ValueError("Two actual arms required")
  cfg=ModelConfig.from_dict(CONFIG);cfg.validate();controls=freeze_generation_policy();requests={}
  for arm in ARMS:
   row=by[arm];evidence=copy.deepcopy(row["evidence"])
   if row["release_id"]!=ctx["corpus"]["release_id"] or row["visibility_hash"]!=ctx["corpus"]["visibility_hash"]:raise ValueError("Shared visibility changed")
   if row["selected_count"]!=5 or len(evidence)!=5 or len({e["chunk_id"] for e in evidence})!=5 or set(row["source_map"])!={e["chunk_id"] for e in evidence}:raise ValueError("Five actual source contexts required")
   for e in evidence:
    EvidenceSnapshot.model_validate(e)
    if hashlib.sha256(e["text"].encode()).hexdigest()!=e["text_hash"]:raise ValueError("Source text changed")
   requests[arm]=GenerationRequest(request_id=str(uuid5(NAMESPACE_URL,"cs30-component08:"+INPUT_SHA+":"+arm)),
   question=QUESTION,evidence=evidence,history=[],summary=None,profile=None,memory_context=None,reading_context=None,
   prepared_query=prepare_query(QUESTION,[],None).model_dump(),understanding=None,source_map=copy.deepcopy(row["source_map"]),
   config=cfg,checker_config=cfg,generation_policy=copy.deepcopy(controls),teaching_plan=None,evidence_coverage=None,coverage_query_policy=None,**copy.deepcopy(POLICY))
  public={a:asdict(r) for a,r in requests.items()};sourcepins=production_sources()
  binding={"runner_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  "main_source_and_prompt_fingerprints":sourcepins,"credential_CODE_sha256":CRED_SHA,"diagnostic_CODE_sha256":DIAG_SHA}
  save("FROZEN_PUBLIC_REQUESTS08.json",public);save("PRODUCTION_BINDING08.json",binding)
  if args.execute:
   mb=(ROOT/"preflight08d/PREFLIGHT_MANIFEST08.json").read_bytes()
   if hashlib.sha256(mb).hexdigest()!=args.manifest_sha256:raise GuardDenied("Manifest pin changed")
   reviewed=json.loads(mb)
   if reviewed["status"]!="READY_FOR_ROOT_REVIEW" or reviewed["runner_sha256"]!=binding["runner_sha256"] or reviewed["request_config_hash"]!=digest(public) or reviewed["context_sha256"]!=INPUT_SHA or reviewed["main_source_and_prompt_fingerprints"]!=sourcepins:raise GuardDenied("Reviewed production/input drift")
   for relative,h in CODE_PINS.items():
    if hashlib.sha256((W/relative).read_bytes()).hexdigest()!=h:raise GuardDenied("Ordinary CODE dependency changed")
   phase="credentials";cred=load("original_approved_credential08",CRED,CRED_SHA)
   credential_paths={Path(cred.BASELINE_PUBLIC_PIN["path"]).resolve(),Path(cred.KEY_REFERENCE).resolve()}
   # Unchanged sanctioned consumer only; never directly parse baseline/key/native fields.
   key=cred.approved_credential(WORKSPACE)
   if not isinstance(key,str) or not key:raise GuardDenied("Approved credential unavailable")
   redactor=diag.Redactor((key,));credential_paths=set();phase="component_generation"
  def make_body(messages,schema,name):
   return prepare_schema_wire(cfg,payload(cfg,messages,schema,name),schema)
  def wire_proof(raw,expected,role):
   if not isinstance(raw,bytes) or len(raw)>MAX_BODY:raise GuardDenied("Body cap exceeded")
   body=json.loads(raw);provider=body.get("provider",{})
   if body!=expected or body.get("model")!=CONFIG["model"] or body.get("max_tokens")!=4096 or body.get("response_format")!={"type":"json_object"} or body.get("reasoning")!={"effort":"low"} or provider.get("only")!=["google-vertex/global"] or provider.get("order")!=["google-vertex/global"] or provider.get("allow_fallbacks") is not False or provider.get("require_parameters") is not True or provider.get("max_price")!={"prompt":0.3,"completion":2.5} or body.get("stream",False) is not False or "temperature" in body or "seed" in body:raise GuardDenied("Wire policy drift")
   upper=(Decimal(len(raw)+1024)*Decimal("0.3")+Decimal(4096)*Decimal("2.5"))/Decimal(1000000)
   if upper>PER:raise GuardDenied("Cost bound exceeded")
   return {"body_bytes":len(raw),"body_sha256":hashlib.sha256(raw).hexdigest(),"conservative_cost_upper_usd":str(upper),
   "role":role,"max_price":provider["max_price"],"output_limit":4096,"input_bound":"UTF8 body bytes+1024 protocol allowance; not actual tokens"}
  original=am.open_provider
  def open_guard(envelope,timeout):
   # Recheck only the frozen deterministic CODE/prompt paths before every POST.
   for relative,expected_pin in sourcepins.items():
    current=(MAIN/relative).read_bytes()
    if len(current)!=expected_pin["bytes"] or hashlib.sha256(current).hexdigest()!=expected_pin["sha256"]:
     raise GuardDenied("Frozen component source/prompt changed before POST")
   c=active
   if c is None or envelope.full_url!=URL or envelope.get_method()!="POST":raise GuardDenied("Only active exact OpenRouter POST")
   # Preserve serialized public input before the final pre-POST assertions; never headers.
   save(c["prefix"]+"-actual-wire08.json",{"payload":json.loads(envelope.data),"original_body_sha256":hashlib.sha256(envelope.data).hexdigest(),"headers_exported":False})
   proof=wire_proof(envelope.data,c["body"],c["role"])
   if c["role"]=="generation" and reviewed["teacher_payloads"][c["arm"]]["body_sha256"]!=proof["body_sha256"]:raise GuardDenied("Teacher wire differs from reviewed capture")
   if ledger["stopped"] or ledger["POST_attempts"]>=4 or c["posted"] or Decimal(ledger["known_cost_usd"])+PER>TOTAL:raise GuardDenied("Finite cap/stopped")
   c["posted"]=True
   post={"arm":c["arm"],"role":c["role"],"started_at_utc":now(),"cost_status":"UNKNOWN","reported_cost_usd":None,"complete":False,"wire_proof":proof,"raw_receipts":[]}
   ledger["POST_attempts"]+=1;ledger["posts"].append(post);c["post"]=post
   save(c["prefix"]+"-POST_STARTED_UNKNOWN08.json",post)
   def retained(receipt):post["raw_receipts"].append(receipt)
   prefix=OUT/(c["prefix"]+"-raw-provider")
   try:return diag.wrap_provider_response(original(envelope,timeout=timeout),path_prefix=prefix,redactor=redactor,on_saved=retained)
   except urlerror.HTTPError as exc:
    diag.retain_http_error_reads(exc,path_prefix=prefix,redactor=redactor,on_saved=retained);raise
  am.open_provider=open_guard
  class RoleAdapter:
   def __init__(self,arm,role):
    self.arm=arm;self.role=role;self.used=False
    self.delegate=LLMAdapter(cfg,api_key=key,retain_invalid_output=True) if args.execute else None
   def denied(self,code):
    return ProviderResult(provider=cfg.provider,model=cfg.model,request_submitted=False,error=failure(code,"Finite component policy stopped this stage",retryable=False))
   def count_tokens(self,*a,**kw):return self.denied("PAID_COUNT_FORBIDDEN")
   def generate(self,messages,*,response_schema,response_schema_name,request_context=None,timeout_seconds=None):
    global active
    rc=request_context or {}
    if rc.get("purpose")!=self.role or rc.get("request_id")!=requests[self.arm].request_id or self.used:return self.denied("EXTRA_STAGE_FORBIDDEN")
    if ledger["stopped"]:return self.denied("GLOBAL_STOP")
    self.used=True;prefix=self.arm+"-"+self.role
    body,metadata=make_body(messages,response_schema,response_schema_name)
    raw=json.dumps(body,ensure_ascii=False,separators=(",",":")).encode()
    save(prefix+"-planned-wire08.json",{"payload":body,"schema":response_schema,"schema_name":response_schema_name,"transport_metadata":metadata,"body_sha256":hashlib.sha256(raw).hexdigest()})
    proof=wire_proof(raw,body,self.role);captures.setdefault(self.arm,{})[self.role]=proof
    if not args.execute:return self.denied("CAPTURE_ONLY_NO_MODEL_RESULT")
    active={"arm":self.arm,"role":self.role,"body":body,"prefix":prefix,"posted":False,"post":None}
    try:
     response=self.delegate.generate(messages,response_schema=response_schema,response_schema_name=response_schema_name,request_context=request_context,timeout_seconds=timeout_seconds)
     post=active["post"]
     if post is not None:
      cost=response.usage.get("cost")
      if type(cost) in (int,float) and math.isfinite(cost) and cost>=0:
       amount=Decimal(str(cost));post["reported_cost_usd"]=str(amount);post["cost_status"]="KNOWN";ledger["known_cost_usd"]=str(Decimal(ledger["known_cost_usd"])+amount)
       if amount>PER or Decimal(ledger["known_cost_usd"])>TOTAL:ledger.update(stopped=True,stop_reason="ACTUAL_COST_CAP_EXCEEDED")
      else:ledger["new_UNKNOWN"]+=1;ledger.update(stopped=True,stop_reason="UNKNOWN_PROVIDER_COST")
      post.update(complete=True,finish_reason=response.finish_reason,error=response.error,usage=response.usage,latency_ms=response.latency_ms)
      save(prefix+"-provider-result08.json",asdict(response));save(prefix+"-POST_FINISH08.json",post)
     if response.error is not None:
      response.error={**response.error,"retryable":False}
      if response.error.get("details",{}).get("uncertain"):ledger.update(stopped=True,stop_reason="UNCERTAIN_SUBMISSION")
     return response
    except Exception as exc:
     post=active["post"]
     if post is not None and not post["complete"]:ledger["new_UNKNOWN"]+=1;ledger.update(stopped=True,stop_reason="SUBMITTED_WITHOUT_RECEIPT")
     save(prefix+"-transport-stop08.json",{"exception_type":type(exc).__name__,"POST_started":post is not None,"retry":False})
     response=self.denied("FINITE_COMPONENT_STOP");response.request_submitted=post is not None;return response
    finally:active=None
  for arm in ARMS:
   row=next(r for r in result["arms"] if r["arm"]==arm)
   if ledger["stopped"]:row["status"]="NOT_RUN_GLOBAL_STOP";continue
   row["status"]="RUNNING";events=[]
   def callback(event):
    events.append(copy.deepcopy(event));save(arm+"-attempt-event-"+str(len(events)).zfill(2)+".json",event)
   def forbidden_sleep(*_):raise GuardDenied("No retry sleep")
   service=GenerationService(adapter=RoleAdapter(arm,"generation"),checker_adapter=RoleAdapter(arm,"joint_check"),sleep=forbidden_sleep)
   start=time.perf_counter();outcome=service.generate(requests[arm],RequestBudget(max_calls=2,max_active_seconds=180.0),on_attempt=callback);elapsed=(time.perf_counter()-start)*1000
   save(arm+"-full-outcome08.json",outcome.to_dict())
   row.update(status=("COMPLETED" if outcome.succeeded else "FAILED_RETAINED") if args.execute else "CAPTURE_ONLY_NO_MODEL_RESULT",
   outcome=outcome.to_dict(),actual_input_context_count=5,component_generation_elapsed_ms=round(elapsed,3) if args.execute else None,
   component_timing_boundary="GenerationService.generate start to final return; teacher+checker if both execute",
   retrieval_preparation_ms=by[arm]["component_context_preparation_ms"],POST_attempts=sum(q["arm"]==arm for q in ledger["posts"]),
   final_pipeline_success_observation=outcome.succeeded if args.execute else None,model_accuracy=None,human_gold=None)
  if not args.execute:
   if any("generation" not in captures.get(a,{}) for a in ARMS):raise GuardDenied("Both actual teacher payloads required")
   manifest={"schema":"matched_component_manifest08","status":"READY_FOR_ROOT_REVIEW","runner_sha256":binding["runner_sha256"],
   "context_sha256":INPUT_SHA,"request_config_hash":digest(public),"main_source_and_prompt_fingerprints":sourcepins,
   "teacher_payloads":{a:captures[a]["generation"] for a in ARMS},"checker_payload":"contingent actual fresh teacher; preserve/validate before POST, never fabricated",
   "model_config":CONFIG,"request_policies":POLICY,"global_POST_limit":4,"each_arm_role_limit":1,"per_POST_cap_usd":str(PER),"total_cap_usd":str(TOTAL),
   "no_retry_no_repair_no_fallback":True,"actual_provider_calls":0,"quality":None,"full_component_answer_time":None,"native_Send_to_DOM":None}
   save("PREFLIGHT_MANIFEST08.json",manifest)
  result["status"]="ACTUAL_PAIR_FINISHED" if args.execute else "PREPARED_PAYLOADS_ONLY"
 except Exception as exc:
  result["status"]="STOP_PREPARATION_OR_EXECUTION";result["failure"]={"exception_type":type(exc).__name__,"phase":phase,"no_retry":True}
 finally:
  if original is not None:am.open_provider=original
  active=None;phase="final";result["ledger"]=ledger;result["finished_at_utc"]=now()
  if redactor is not None:receipt=diag.save(OUT/"RESULT08.json",result,redactor)
  else:
   b=(json.dumps(result,indent=2)+"\n").encode()
   with (OUT/"RESULT08.json").open("xb") as f:f.write(b)
   receipt={"path":str(OUT/"RESULT08.json"),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
  print(json.dumps({"status":result["status"],"receipt":receipt,"POST_attempts":ledger["POST_attempts"],"known_cost_usd":ledger["known_cost_usd"],"new_UNKNOWN":ledger["new_UNKNOWN"],"native_Send_to_DOM_ms":None}))
 return 0 if result.get("status") in {"ACTUAL_PAIR_FINISHED","PREPARED_PAYLOADS_ONLY"} else 2
if __name__=="__main__":raise SystemExit(main())
