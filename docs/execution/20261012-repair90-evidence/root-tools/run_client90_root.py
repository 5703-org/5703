"""One normal synthetic API journey; credentials remain in memory."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import logging
import sys

sys.dont_write_bytecode = True
W = Path(__file__).resolve().parent
R = W / "5703-repair90-runtime"
logging.disable(logging.CRITICAL)


def main():
    assert len(sys.argv) == 3
    case_id, scope_sha = sys.argv[1:]
    assert case_id in {"case01", "case08", "case06", "case01r", "case08r", "case06r"}
    scope_file = R / ("scope88-" + case_id + ".json")
    assert hashlib.sha256(scope_file.read_bytes()).hexdigest() == scope_sha
    sys.path[:0] = [str(R), str(W / "5703-native76-preparation")]
    from api_client88 import run_case
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from bootstrap_native70 import memory_inputs
        settings, owner, login, key = memory_inputs()
    del settings, owner, key
    result = run_case(R / case_id, scope_file, scope_sha, login=login, runtime=R)
    del login
    print(json.dumps({"case_id": case_id, "status": result["status"],
                      "stage": result.get("stage"), "receipt": str(R / case_id / "journey-receipt88.json"),
                      "auth_exported": False}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "ROOT_CLIENT_STOPPED", "error_class": type(error).__name__,
                          "code": getattr(error, "code", "ROOT_CLIENT_GUARD_FAILED"),
                          "private_details_exported": False}))
        raise SystemExit(1)
