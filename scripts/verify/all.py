"""Run the repeatable mock software gate; no paid provider calls are made."""

import argparse
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]


def source_snapshot():
    """Tie a gate to unchanged executable sources, fixtures and configuration."""
    values = {}
    for directory in (
        "backend",
        "contracts",
        "conversation",
        "evaluation",
        "generation",
        "personalisation",
        "pipelines",
        "retrieval",
        "scripts",
        "tests",
        "configs",
        "frontend/src",
        "frontend/tests",
        "frontend/scripts",
        ".github",
    ):
        for path in (ROOT / directory).rglob("*"):
            if not path.is_file() or any(
                part in {"__pycache__", "private_runs", "exports", "results"} for part in path.parts
            ):
                continue
            if path.suffix not in {
                ".py",
                ".ts",
                ".tsx",
                ".css",
                ".json",
                ".yaml",
                ".yml",
                ".txt",
                ".md",
                ".mjs",
                ".ps1",
                ".ini",
                ".html",
                ".mako",
            }:
                continue
            if path.suffix == ".md" and not path.is_relative_to(ROOT / "generation/prompts"):
                continue
            # Foundation regenerates only these schema exports. OpenAPI remains
            # a stable input because the contracts stage runs without --write.
            if path.is_relative_to(ROOT / "contracts/schemas"):
                continue
            values[path.relative_to(ROOT).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    for path in [
        *ROOT.glob("requirements*.lock"),
        ROOT / "pyproject.toml",
        ROOT / "pytest.ini",
        ROOT / "frontend/package-lock.json",
        ROOT / "frontend/package.json",
        ROOT / "frontend/vite.config.ts",
        ROOT / "frontend/tsconfig.json",
        ROOT / "frontend/index.html",
        ROOT / "frontend/nginx.conf",
        ROOT / "frontend/playwright.config.ts",
        ROOT / "evaluation/enhancement/highlight_review.README.md",
        ROOT / "docs/execution/tasks.json",
        ROOT / "docs/execution/acceptance.json",
        ROOT / "docs/execution/reporting_plan.json",
        ROOT / "docs/execution/ui_acceptance.json",
        ROOT / "evidence/openstax/v5/retrieval-verification.json",
        ROOT / "backend/Dockerfile",
        ROOT / "frontend/Dockerfile",
        ROOT / ".env.example",
        *ROOT.glob("compose*.yaml"),
    ]:
        values[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
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
    ):
        path = ROOT / "docs/foundation" / f"{name}.md"
        values[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for resource in ("cl100k_base", "o200k_base"):
        url = f"https://openaipublic.blob.core.windows.net/encodings/{resource}.tiktoken"
        path = ROOT / "artifacts/tiktoken" / hashlib.sha1(url.encode()).hexdigest()
        values[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["mock"], required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/final")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Gate evidence must remain within the project")
    output.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()
    before = source_snapshot()
    environment = {
        **os.environ,
        "MODEL_MODE": "mock",
        "TIKTOKEN_CACHE_DIR": str(ROOT / "artifacts/tiktoken"),
        "PYTHONPATH": os.pathsep.join([str(ROOT), str(ROOT / "backend")]),
    }
    if not environment.get("TEST_DATABASE_SERVER"):
        configured_url = environment.get("DATABASE_URL") or dotenv_values(ROOT / ".env").get(
            "DATABASE_URL"
        )
        if configured_url:
            database = make_url(configured_url)
            if database.get_backend_name() == "postgresql":
                # The test fixture creates/drops only a random cs30_test_* DB.
                # Use the local server's actual port; never print its credential.
                environment["TEST_DATABASE_SERVER"] = (
                    database.set(database="").render_as_string(hide_password=False).rstrip("/")
                )
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    assert npm, "Node/npm is required for the complete software gate"
    commands = [
        (
            "python_quality",
            [
                sys.executable,
                "-m",
                "scripts.verify.python_quality",
                "--output",
                str(output / "python-quality"),
            ],
            ROOT,
        ),
        ("foundation", [sys.executable, "-m", "scripts.verify.foundation"], ROOT),
        ("contracts", [sys.executable, "-m", "scripts.verify.contracts"], ROOT),
        ("chat_scope", [sys.executable, "-m", "scripts.verify.chat_scope"], ROOT),
        (
            "python_tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=" + str(output / "pytest-temp"),
                "--junitxml=" + str(output / "pytest.xml"),
            ],
            ROOT,
        ),
        ("frontend_types", [npm, "run", "types:check"], ROOT / "frontend"),
        ("frontend_tests", [npm, "test"], ROOT / "frontend"),
        ("frontend_build", [npm, "run", "build"], ROOT / "frontend"),
    ]
    results = []
    for name, command, cwd in commands:
        print("Running " + name, flush=True)
        with (output / (name + ".log")).open("w", encoding="utf-8") as log:
            result = subprocess.run(
                command, cwd=cwd, env=environment, stdout=log, stderr=subprocess.STDOUT
            )
        results.append(
            {
                "name": name,
                "command": command,
                "exit_code": result.returncode,
                "log": str((output / (name + ".log")).relative_to(ROOT)),
            }
        )
    after = source_snapshot()
    changed = [
        path for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)
    ]
    (output / "source_snapshot.json").write_text(
        json.dumps({"before": before, "after": after, "changed_during_run": changed}, indent=2),
        encoding="utf-8",
    )
    result = {
        "mode": args.mode,
        "started_at": started_at,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed"
        if not changed and all(item["exit_code"] == 0 for item in results)
        else "failed",
        "source_files_unchanged": not changed,
        "changed_during_run": changed,
        "source_snapshot": (output / "source_snapshot.json").relative_to(ROOT).as_posix(),
        "checks": results,
        "separate_evidence_required": [
            "real browser responsive and lifecycle journeys",
            "clean Compose install",
            "backup restore",
            "live scientific evaluation",
            "human ratings and physical mobile keyboard",
        ],
    }
    (output / "software_gate.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
