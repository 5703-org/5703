"""Record current configured Ruff and unchanged contract/registry content pins."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

MAIN = Path(r"E:\5703\learning-assistant")
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "5703-proof60-runs/static01"
OUT.mkdir(exist_ok=False)
review = json.loads((HERE / "promotion60-review.json").read_text(encoding="utf-8"))
pins = {}
for row in review["files"]:
    content = (MAIN / row["target"]).read_bytes()
    actual = hashlib.sha256(content).hexdigest()
    assert actual == row["sha256"]
    pins[row["target"]] = actual
unchanged = {
    "generation/source_relations_v2.py": "ab22171c03566ed1f8b97e67bb1d0d5f4b276e0ab0bcc40be487f3b296ceeb11",
    "frontend/src/Chat.tsx": "e15a0b56d7ee9d20c8312c05b7e86f60360c3127d930ce50f348c56b0c0a3ad7",
    "docs/execution/tasks.json": "c56119170b9fca1e7eadb1f91db0268c3f57ff25f332e068dfb8679b24aface7",
    "docs/execution/acceptance.json": "b36020cd2acd576fa071ce85c6007d116c7c0b73c8859875f047c44f59c80c73",
}
for target, expected in unchanged.items():
    assert hashlib.sha256((MAIN / target).read_bytes()).hexdigest() == expected, target
args = [str(MAIN / ".venv/Scripts/python.exe"), "-B", "-m", "ruff", "check",
        *[row["target"] for row in review["files"] if row["target"].endswith(".py")],
        "--no-cache", "--config", str(MAIN / "pyproject.toml")]
env = os.environ.copy()
env["PYTHONDONTWRITEBYTECODE"] = "1"
started = datetime.now(timezone.utc).isoformat()
run = subprocess.run(args, cwd=MAIN, env=env, capture_output=True, text=True,
                     encoding="utf-8", errors="replace", timeout=30)
(OUT / "console.txt").write_text(run.stdout + run.stderr, encoding="utf-8")
unit = ET.parse(HERE.parent / "5703-proof60-runs/unit01/tests.xml").getroot()
new_cases = [row for row in unit.iter("testcase")
             if row.get("classname", "").endswith("test_source_evidence_combinations_v1")]
receipt = dict(started_at=started, finished_at=datetime.now(timezone.utc).isoformat(),
               command=args, exit_code=run.returncode, source_pins=pins,
               unchanged_pins=unchanged, new_primary_unit_cases=len(new_cases),
               new_case_failures=sum(any(child.tag in {"failure", "error"} for child in row) for row in new_cases),
               external_model_calls=0)
assert receipt["new_primary_unit_cases"] == 39 and receipt["new_case_failures"] == 0
(OUT / "run.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, indent=2))
print(run.stdout + run.stderr)
raise SystemExit(run.returncode)
