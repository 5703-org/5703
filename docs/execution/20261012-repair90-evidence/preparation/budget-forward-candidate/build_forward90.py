"""Static one-time W-only candidate construction; no actual execution."""
from pathlib import Path
import ast
import difflib
import hashlib
import json

W = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2")
P = W / "5703-repair90-preparation/budget-forward-candidate"
R = W / "5703-repair90-runtime"
before = (R / "budget88.py").read_bytes()
assert hashlib.sha256(before).hexdigest() == "081b132d8a40b75ca13124ff433857f2b137fa8687846afc49f313ffae6f071c"
text = before.decode("utf-8").replace("\r\n", "\n")
branch = (P / "component_branch90.txt").read_text(encoding="utf-8")
old = 'def claim_component(*_args, **_kwargs):\n    raise BudgetError("CHECKER_LOW_COMPONENT_FORBIDDEN_IN_REPAIR90")'
assert text.count(old) == 1
text = text.replace(old, branch.rstrip())
old = '            if case_id in _SUPPLEMENTS:\n'
new = '''            if case_id in COMPONENT_CASES:
                expected["schema"] = "repair90_checker_component_claim_v1"
                expected["physical_posts_maximum"] = 1
                expected["component_descriptor_sha256"] = _sha(record.get("component_descriptor_sha256"))
                _require(planned["kind"] == "diagnostic" and planned["maximum_posts"] == 1,
                         "COMPONENT_PLAN_CHANGED")
            elif case_id in _SUPPLEMENTS:
'''
assert text.count(old) == 1
text = text.replace(old, new)
old = '    _require(sorted(claims) == list(range(1, len(claims) + 1)) and len(claims) <= POST_CAP,'
new = '''    components = [_component_records(root, case_id, row["component_descriptor_sha256"], marker, cases)
                  for case_id, row in cases.items() if case_id in COMPONENT_CASES]
    _require(sorted(claims) == list(range(1, len(claims) + 1)) and len(claims) <= POST_CAP,'''
assert text.count(old) == 1
text = text.replace(old, new)
old = '        _require(index < CASE_POST_CAP, "CASE_POST_LIMIT")'
new = '        _require(index < (1 if case_id in COMPONENT_CASES else CASE_POST_CAP), "CASE_POST_LIMIT")'
assert text.count(old) == 1
text = text.replace(old, new)
old = '        _require(next_step_allowed(case_steps[case_id], role, purpose), "ROLE_PURPOSE_SEQUENCE_INVALID")'
new = '''        if case_id in COMPONENT_CASES:
            _require(index == 0 and role == "checker" and purpose == "diagnostic_check",
                     "COMPONENT_SINGLE_CHECKER_DIAGNOSTIC_ONLY")
            descriptor = next(row[0] for row in components if row[0]["instance_id"] == case_id)
            _require(claim.get("wire_sha256") == descriptor["contrast_wire_sha256"]
                     and wire_bytes == descriptor["contrast_wire_bytes"], "COMPONENT_RESERVED_WIRE_CHANGED")
        else:
            _require(next_step_allowed(case_steps[case_id], role, purpose), "ROLE_PURPOSE_SEQUENCE_INVALID")'''
assert text.count(old) == 1
text = text.replace(old, new)
old = '    for descriptor, final in supplements:\n        _closed_base_journal(descriptor, final, cases, claims, settlements, exposures)'
new = old + '\n    for descriptor, final, selected in components:\n        _closed_component_journal(descriptor, final, selected, cases, claims, settlements, exposures)'
assert text.count(old) == 1
text = text.replace(old, new)
text = text.replace('"diagnostic_components_claimed": 0,', '"diagnostic_components_claimed": sum(case_id in COMPONENT_CASES for case_id in cases),')
old = '    _require(index < CASE_POST_CAP, "CASE_POST_LIMIT")'
new = '    _require(index < (1 if case_id in COMPONENT_CASES else CASE_POST_CAP), "CASE_POST_LIMIT")'
assert text.count(old) == 1
text = text.replace(old, new)
old = '    _require(next_step_allowed(steps, role, purpose), "ROLE_PURPOSE_SEQUENCE_INVALID")'
new = '''    if case_id in COMPONENT_CASES:
        _require(index == 0 and role == "checker" and purpose == "diagnostic_check",
                 "COMPONENT_SINGLE_CHECKER_DIAGNOSTIC_ONLY")
        descriptor, _, _ = _component_records(_root(root), case_id,
            cases[case_id]["component_descriptor_sha256"], marker, cases)
        _require(wire_sha256 == descriptor["contrast_wire_sha256"]
                 and wire_bytes == descriptor["contrast_wire_bytes"], "COMPONENT_RESERVED_WIRE_CHANGED")
    else:
        _require(next_step_allowed(steps, role, purpose), "ROLE_PURPOSE_SEQUENCE_INVALID")'''
assert text.count(old) == 1
text = text.replace(old, new)
ast.parse(text)
with (P / "budget88.py").open("xb") as f:
    f.write(text.encode("utf-8"))
controller_path = W / "5703-repair90-preparation/component-candidate/checker_component90.py"
controller_before = controller_path.read_bytes()
assert hashlib.sha256(controller_before).hexdigest() == "540bc89ed8edbf1ed76abb49f0e6e1c941ac87f6826baa8ea7eda6a8a380440c"
controller = controller_before.decode("utf-8").replace("\r\n", "\n")
controller = controller.replace('type(messages) is list and len(messages) == 2\n            and [row.get("role") for row in messages] == ["system", "user"]',
    'type(messages) is list and len(messages) in {2, 3}\n            and [row.get("role") for row in messages] == (["system", "user"] if len(messages) == 2 else ["system", "user", "user"])')
old = '        except HTTPError as exc:\n            raw = exc.read(MAX_RESPONSE + 1)\n            try:\n                observe(raw, exc.code)'
new = '        except HTTPError as exc:\n            try:\n                raw = exc.read(MAX_RESPONSE + 1)\n                observe(raw, exc.code)'
assert controller.count(old) == 1
controller = controller.replace(old, new)
ast.parse(controller)
with (P / "checker_component90.py").open("xb") as f:
    f.write(controller.encode("utf-8"))
for name, original, candidate in (("budget88", before.decode("utf-8").replace("\r\n", "\n"), text),
                                   ("checker_component90", controller_before.decode("utf-8").replace("\r\n", "\n"), controller)):
    with (P / f"{name}.diff").open("x", encoding="utf-8", newline="\n") as f:
        f.write("".join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True),
                    fromfile=f"{name}.before.py", tofile=f"{name}.py")))
print(json.dumps({"candidate_only": True, "files": [{"name": n, "bytes": (P/n).stat().st_size,
                    "sha256": hashlib.sha256((P/n).read_bytes()).hexdigest()}
                    for n in ("budget88.py", "checker_component90.py")]}))
