"""Preserve the first authored browser failure and align with the real job contract."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = HERE / "proof60.spec.ts"
old = spec.read_bytes()
assert hashlib.sha256(old).hexdigest() == "553d4e3c54f54fe09aee9c276da14777e81c0ad1cbf4260ce506a800f8750709"
with (HERE / "proof60.native01.spec.ts").open("xb") as stream:
    stream.write(old)
text = old.decode("utf-8")
line = "await expect(page.getByRole('button', { name: 'Retry response', exact: true })).toBeVisible();"
assert text.count(line) == 2
text = text.replace(line, "await expect(page.getByRole('button', { name: 'Retry response', exact: true })).toHaveCount(0);")
anchor = "  expect(secondJob.error.code).toBe('SEMANTIC_CHECK_FAILED');\n"
assert text.count(anchor) == 1
text = text.replace(anchor, anchor + "  expect(secondJob.can_retry).toBe(false);\n")
new = text.encode("utf-8")
spec.write_bytes(new)
new_hash = hashlib.sha256(new).hexdigest()
runner = HERE / "run_native60.py"
runner_old = runner.read_bytes()
with (HERE / "run_native60.native01.py").open("xb") as stream:
    stream.write(runner_old)
anchor = "553d4e3c54f54fe09aee9c276da14777e81c0ad1cbf4260ce506a800f8750709"
assert runner_old.decode("utf-8").count(anchor) == 1
runner.write_text(runner_old.decode("utf-8").replace(anchor, new_hash), encoding="utf-8", newline="")
receipt = dict(status="CORRECTED_AUTHORED_BROWSER_EXPECTATION", predecessor_sha256=anchor,
               corrected_spec_sha256=new_hash, reason="The genuine final-partial job has consumed its finite four-call budget and can_retry=false; Chat correctly hides Retry response",
               production_files_changed=False, original_failure_preserved="native01")
with (HERE / "browser-expectation-correction60.json").open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
