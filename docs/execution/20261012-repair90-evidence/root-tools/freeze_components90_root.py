"""Freeze two prospective checker-only contrasts from closed public Phase90 inputs."""
import hashlib
import json
import sys
from pathlib import Path

W = Path(__file__).resolve().parent
R = W / "5703-repair90-runtime"
M = Path(r"E:\5703\learning-assistant")
sys.dont_write_bytecode = True
sys.path[:0] = [str(R), str(M)]
import budget88
from checker_component90 import prepare_descriptor

review = {
    "purpose": "Root selected same saved Phase90 checker input after three closed BASE cases",
    "current_public_model_config_sha256": budget88.QWEN_PUBLIC_SNAPSHOT_SHA256,
    "current_qwen_configuration": {
        "configuration_id": budget88.QWEN_ID, "revision": 1,
        "config_hash": budget88.QWEN_CONFIG_HASH,
        "stored_max_tokens": 2048, "stored_structured_output_mode": "json_schema",
        "comparison_max_tokens": 8192, "comparison_structured_output_mode": "json_object",
    },
    "quality_certification_from_decode_pass": False,
    "model_only_causal_comparison": False,
    "reasoning_profile_delta": "Gemini HIGH to Qwen disabled",
}
before = budget88.snapshot(R / "cohort-ledger")
assert before["claimed_physical_posts"] == before["settled_posts"] == 7
assert before["unknown_full_hold_USD"] == "0"
outputs = []
for instance, base in (("component01qwen", "case01"), ("component08qwen", "case08")):
    descriptor = prepare_descriptor(R, instance, base, 2, review)
    raw = (json.dumps(descriptor, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    path = R / (instance + "-descriptor90.json")
    with path.open("xb") as stream:
        stream.write(raw)
    pin = hashlib.sha256(raw).hexdigest()
    budget88.validate_component(R / "cohort-ledger", instance, pin)
    outputs.append({"instance": instance, "descriptor_sha256": pin,
        "context_sha256": descriptor["context_sha256"],
        "wire_bytes": descriptor["contrast_wire_bytes"],
        "model_delta": descriptor["model_config_delta"]})
assert budget88.snapshot(R / "cohort-ledger") == before
print(json.dumps({"status": "TWO_PROSPECTIVE_DESCRIPTORS_VALID", "descriptors": outputs,
    "actual_ledger_claims_added": 0, "auth_reads": 0, "database_calls": 0,
    "model_calls": 0, "publication_exercised": False}), flush=True)
