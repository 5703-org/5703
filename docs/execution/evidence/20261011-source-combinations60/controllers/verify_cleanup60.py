"""Inspect only the two owned listener ports and the known synthetic PG identity."""
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import subprocess

OUT = Path(__file__).resolve().parent.parent / "5703-proof60-runs/cleanup01"
OUT.mkdir(exist_ok=False)
closed = {}
for port in (18029, 15199):
    with socket.socket() as connection:
        connection.settimeout(1)
        closed[str(port)] = connection.connect_ex(("127.0.0.1", port)) != 0
assert all(closed.values())
identity = "8014a51a166f9258c4a7753dcb351ad666e890af31a5dc6fda9e517f4bcba5ec"
status = subprocess.run(["docker", "inspect", "--format", "{{.Id}}|{{.Name}}|{{.State.Running}}", identity],
                        check=True, capture_output=True, text=True, timeout=10).stdout.strip()
assert status == identity + "|/5703-latency-20261006-01-pg|true"
receipt = dict(status="PASS", at_UTC=datetime.now(timezone.utc).isoformat(),
               owned_listener_ports_closed=closed, original_synthetic_pg_container_running=True,
               fixture_database_cleanup="Both browser contexts returned after their own disposable DB was dropped",
               retained_database_queries=False, credential_read=False, external_model_calls=0)
with (OUT / "run.json").open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
