"""Migration and subsequent repository commands share a fresh interpreter."""

import os
from pathlib import Path
import subprocess
import sys


def test_migration_preserves_repository_command_import_precedence(postgres_url):
    root = Path(__file__).resolve().parents[2]
    program = (
        "from pathlib import Path\n"
        "from alembic.config import Config\n"
        "from alembic import command\n"
        "command.upgrade(Config('backend/alembic.ini'), 'head')\n"
        "import scripts\n"
        "from scripts.verify.all import source_snapshot\n"
        "assert Path(scripts.__file__).resolve() == Path('scripts/__init__.py').resolve()\n"
        "assert callable(source_snapshot)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=root,
        env={
            **os.environ,
            "DATABASE_URL": postgres_url,
            "PYTHONPATH": str(root) + os.pathsep + str(root / "backend"),
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
