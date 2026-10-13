"""Run one authorized repair90 case through the existing guarded API."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

W = Path(__file__).resolve().parent
R = W / "5703-repair90-runtime"
MAIN = Path(r"E:\5703\learning-assistant")
PYTHON = str(MAIN / ".venv/Scripts/python.exe")
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def main():
    assert len(sys.argv) == 2 and sys.argv[1] in {"case01", "case08", "case06", "case01r", "case08r", "case06r"}
    for case in (sys.argv[1],):
        if not (R / ("scope88-" + case + ".json")).exists():
            assert case not in {"case01r", "case08r", "case06r"}, "manual or fresh scope must be prepared explicitly"
            prepared = subprocess.run(
                [PYTHON, "-B", "-X", "utf8", str(R / "prepare88.py"), case],
                cwd=W, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding="utf-8", creationflags=FLAGS, check=False,
            )
            if prepared.returncode:
                print(json.dumps({"case": case, "status": "PREPARATION_FAILED", "models_started": False}), flush=True)
                return 1
        source = R / ("scope88-" + case + ".json")
        pin = hashlib.sha256(source.read_bytes()).hexdigest()
        server = subprocess.Popen(
            [PYTHON, "-B", "-X", "utf8", str(R / "server88.py"), case],
            cwd=MAIN, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", creationflags=FLAGS,
        )
        ready = False
        for line in server.stdout:
            if '"event": "NORMAL_ISOLATED_API_STARTING"' in line:
                ready = True
                break
            if '"event": "SERVER_STOP"' in line:
                print(line.strip(), flush=True)
        if not ready:
            server.wait()
            print(json.dumps({"case": case, "status": "STARTUP_FAILED", "models_started": False}), flush=True)
            return 1
        print(json.dumps({"case": case, "event": "READY_SENDING_IMMEDIATELY"}), flush=True)
        client = subprocess.run(
            [PYTHON, "-B", "-X", "utf8", str(W / "run_client90_root.py"), case, pin],
            cwd=W, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", creationflags=FLAGS, check=False,
        )
        print(client.stdout.strip(), flush=True)
        tail = server.communicate()[0]
        for line in tail.splitlines():
            if line.startswith('{"event":'):
                print(line, flush=True)
        closure_path = R / case / "api-closure77.json"
        if client.returncode or server.returncode or not closure_path.exists():
            print(json.dumps({"case": case, "status": "LOCAL_RUNNER_FAILED_PRESERVE"}), flush=True)
            return 1
        closure = json.loads(closure_path.read_bytes())
        final = json.loads((R / case / "native-provider70/final-receipt.json").read_bytes())
        print(json.dumps({"case": case, "posts": final["actual_posts"],
                          "known_cost_USD": final["native_settled_known_cost_USD"],
                          "cohort_posts": final["cohort_claimed_posts"],
                          "cohort_cost_USD": final["cohort_known_cost_USD"],
                          "UNKNOWN_USD": final["cohort_unknown_full_hold_USD"]}), flush=True)
        if (not closure.get("owned_threads_closed") or final["cohort_permanently_stopped"]
                or final["closure_status"] != "CLOSED_NUMERIC_NO_UNKNOWN"):
            print(json.dumps({"case": case, "status": "SHARED_RISK_STOP_RETAIN_HOLD"}), flush=True)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
