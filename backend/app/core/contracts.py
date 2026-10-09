"""Publish the same structured errors that the exception handlers return."""

from contracts.http import ErrorEnvelope


def register_response_schemas(app):
    native_openapi = app.openapi

    def openapi():
        schema = native_openapi()
        errors = ErrorEnvelope.model_json_schema(ref_template="#/components/schemas/{model}")
        definitions = errors.pop("$defs", {})
        schema["components"]["schemas"].update(definitions)
        schema["components"]["schemas"]["ErrorEnvelope"] = errors
        for path, operations in schema["paths"].items():
            if not path.startswith("/api/v1/") or "/health/" in path:
                continue
            for method, operation in operations.items():
                if method not in {"get", "post", "put", "patch", "delete"}:
                    continue
                for code in (
                    "400",
                    "401",
                    "403",
                    "404",
                    "409",
                    "410",
                    "413",
                    "415",
                    "422",
                    "500",
                    "503",
                ):
                    operation["responses"][code] = {
                        "description": "Structured application error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
                            }
                        },
                    }
        return schema

    app.openapi = openapi
