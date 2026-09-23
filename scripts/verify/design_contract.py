"""Export initial OpenAPI design, superseded by runtime export at G1."""

import inspect
import json
from pathlib import Path
import hashlib
import yaml
from contracts import models

ROOT = Path(__file__).resolve().parents[2]
ROUTES = {
    "/auth/login": ["post"],
    "/users/me": ["get", "patch"],
    "/users/me/password": ["post"],
    "/admin/users": ["get", "post"],
    "/admin/users/{user_id}": ["patch"],
    "/profiles/me": ["get", "put"],
    "/profiles/me/reset": ["post"],
    "/sessions": ["get", "post"],
    "/sessions/{session_id}": ["get", "patch", "delete"],
    "/sessions/{session_id}/archive": ["post"],
    "/sessions/{session_id}/restore": ["post"],
    "/sessions/{session_id}/messages": ["get", "post"],
    "/sessions/{session_id}/summary": ["get", "post"],
    "/jobs/{job_id}": ["get"],
    "/jobs/{job_id}/cancel": ["post"],
    "/answer-requests/{request_id}/retry": ["post"],
    "/answers/{answer_id}": ["get"],
    "/answers/{answer_id}/regenerate": ["post"],
    "/answers/{answer_id}/evidence/{evidence_id}": ["get"],
    "/answers/{answer_id}/feedback": ["get", "put"],
    "/admin/feedback": ["get"],
    "/admin/feedback/{feedback_id}": ["patch"],
    "/documents": ["get", "post"],
    "/documents/{document_id}": ["get"],
    "/documents/{document_id}/process": ["post"],
    "/documents/{document_id}/deactivate": ["post"],
    "/documents/{document_id}/restore": ["post"],
    "/documents/{document_id}/revoke": ["post"],
    "/corpus/releases": ["get", "post"],
    "/corpus/releases/{release_id}/activate": ["post"],
    "/corpus/releases/{release_id}/rollback": ["post"],
    "/configurations": ["get", "post"],
    "/capabilities": ["get"],
    "/health/live": ["get"],
    "/health/ready": ["get"],
    "/experiments": ["get", "post"],
    "/experiments/{run_id}": ["get"],
    "/experiments/{run_id}/freeze": ["post"],
    "/experiments/{run_id}/start": ["post"],
    "/experiments/{run_id}/cancel": ["post"],
    "/experiments/{run_id}/results": ["get"],
    "/experiments/{run_id}/export": ["get"],
}


def main():
    import re

    schemas = {}
    for name, cls in inspect.getmembers(models, inspect.isclass):
        if cls.__module__ == models.__name__ and issubclass(cls, models.Contract):
            schema = cls.model_json_schema(ref_template="#/components/schemas/{model}")
            schemas.update(schema.pop("$defs", {}))
            schemas[name] = schema
    paths = {}
    for route, methods in ROUTES.items():
        operations = {}
        for method in methods:
            operations[method] = {
                "summary": f"{method.upper()} {route}",
                "x-design-status": "planned",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {"name": name, "in": "path", "required": True, "schema": {"type": "string"}}
                    for name in re.findall(r"\{(\w+)\}", route)
                ],
                "responses": {
                    "200": {
                        "description": "Success envelope; full field and state contract in docs/foundation/api_contract.md"
                    },
                    "422": {"description": "Invalid input"},
                },
            }
            if method == "post" and route.endswith("/messages"):
                operations[method]["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ChatMessageCreate"}
                        }
                    },
                }
                operations[method]["responses"] = {
                    "202": {"description": "Persisted JobReceipt"},
                    "409": {"description": "Busy or conflicting request"},
                    "422": {"description": "Invalid input"},
                }
        paths["/api/v1" + route] = operations
    doc = {
        "openapi": "3.1.0",
        "info": {
            "title": "CS-30-1 design contract",
            "version": "5.0.0",
            "description": "Initial design only; runtime export replaces this artifact after implementation.",
        },
        "paths": paths,
        "components": {
            "schemas": schemas,
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
        },
    }
    (ROOT / "contracts/openapi.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False), encoding="utf-8"
    )
    fixture_path = ROOT / "contracts/fixtures/evidence.json"
    fixture = json.loads(fixture_path.read_text())
    fixture["payload"]["text_hash"] = hashlib.sha256(
        fixture["payload"]["text"].encode()
    ).hexdigest()
    fixture_path.write_text(json.dumps(fixture, indent=2), encoding="utf-8")
    print(f"Exported {len(paths)} designed routes and {len(schemas)} schemas")


if __name__ == "__main__":
    main()
