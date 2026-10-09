"""Load the private authored study inventory outside application execution.

The team's research bundle provides private/question-catalogue.json. Public
runnable and GitHub contribution packages intentionally omit evaluation labels.
"""

import json
from pathlib import Path


def tasks(path: Path | None = None):
    source = path or Path(__file__).with_name("private") / "question-catalogue.json"
    if not source.is_file():
        raise ValueError("Restore the private research question catalogue before preparing a study")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("schema") != "week08_memory_v2_private_questions_v1":
        raise ValueError("Unsupported private question catalogue version")
    return payload["tasks"]


def generation_input(task):
    """Never send private references, expected sources or labels to a generator."""
    return {key: task[key] for key in ("id", "question", "turns")}
