"""Export or check runtime OpenAPI and strict public response contracts."""

from pathlib import Path
import argparse
import json
import yaml
from app.main import create_app
from app.core.config import Settings
from contracts.http import ErrorEnvelope
from scripts.verify.foundation import export_schemas

ROOT = Path(__file__).resolve().parents[2]


def runtime_openapi():
    app = create_app(Settings(env="test", database_url="sqlite+pysqlite:///:memory:"))
    try:
        return app.openapi()
    finally:
        app.state.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    schema = runtime_openapi()
    path = ROOT / "contracts/openapi.json"
    rendered = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    if args.write:
        export_schemas()
        path.write_text(rendered, encoding="utf-8")
        (ROOT / "contracts/openapi.yaml").write_text(
            yaml.safe_dump(schema, sort_keys=False), encoding="utf-8"
        )
    else:
        assert path.read_text(encoding="utf-8") == rendered, (
            "Runtime OpenAPI drift: run python -m scripts.verify.contracts --write and regenerate frontend types."
        )
    public = schema["components"]["schemas"]
    for name in (
        "ChatMessageCreate",
        "ChatResponseV1",
        "MCQResponseV1",
        "MessagePage",
        "JobReceipt",
        "AnswerOut",
        "EvidenceSnapshot",
    ):
        assert name in public, name
    assert public["ChatMessageCreate"]["additionalProperties"] is False
    assert set(public["ChatMessageCreate"]["properties"]) == {
        "content",
        "use_profile",
        "answer_mode",
        "teaching_mode",
        "task_id",
        "task_action",
    }
    assert public["ChatMessageCreate"]["properties"]["answer_mode"]["default"] == "textbook"
    assert public["ChatMessageCreate"]["properties"]["answer_mode"]["enum"] == [
        "textbook",
        "general_knowledge",
    ]
    assert "/api/v1/experiments/{run_id}/results" in schema["paths"]
    result = {
        "status": "passed",
        "scope": "runtime API schema and canonical chat boundary",
        "paths": len(schema["paths"]),
        "schemas": len(public),
    }
    out = ROOT / "evidence/contracts"
    out.mkdir(parents=True, exist_ok=True)
    (out / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
