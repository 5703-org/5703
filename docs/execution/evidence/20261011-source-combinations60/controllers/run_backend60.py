"""Current local source-composition integration in fixture-owned random databases."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote

MAIN = Path(r"E:\5703\learning-assistant")
OUT = Path(__file__).resolve().parent.parent / "5703-proof60-runs"
OUT.mkdir(exist_ok=True)
round_name = sys.argv[1] if len(sys.argv) > 1 else "backend01"
assert round_name.startswith("backend") and round_name.isalnum()
output = OUT / round_name
output.mkdir(exist_ok=False)
identity = "8014a51a166f9258c4a7753dcb351ad666e890af31a5dc6fda9e517f4bcba5ec"
row = json.loads(subprocess.run(["docker", "inspect", identity], check=True,
                               capture_output=True, text=True, timeout=10).stdout)[0]
assert row["Id"] == identity and row["Name"] == "/5703-latency-20261006-01-pg"
assert row["State"]["Running"]
assert row["HostConfig"]["PortBindings"]["5432/tcp"] == [{"HostIp": "127.0.0.1", "HostPort": "15433"}]
variables = dict(value.split("=", 1) for value in row["Config"]["Env"] if "=" in value)
password = variables["POSTGRES_PASSWORD"]
base = f"postgresql+psycopg://{quote(variables['POSTGRES_USER'], safe='')}:{quote(password, safe='')}@127.0.0.1:15433"
env = {key: value for key, value in os.environ.items()
       if not any(marker in key.upper() for marker in ("API_KEY", "TOKEN", "SECRET", "DATABASE_URL", "TEST_DATABASE_SERVER"))}
env.update(TEST_DATABASE_SERVER=base, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
           HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
           PYTHONPATH=os.pathsep.join(map(str, [MAIN, MAIN / "backend", MAIN / "tests/unit"])))
args = [str(MAIN / ".venv/Scripts/python.exe"), "-B", "-m", "pytest",
        "tests/integration/test_source_evidence_combinations_runtime.py",
        "tests/integration/test_source_relation_correction_runtime.py", "-q", "--tb=short",
        "-p", "no:cacheprovider", "--basetemp=" + str(output / "temp"),
        "--junitxml=" + str(output / "tests.xml")]
started = datetime.now(timezone.utc).isoformat()
run = subprocess.run(args, cwd=MAIN, env=env, capture_output=True, text=True,
                     encoding="utf-8", errors="replace", timeout=180)
def redact(value):
    return value.replace(base, "[isolated-test-server]").replace(password, "[redacted]").replace(quote(password, safe=""), "[redacted]")
console = redact(run.stdout + run.stderr)
(output / "console.txt").write_text(console, encoding="utf-8")
xml = output / "tests.xml"
if xml.exists():
    xml.write_text(redact(xml.read_text(encoding="utf-8")), encoding="utf-8")
receipt = dict(command=args, started_at=started, finished_at=datetime.now(timezone.utc).isoformat(),
               exit_code=run.returncode, server_identity=identity, port=15433,
               database_scope="fixture-created random cs30_test_* only; fixture drops its own DB",
               retained_database_queries=False, external_model_calls=0, credential_export=False,
               source_scope="current real PostgreSQL/worker/API with authored scripted transport")
(output / "run.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
password = base = variables = row = None
print(json.dumps(receipt, indent=2))
print(console)
raise SystemExit(run.returncode)
