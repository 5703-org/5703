"""Two current-source Mock browser outcomes in one newly owned database."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote

MAIN = Path(r"E:\5703\learning-assistant")
HERE = Path(__file__).resolve().parent
round_name = sys.argv[1] if len(sys.argv) > 1 else "native01"
assert round_name.startswith("native") and round_name.isalnum()
OUT = HERE / round_name
TEMP = HERE / (round_name + "-temp")
TEMP.mkdir(exist_ok=False)
pins = {
    "proof60_browser.py": "a3b3d93ee3659afc8da8f0e0dd91e2df3a85cefa4b61b15cba58ee318c32453d",
    "proof60.spec.ts": "c1fd18c2980df0e37b3dafd0aadaca43a3ee55115f504062bfae7603d4aaff0a",
    "playwright60.config.cjs": "fa6b4d421d1e99f7dae016843c2e676e57672341bf3e26bef18b26b586dd4223",
}
for name, expected in pins.items():
    assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected
for key in list(os.environ):
    if any(marker in key.upper() for marker in ("API_KEY", "TOKEN", "SECRET", "DATABASE_URL", "TEST_DATABASE_SERVER")):
        os.environ.pop(key, None)
os.environ.update(PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                  TEMP=str(TEMP), TMP=str(TEMP), TMPDIR=str(TEMP))
sys.path[:0] = [str(MAIN), str(MAIN / "backend"), str(MAIN / "tests/unit"), str(HERE)]
from proof60_browser import proof60_runtime, verify_browser_receipt, browser_environment

identity = "8014a51a166f9258c4a7753dcb351ad666e890af31a5dc6fda9e517f4bcba5ec"
row = json.loads(subprocess.run(["docker", "inspect", identity], check=True,
                               capture_output=True, text=True, timeout=10).stdout)[0]
assert row["Id"] == identity and row["Name"] == "/5703-latency-20261006-01-pg"
assert row["State"]["Running"]
assert row["HostConfig"]["PortBindings"]["5432/tcp"] == [{"HostIp": "127.0.0.1", "HostPort": "15433"}]
variables = dict(value.split("=", 1) for value in row["Config"]["Env"] if "=" in value)
password = variables["POSTGRES_PASSWORD"]
base = f"postgresql+psycopg://{quote(variables['POSTGRES_USER'], safe='')}:{quote(password, safe='')}@127.0.0.1:15433"
report = dict(status="STARTED", started_at=datetime.now(timezone.utc).isoformat(),
              model_mode="mock", external_model_calls=0, original_database_contents_used=False,
              current_source=True, fixture_database_closed=False, source_pins=pins)
try:
    with proof60_runtime(base, OUT) as runtime:
        args = ["node", str(MAIN / "frontend/node_modules/@playwright/test/cli.js"), "test",
                "--config", str(HERE / "playwright60.config.cjs")]
        run = subprocess.run(args, cwd=HERE, env=browser_environment(OUT), capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=70)
        console = (run.stdout + run.stderr).replace(base, "[isolated-test-server]").replace(password, "[redacted]")
        (OUT / "console.txt").write_text(console, encoding="utf-8")
        report.update(command=args, browser_exit_code=run.returncode)
        if run.returncode == 0:
            report.update(verify_browser_receipt(runtime, OUT / "proof60-browser-receipt.json"))
    report.update(status="PASS" if run.returncode == 0 else "FAIL",
                  fixture_database_closed=True, owned_threads_closed=True)
except BaseException as exc:
    report.update(status="FAIL", error_type=type(exc).__name__)
finally:
    password = base = variables = row = None
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    destination = OUT / "summary.json" if OUT.exists() else HERE / (round_name + "-start-failure.json")
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
raise SystemExit(0 if report["status"] == "PASS" else 1)
