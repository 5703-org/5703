"""Verify the complete design registry without claiming runtime implementation."""

from pathlib import Path
import json
import inspect
from contracts import models

ROOT = Path(__file__).resolve().parents[2]


def export_schemas():
    target = ROOT / "contracts/schemas"
    target.mkdir(parents=True, exist_ok=True)
    for name, cls in inspect.getmembers(models, inspect.isclass):
        if cls.__module__ == models.__name__ and issubclass(cls, models.Contract):
            schema = cls.model_json_schema()
            (target / f"{name}.json").write_text(
                json.dumps(schema, indent=2) + "\n", encoding="utf-8"
            )


def main():
    import jsonschema

    export_schemas()
    tasks = json.loads((ROOT / "docs/execution/tasks.json").read_text(encoding="utf-8"))["tasks"]
    checks = json.loads((ROOT / "docs/execution/acceptance.json").read_text(encoding="utf-8"))[
        "checks"
    ]
    ids = {t["task_id"] for t in tasks}
    cids = {c["check_id"] for c in checks}
    assert len(tasks) == len(ids) == 108
    assert len(checks) == len(cids) == 60
    assert cids == {f"AC-{i:02}" for i in range(1, 49)} | {f"HC-{i:02}" for i in range(1, 13)}
    finished = set()
    while len(finished) < len(ids):
        ready = {
            t["task_id"]
            for t in tasks
            if t["task_id"] not in finished and set(t["dependencies"]) <= finished
        }
        assert ready, "Cyclic or missing artifact dependencies"
        finished |= ready
    for task in tasks:
        assert set(task["acceptance_ids"]) <= cids
    for check in checks:
        assert set(check["task_ids"]) <= ids
    required = [
        "source_inventory",
        "requirements",
        "architecture",
        "data_model",
        "api_contract",
        "ai_pipeline",
        "evaluation_plan",
        "ui_flows",
        "test_plan",
        "decisions",
        "conversation_design",
        "scope_migration",
        "handover_migration",
        "integration_ownership",
        "ui_design",
        "responsive_spec",
    ]
    for name in required:
        path = ROOT / "docs/foundation" / f"{name}.md"
        assert path.exists() and len(path.read_text(encoding="utf-8")) > 400, name
    for path in (ROOT / "contracts/schemas").glob("*.json"):
        jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text()))
    for path in (ROOT / "contracts/fixtures").glob("*.json"):
        item = json.loads(path.read_text())
        getattr(models, item["contract"]).model_validate(item["payload"])
    import yaml

    api = yaml.safe_load((ROOT / "contracts/openapi.yaml").read_text())
    assert "/api/v1/sessions/{session_id}/messages" in api["paths"]
    assert (
        "content" in models.ChatMessageCreate.model_fields
        and "options" not in models.ChatMessageCreate.model_fields
    )
    result = {
        "checkpoint": "FOUNDATION_READY",
        "task_count": len(tasks),
        "check_count": len(checks),
        "schema_count": len(list((ROOT / "contracts/schemas").glob("*.json"))),
        "scope": "design consistency only",
        "runtime_acceptance": False,
    }
    from datetime import datetime, timezone

    result["verified_at"] = datetime.now(timezone.utc).isoformat()
    (ROOT / "evidence/foundation").mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence/foundation/verification.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
