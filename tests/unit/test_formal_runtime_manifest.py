from pathlib import Path
import pytest
from scripts.release.runtime_manifest import runtime_member, implementation_blockers, audit


@pytest.mark.parametrize(
    "name",
    [
        "tests/unit/test_x.py",
        "frontend/src/X.test.tsx",
        "frontend/node_modules/a.js",
        "backend/.env",
        "configs/private/key.key",
        "backend/data.sqlite",
        "development_support/provider.py",
        "../backend/app/x.py",
        "backend/scripts/seed.py",
        "backend/scripts/__init__.py",
        "backend/Dockerfile",
        "backend/docker-compose.yml",
        "backend/requirements.txt",
        "backend/pytest.ini",
        "backend/.gitignore",
    ],
)
def test_excludes_private_or_development_members(name):
    assert not runtime_member(Path(name))


@pytest.mark.parametrize(
    "name",
    [
        "backend/app/main.py",
        "frontend/dist/assets/app.js",
        "configs/production.env.example",
        "scripts/release/start_local.ps1",
        "backend/alembic/env.py",
        "backend/alembic.ini",
        "backend/README.md",
    ],
)
def test_keeps_supported_runtime_inputs(name):
    assert runtime_member(Path(name))


def test_executable_mock_blocks_but_historical_labels_remain_readable():
    assert implementation_blockers(
        Path("generation/adapters.py"), b"def mock_payload():\n return {}\n"
    )
    assert not implementation_blockers(Path("generation/types.py"), b'OLD_PROVIDER = "mock"\n')


def test_dry_run_fails_closed_without_building_archive(tmp_path):
    root = tmp_path / "runtime"
    (root / "generation").mkdir(parents=True)
    (root / "generation/provider.py").write_text("def mock_payload():\n return {}\n")
    result = audit(root)
    assert result["status"] == "BLOCKED"
    assert len(result["files"]) == 1 and len(result["blockers"]) == 1
    assert not list(root.rglob("*.zip"))
