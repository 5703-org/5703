"""Formal local deployment must not inherit executable development defaults."""
from pathlib import Path

import yaml

from scripts.release.runtime_manifest import runtime_member

ROOT = Path(__file__).resolve().parents[2]


def test_formal_membership_excludes_the_development_stack():
    assert not runtime_member(Path("compose.yaml"))
    assert runtime_member(Path("compose.local.yaml"))


def test_local_database_requires_explicit_operator_configuration():
    value = yaml.safe_load((ROOT / "compose.local.yaml").read_text())
    assert set(value["services"]) == {"db"}
    db = value["services"]["db"]
    assert db["environment"]["POSTGRES_PASSWORD"].startswith("${POSTGRES_PASSWORD:?")
    assert db["ports"] == ["127.0.0.1:${POSTGRES_PORT:?Set the local database port}:5432"]
    assert db["volumes"] == ["pgdata:/var/lib/postgresql/data"]
    assert not any(key in db["environment"] for key in ("SECRET_KEY", "LLM_API_KEY", "MODEL_MODE"))


def test_formal_launcher_selects_only_the_database_template():
    text = (ROOT / "scripts/release/start_local.ps1").read_text()
    assert "-f compose.local.yaml up -d db --wait" in text
    assert "-f compose.yaml" not in text
    # The historical developer stack remains available outside formal membership.
    assert (ROOT / "compose.yaml").is_file()
