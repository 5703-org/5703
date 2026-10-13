"""Current-source targeted tests with all outputs confined to this workspace."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

MAIN = Path(r"E:\5703\learning-assistant")
OUT = Path(__file__).resolve().parent.parent / "5703-proof60-runs"
OUT.mkdir(exist_ok=True)
round_name = sys.argv[1] if len(sys.argv) > 1 else "unit01"
assert round_name.startswith("unit") and round_name.isalnum()
run_directory = OUT / round_name
run_directory.mkdir(exist_ok=False)
tests = [
    "tests/unit/test_source_evidence_combinations_v1.py",
    "tests/unit/test_source_relation_units_v2.py",
    "tests/unit/test_source_relation_contract.py",
    "tests/unit/test_source_relation_correction_feedback.py",
    "tests/unit/test_source_relation_protection27.py",
    "tests/unit/test_claim_feedback_transport_v1.py",
    "tests/unit/test_claim_feedback_transport_service_v1.py",
    "tests/unit/test_enhancement_generation.py",
]
env = {key: value for key, value in os.environ.items()
       if not any(marker in key.upper() for marker in ("API_KEY", "TOKEN", "SECRET", "DATABASE_URL", "TEST_DATABASE_SERVER"))}
env.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
           HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
           PYTHONPATH=os.pathsep.join(map(str, [MAIN, MAIN / "backend", MAIN / "tests/unit"])))
args = [str(MAIN / ".venv/Scripts/python.exe"), "-B", "-m", "pytest", *tests,
        "-q", "--tb=short", "-p", "no:cacheprovider",
        "--basetemp=" + str(run_directory / "temp"), "--junitxml=" + str(run_directory / "tests.xml")]
started = datetime.now(timezone.utc).isoformat()
run = subprocess.run(args, cwd=MAIN, env=env, capture_output=True, text=True,
                     encoding="utf-8", errors="replace", timeout=180)
console = run.stdout + run.stderr
(run_directory / "console.txt").write_text(console, encoding="utf-8")
receipt = dict(command=args, started_at=started, finished_at=datetime.now(timezone.utc).isoformat(),
               exit_code=run.returncode, external_model_calls=0, database_access=False,
               source_scope="current Main targeted authored development tests; no held-out model evaluation")
(run_directory / "run.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, indent=2))
print(console)
raise SystemExit(run.returncode)
