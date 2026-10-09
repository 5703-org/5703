"""Passing subprocesses cannot hide changes to executable runtime resources."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.verify import all as software_gate


@pytest.fixture
def gate_checkout(tmp_path, monkeypatch):
    monkeypatch.setattr(software_gate, "ROOT", tmp_path)
    monkeypatch.setattr(software_gate.shutil, "which", lambda command: "npm")
    monkeypatch.setenv("TEST_DATABASE_SERVER", "postgresql://unused-local-test")
    for relative in (
        "pyproject.toml",
        "pytest.ini",
        "frontend/package-lock.json",
        "frontend/package.json",
        "frontend/vite.config.ts",
        "frontend/tsconfig.json",
        "frontend/index.html",
        "frontend/nginx.conf",
        "frontend/playwright.config.ts",
        "backend/Dockerfile",
        "frontend/Dockerfile",
        ".env.example",
        "backend/alembic.ini",
        "backend/alembic/script.py.mako",
        "evaluation/enhancement/highlight_review.html",
        "evaluation/enhancement/highlight_review.README.md",
        "docs/execution/tasks.json",
        "docs/execution/acceptance.json",
        "docs/execution/reporting_plan.json",
        "docs/execution/ui_acceptance.json",
        "evidence/openstax/v5/retrieval-verification.json",
        "contracts/openapi.json",
        "contracts/openapi.yaml",
        "artifacts/tiktoken/9b5ad71b2ce5302211f9c61530b329a4922fc6a4",
        "artifacts/tiktoken/fb374d419588a4632f3f557e76b4b70aebbca790",
        *(
            f"docs/foundation/{name}.md"
            for name in (
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
            )
        ),
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("initial runtime resource\n", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    "relative",
    [
        "pytest.ini",
        "backend/alembic.ini",
        "backend/alembic/script.py.mako",
        "evaluation/enhancement/highlight_review.html",
        "evaluation/enhancement/highlight_review.README.md",
        "frontend/index.html",
        "frontend/nginx.conf",
        "frontend/playwright.config.ts",
        "docs/execution/tasks.json",
        "docs/execution/acceptance.json",
        "docs/execution/reporting_plan.json",
        "docs/execution/ui_acceptance.json",
        "docs/foundation/requirements.md",
        "evidence/openstax/v5/retrieval-verification.json",
        "contracts/openapi.json",
        "contracts/openapi.yaml",
        "artifacts/tiktoken/9b5ad71b2ce5302211f9c61530b329a4922fc6a4",
    ],
)
def test_gate_rejects_changed_runtime_resource_despite_eight_passing_stages(
    gate_checkout, monkeypatch, relative
):
    def run(command, **kwargs):
        assert kwargs["env"]["TIKTOKEN_CACHE_DIR"] == str(gate_checkout / "artifacts/tiktoken")
        if command[-1] == "build":
            (gate_checkout / relative).write_text("changed during verification\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(software_gate.subprocess, "run", run)
    output = gate_checkout / "evidence/check"
    monkeypatch.setattr(sys, "argv", ["gate", "--mode", "mock", "--output", str(output)])
    with pytest.raises(SystemExit) as outcome:
        software_gate.main()
    assert outcome.value.code == 1
    report = json.loads((output / "software_gate.json").read_text(encoding="utf-8"))
    assert all(check["exit_code"] == 0 for check in report["checks"])
    assert report["status"] == "failed"
    assert report["changed_during_run"] == [relative]


def test_gate_allows_unchanged_runtime_resources_and_generated_schema_export(
    gate_checkout, monkeypatch
):
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(gate_checkout / "unused-external-tokenizer"))

    def run(command, **kwargs):
        assert kwargs["env"]["TIKTOKEN_CACHE_DIR"] == str(gate_checkout / "artifacts/tiktoken")
        if "scripts.verify.contracts" in command:
            schema = gate_checkout / "contracts/schemas/generated.json"
            schema.parent.mkdir(parents=True, exist_ok=True)
            schema.write_text("{}\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(software_gate.subprocess, "run", run)
    output = gate_checkout / "evidence/check"
    monkeypatch.setattr(sys, "argv", ["gate", "--mode", "mock", "--output", str(output)])
    with pytest.raises(SystemExit) as outcome:
        software_gate.main()
    assert outcome.value.code == 0
    report = json.loads((output / "software_gate.json").read_text(encoding="utf-8"))
    assert report["status"] == "passed" and report["source_files_unchanged"]
