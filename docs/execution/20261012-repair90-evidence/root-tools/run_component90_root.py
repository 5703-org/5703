"""One authorized saved-task checker contrast; memory-only fixture credentials."""
from pathlib import Path
import contextlib
import io
import json
import logging
import sys

sys.dont_write_bytecode = True
W = Path(__file__).resolve().parent
R = W / "5703-repair90-runtime"
M = Path(r"E:\5703\learning-assistant")
logging.disable(logging.CRITICAL)


def main():
    assert len(sys.argv) == 3
    instance, descriptor_sha = sys.argv[1:]
    assert instance in {"component01qwen", "component08qwen"}
    assert len(descriptor_sha) == 64
    sys.path[:0] = [str(R), str(M), str(W / "5703-native76-preparation")]
    from checker_component90 import run
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from bootstrap_native70 import memory_inputs
        fixture_settings, fixture_owner, fixture_login, model_key = memory_inputs()
    del fixture_settings, fixture_owner, fixture_login
    result = run(R, instance, descriptor_sha, api_key=model_key)
    del model_key
    final = json.loads((R / instance / "final-receipt.json").read_bytes())
    print(json.dumps({"instance": instance, "status": result["status"],
        "physical_posts": final["physical_posts"], "cohort": final["cohort"],
        "publication_exercised": False, "independent_QA_required": True,
        "auth_exported": False}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "ROOT_COMPONENT_STOPPED_PRESERVE",
            "error_class": type(error).__name__,
            "finite_code": getattr(error, "code", "ROOT_COMPONENT_GUARD_FAILED"),
            "automatic_retries": 0, "private_details_exported": False}), flush=True)
        raise SystemExit(1)
