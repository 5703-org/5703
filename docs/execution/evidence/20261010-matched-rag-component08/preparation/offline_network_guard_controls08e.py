"""Pure offline audit-callback controls08e: no actual DNS, sockets, API, DB, or key."""
import ast,copy,hashlib,ipaddress,json,socket,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-week10-native-pair-20261009-01\diagnostic-preparation\component-rag-quality08")
OUT=ROOT/"offline-network-guard-controls08e"
URL="https://openrouter.ai/api/v1/chat/completions"
def forbid_real_network(event,args):
 if event.startswith("socket."):raise PermissionError("This control never executes a real socket/DNS operation")
sys.addaudithook(forbid_real_network)
OUT.mkdir(exist_ok=False)
rows=[]
def namespace(name):
 p=ROOT/name;tree=ast.parse(p.read_text(encoding="utf-8"))
 names={"inside","safe_network_identity","network_trace","same_pinned_ip","audit"}
 funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="main")
 funcs += [n for n in ast.walk(main) if isinstance(n,ast.FunctionDef) and n.name=="pin_guard"]
 ns={"Path":Path,"ipaddress":ipaddress,"socket":socket,"phase":"component_generation","URL":URL,"GuardDenied":RuntimeError,
 "active":{"transport_url":URL,"posted":True,"post":{},"resolving_host":False,"pinned_ip":None,"network_trace":[]}}
 exec(compile(ast.Module(body=funcs,type_ignores=[]),str(p)+" [only extracted function definitions]","exec"),ns)
 return ns
def case(name,fn,allowed):
 try:fn();actual=True;exc=None
 except PermissionError as e:actual=False;exc=type(e).__name__
 except RuntimeError as e:actual=False;exc=type(e).__name__
 rows.append({"id":name,"expected_allowed":allowed,"observed_allowed":actual,"exception_type":exc,"passed":actual==allowed})
def dns(ns,host="8.8.8.8",port=443,stype=socket.SOCK_STREAM):
 return ns["audit"]("socket.getaddrinfo",(host,port,0,stype,0))
class FakeSocket:
 def __init__(self,family=socket.AF_INET,kind=socket.SOCK_STREAM,proto=0):
  self.family=family;self.type=kind;self.proto=proto
 def settimeout(self,t):pass
 def bind(self,a):raise AssertionError("No source bind expected")
 def close(self):pass
 def connect(self,a):self.audit("socket.connect",(self,a))
def connect(ns,host="8.8.8.8",port=443,kind=socket.SOCK_STREAM,tail=()):
 s=FakeSocket(socket.AF_INET6 if ":" in host else socket.AF_INET,kind);s.audit=ns["audit"]
 return s.connect((host,port)+tail)
old=namespace("run_matched_component_generation08d.py")
case("old-hostname-resolution-allowed",lambda:dns(old,"openrouter.ai"),True)
case("old-legitimate-numeric-resolution-denied",lambda:dns(old),False)
case("old-unrelated-IP443-too-broad",lambda:connect(old,"1.1.1.1"),True)
new=namespace("run_matched_component_generation08e.py")
def state(**values):
 new["phase"]="component_generation"
 new["active"]={"transport_url":URL,"posted":True,"post":{},"resolving_host":False,"pinned_ip":"8.8.8.8","network_trace":[]}
 new["active"].update(values)
state(resolving_host=True,pinned_ip=None)
case("new-original-resolver-hostname443-stream-allowed",lambda:dns(new,"openrouter.ai"),True)
case("new-hostname-wrong-port-denied",lambda:dns(new,"openrouter.ai",80),False)
case("new-hostname-UDP-denied",lambda:dns(new,"openrouter.ai",443,socket.SOCK_DGRAM),False)
case("new-unrelated-hostname-denied",lambda:dns(new,"example.com"),False)
case("new-numeric-before-validation-denied",lambda:dns(new),False)
state()
case("new-hostname-outside-original-resolver-denied",lambda:dns(new,"openrouter.ai"),False)
case("new-exact-validated-numeric443-stream-allowed",lambda:dns(new),True)
case("new-other-numeric-IP-denied",lambda:dns(new,"1.1.1.1"),False)
case("new-numeric-wrong-port-denied",lambda:dns(new,"8.8.8.8",80),False)
case("new-numeric-UDP-denied",lambda:dns(new,"8.8.8.8",443,socket.SOCK_DGRAM),False)
case("new-exact-validated-connect443-stream-allowed",lambda:connect(new),True)
case("new-other-IP-connect443-denied",lambda:connect(new,"1.1.1.1"),False)
case("new-hostname-connect-denied",lambda:connect(new,"openrouter.ai"),False)
case("new-private-IP-connect-denied",lambda:connect(new,"127.0.0.1"),False)
case("new-connect-wrong-port-denied",lambda:connect(new,"8.8.8.8",80),False)
case("new-connect-UDP-denied",lambda:connect(new,kind=socket.SOCK_DGRAM),False)
state(transport_url="https://example.com/api/v1/chat/completions")
case("new-wrong-active-URL-denied",lambda:dns(new),False)
state(post=None)
case("new-no-started-receipt-denied",lambda:dns(new),False)
state(posted=False)
case("new-not-posted-denied",lambda:connect(new),False)
state();new["phase"]="public_preparation"
case("new-wrong-phase-denied",lambda:dns(new),False)
state();new["active"]=None
case("new-no-active-stage-denied",lambda:connect(new),False)
state(pinned_ip="2001:4860:4860::8888")
case("new-IPv6-canonical-pinned-resolution-allowed",lambda:dns(new,"2001:4860:4860:0:0:0:0:8888"),True)
case("new-IPv6-unscoped-connect-allowed",lambda:connect(new,"2001:4860:4860::8888",tail=(0,0)),True)
case("new-IPv6-nonzero-scope-denied",lambda:connect(new,"2001:4860:4860::8888",tail=(0,1)),False)
calls=[]
def fake_original(url):
 calls.append(url);dns(new,"openrouter.ai");return "8.8.8.8"
new["original_pin"]=fake_original
state(pinned_ip=None)
case("new-wrapper-unchanged-original-resolver-once",lambda:new["pin_guard"](URL),True)
assert calls==[URL] and new["active"]["pinned_ip"]=="8.8.8.8"
case("new-wrapper-repeat-resolution-denied",lambda:new["pin_guard"](URL),False)
state(pinned_ip=None)
case("new-wrapper-wrong-URL-denied-before-resolver",lambda:new["pin_guard"]("https://example.com"),False)
assert calls==[URL]
state(pinned_ip=None);new["original_pin"]=lambda url:"127.0.0.1"
case("new-wrapper-nonpublic-return-denied",lambda:new["pin_guard"](URL),False)
# Execute only installed stdlib create_connection's AST with fully in-memory fake primitives.
# No installed socket.getaddrinfo/socket/socket.connect is called.
stdlib_path=Path(socket.__file__)
stdlib_tree=ast.parse(stdlib_path.read_text(encoding="utf-8"))
cc=next(n for n in stdlib_tree.body if isinstance(n,ast.FunctionDef) and n.name=="create_connection")
def fake_stdlib_connection(ns):
 def lookup(host,port,*args):
  dns(ns,host,port,args[1] if len(args)>1 else socket.SOCK_STREAM)
  return [(socket.AF_INET,socket.SOCK_STREAM,6,"",(host,port))]
 class BoundFakeSocket(FakeSocket):
  def __init__(self,*args):super().__init__(*args);self.audit=ns["audit"]
 env={"_GLOBAL_DEFAULT_TIMEOUT":object(),"SOCK_STREAM":socket.SOCK_STREAM,"getaddrinfo":lookup,"socket":BoundFakeSocket,"error":OSError}
 exec(compile(ast.Module(body=[cc],type_ignores=[]),str(stdlib_path)+" [fake primitives only]","exec"),env)
 return env["create_connection"](("8.8.8.8",443))
case("old-real-stdlib-chain-with-fake-primitives-reproduces-denial",lambda:fake_stdlib_connection(old),False)
state(pinned_ip=None);new["original_pin"]=fake_original;new["pin_guard"](URL)
case("new-real-stdlib-chain-with-fake-primitives-passes",lambda:fake_stdlib_connection(new),True)
# Credential loopback exception remains bounded and does not grant other component egress.
new["phase"]="credentials";new["active"]=None
case("existing-credential-loopback-DNS-preserved",lambda:dns(new,"127.0.0.1",15433),True)
case("existing-credential-loopback-connect-preserved",lambda:connect(new,"127.0.0.1",15433),True)
case("credential-other-IP443-denied",lambda:connect(new,"8.8.8.8"),False)
files=[ROOT/"run_matched_component_generation08d.py",ROOT/"run_matched_component_generation08e.py",
 Path(r"E:\5703\learning-assistant\generation\adapters.py"),
 Path(r"E:\5703\learning-assistant\generation\network_policy.py"),stdlib_path,Path(__file__)]
pins=[{"path":str(p),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
result={"schema":"offline_guard_controls08e","status":"PASS" if all(r["passed"] for r in rows) else "FAIL",
 "controls":rows,"passed":sum(r["passed"] for r in rows),"failed":sum(not r["passed"] for r in rows),
 "actual_DNS_socket_provider_DB_credential_model_calls":0,"method":"Extracted callback functions and installed stdlib create_connection AST executed with synthetic in-memory fake primitives only; no entire runner or Main modules executed.",
 "diagnosis":"08d deterministically denies the numeric getaddrinfo required by Main pinned transport; actual08d did not retain the underlying exception, so this reproduces a local incompatibility and is not direct proof of the actual failed event.",
 "prior08d_UNKNOWN":1,"prior08d_hold_usd":"0.03","UNKNOWN_not_reclassified":True,"pins":pins}
raw=(json.dumps(result,indent=2)+"\n").encode()
with (OUT/"OFFLINE_NETWORK_GUARD_CONTROLS08e.json").open("xb") as f:f.write(raw)
print(json.dumps({"status":result["status"],"passed":result["passed"],"failed":result["failed"],
 "path":str(OUT/"OFFLINE_NETWORK_GUARD_CONTROLS08e.json"),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"real_network_calls":0}))
raise SystemExit(0 if result["status"]=="PASS" else 1)
