"""Promote five reviewed local files with exact predecessor and content pins."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

MAIN = Path(r"E:\5703\learning-assistant")
HERE = Path(__file__).resolve().parent
review_path = HERE / "promotion60-review.json"
review_bytes = review_path.read_bytes()
review = json.loads(review_bytes)
assert review["status"] == "REVIEWED_LOCAL_ONLY"
receipt_path = HERE / "promotion60-published.json"
assert not receipt_path.exists()

def digest(data):
    return hashlib.sha256(data).hexdigest()

prepared = []
for row in review["files"]:
    destination = (MAIN / row["target"]).resolve()
    destination.relative_to(MAIN.resolve())
    candidate = Path(row["source"]).read_bytes()
    assert digest(candidate) == row["sha256"]
    assert len(candidate) == row["bytes"]
    predecessor = row["predecessor_sha256"]
    if predecessor is None:
        assert not destination.exists(), str(destination)
    else:
        old = destination.read_bytes()
        assert digest(old) == predecessor, str(destination)
        backup = HERE / "preimages" / row["target"]
        backup.parent.mkdir(parents=True, exist_ok=True)
        assert not backup.exists()
        with backup.open("xb") as stream:
            stream.write(old)
    prepared.append((row, destination, candidate))

written = []
for row, destination, candidate in prepared:
    if row["predecessor_sha256"] is None:
        with destination.open("xb") as stream:
            stream.write(candidate)
    else:
        destination.write_bytes(candidate)
    assert digest(destination.read_bytes()) == row["sha256"]
    written.append({"target": row["target"], "bytes": len(candidate),
                    "sha256": row["sha256"], "predecessor_sha256": row["predecessor_sha256"]})
receipt = {"status": "PUBLISHED", "at_UTC": datetime.now(timezone.utc).isoformat(),
           "review_sha256": digest(review_bytes), "files": written,
           "external_model_calls": 0, "database_access": False,
           "git_actions": False, "other_projects_changed": False}
with receipt_path.open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
