"""Freeze a new provider-development run directory; never invoke live providers."""

from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import hashlib
from importlib.machinery import EXTENSION_SUFFIXES
import json
from pathlib import Path, PurePosixPath
import stat

CODE_ROOT = Path(__file__).resolve().parent
SOURCE_DIRECTORIES = (
    "contracts",
    "conversation",
    "generation",
    "retrieval",
    "personalisation",
    "backend/app/core",
    "backend/app/modules/answering",
    "backend/app/modules/model_settings",
)
EVALUATION_FILES = (
    "evaluation/runner.py",
    "evaluation/bridge.py",
    "evaluation/conversations/runner.py",
    "evaluation/conversations/http_backend.py",
)
INPUT_ARTIFACTS = (
    "fixtures.json",
    "cases.json",
    "rubrics.json",
    "manifest_template.json",
    "build_matrix.py",
    "validate_dryrun.py",
)


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def no_reparse(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(
        stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
    ):
        raise ValueError("Symlink, junction or reparse path is not accepted")
    return info


def checked_root(path):
    lexical = path.absolute()
    for ancestor in reversed((lexical, *lexical.parents)):
        no_reparse(ancestor)
    if not stat.S_ISDIR(lexical.lstat().st_mode):
        raise ValueError("Explicit root must be a regular directory")
    return lexical.resolve()


def canonical_relative(value):
    if not isinstance(value, str) or not value or any(char in value for char in "\\:\x00"):
        raise ValueError("Pin path must be a canonical Posix relative path")
    relative = PurePosixPath(value)
    if (
        not relative.parts
        or relative.is_absolute()
        or relative.as_posix() != value
        or any(part in {".", ".."} for part in relative.parts)
    ):
        raise ValueError("Pin path must be a canonical Posix relative path")
    return relative


def rooted_path(root, relative, *, directory=False):
    parts = canonical_relative(relative).parts
    target = root
    for index, part in enumerate(parts):
        target = target / part
        info = no_reparse(target)
        wants_directory = index < len(parts) - 1 or directory
        if not (stat.S_ISDIR(info.st_mode) if wants_directory else stat.S_ISREG(info.st_mode)):
            raise ValueError("Pin target must be a regular file within its explicit root")
    if not target.resolve().is_relative_to(root):
        raise ValueError("Pin target escaped its explicit root")
    return target


def source_inventory(root):
    sources, _ = import_root_inventory(root)
    sources = set(sources)
    for relative in SOURCE_DIRECTORIES:
        pending = [rooted_path(root, relative, directory=True)]
        while pending:
            directory = pending.pop()
            for entry in directory.iterdir():
                info = no_reparse(entry)
                if stat.S_ISDIR(info.st_mode):
                    if entry.name != "__pycache__":
                        pending.append(entry)
                elif stat.S_ISREG(info.st_mode) and entry.suffix.lower() == ".py":
                    sources.add(entry.relative_to(root).as_posix())
                elif stat.S_ISREG(info.st_mode) and entry.suffix.lower() in {".pyc", ".pyd", ".so"}:
                    raise ValueError("Unfrozen source-less or binary module is not accepted")
    for relative in EVALUATION_FILES:
        rooted_path(root, relative)
        sources.add(relative)
    prompts = []
    for entry in rooted_path(root, "generation/prompts", directory=True).iterdir():
        info = no_reparse(entry)
        if stat.S_ISREG(info.st_mode) and entry.suffix.lower() == ".txt":
            prompts.append(entry.relative_to(root).as_posix())
    return sorted(sources), sorted(prompts)


def import_root_inventory(root):
    sources, directories = [], []
    for entry in root.iterdir():
        if entry.name.startswith(".") or entry.name == "__pycache__":
            continue
        info = no_reparse(entry)
        if stat.S_ISREG(info.st_mode):
            if entry.suffix.lower() == ".py":
                sources.append(entry.name)
            elif entry.suffix.lower() in {".pyc", ".pyd", ".so"}:
                raise ValueError(
                    "Unfrozen import-root binary or source-less module is not accepted"
                )
        elif stat.S_ISDIR(info.st_mode) and entry.name.isidentifier():
            directories.append(entry.name)
            initializers = {"__init__.py", "__init__.pyc", "__init__.pyd", "__init__.so"} | {
                "__init__" + suffix for suffix in EXTENSION_SUFFIXES
            }
            for name in initializers:
                child = entry / name
                try:
                    child_info = no_reparse(child)
                except FileNotFoundError:
                    continue
                if stat.S_ISREG(child_info.st_mode):
                    if child.name.casefold() == "__init__.py":
                        sources.append(child.resolve().relative_to(root).as_posix())
                    elif child.suffix.lower() in {".pyc", ".pyd", ".so"}:
                        raise ValueError("Unfrozen source-less or binary package is not accepted")
    return sorted(sources), sorted(directories)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(root, name, value):
    (root / name).write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--inputs-dir", type=Path, default=CODE_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source, inputs = checked_root(args.source_root), checked_root(args.inputs_dir)
    code_root = checked_root(CODE_ROOT)
    output = args.output_dir.absolute()
    try:
        no_reparse(output)
    except FileNotFoundError:
        pass
    else:
        raise ValueError("Use a new output directory; never rewrite a previous frozen run")
    for ancestor in reversed(tuple(output.parents)):
        if ancestor.exists():
            no_reparse(ancestor)
    output = output.resolve()
    if output.exists():
        raise ValueError("Use a new output directory; never rewrite a previous frozen run")
    if output.is_relative_to(source):
        raise ValueError("Keep generated run directories outside the captured source root")
    required = ("fixtures.json", "cases.json", "rubrics.json", "manifest_template.json")
    values = {
        name: json.loads(
            rooted_path(inputs, name).read_bytes(), object_pairs_hook=reject_duplicate_keys
        )
        for name in required
    }
    manifest = deepcopy(values["manifest_template.json"])
    tree = ast.parse(
        rooted_path(source, "backend/app/modules/model_settings/service.py").read_text(
            encoding="utf-8"
        )
    )
    preset = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "presets"
    )
    definitions = ast.literal_eval(
        next(node.value for node in preset.body if isinstance(node, ast.Assign))
    )
    model_expression = next(
        value
        for node in ast.walk(preset)
        if isinstance(node, ast.Dict)
        for key, value in zip(node.keys, node.values)
        if isinstance(key, ast.Constant) and key.value == "model"
    )
    permitted = (ast.IfExp, ast.Compare, ast.Eq, ast.Constant, ast.Name, ast.Load)
    if any(not isinstance(node, permitted) for node in ast.walk(model_expression)):
        raise ValueError("Preset model expression needs a source-reviewed parser update")
    for route in manifest["preset_routes"]:
        if route["route_id"] == "protocol_local":
            continue
        row = next(value for value in definitions if value[0] == route["route_id"])
        route.update(
            display_name=row[1],
            provider=row[2],
            source_preset_base_url=row[3],
            requires_api_key=row[4],
            source_structured_output_mode=row[5],
            source_auth_header=row[6],
            resolved_model_id=None,
            configuration_id=None,
            credential_reference=None,
            connectivity_status="not_run",
            quality_participant_key=None,
            access_verified=False,
        )
        # Preset defaults are source configuration, never resolved account model IDs.
        route["source_preset_model_default"] = eval(
            compile(ast.Expression(model_expression), "<frozen-preset-model>", "eval"),
            {"__builtins__": {}},
            {"provider": row[2], "id": row[0]},
        )
        route["source_preset_default_is_account_access_claim"] = False
    config_tree = ast.parse(
        rooted_path(source, "backend/app/core/config.py").read_text(encoding="utf-8")
    )
    policy = next(
        ast.literal_eval(node.value)
        for node in ast.walk(config_tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "chat_query_preparation_policy"
    )
    manifest["prepared_source_state"] = {
        "source_default_preparation_policy": policy,
        "method": "Hash the explicit public source-root supplied to this build; no deployed state or historical runtime inference",
    }
    manifest["freeze"]["source_default_preparation_policy"] = policy
    pinned, prompts = source_inventory(source)
    _, import_directories = import_root_inventory(source)
    manifest["freeze"]["import_root_directories"] = import_directories
    manifest["freeze"]["source_files"] = [
        {"path": relative, "sha256": sha(rooted_path(source, relative))} for relative in pinned
    ]
    manifest["freeze"]["prompt_files"] = [
        {"path": relative, "sha256": sha(rooted_path(source, relative))} for relative in prompts
    ]
    manifest["freeze"]["candidate_files"] = []
    for relative in (
        "conversation/query_v21.py",
        "conversation/query_v22.py",
        "conversation/requirements_v7.py",
        "conversation/requirements_v8.py",
    ):
        rooted_path(source, relative)
    manifest["freeze"]["runtime_environment_resolution"] = (
        "Before live execution freeze Python version/executable hash, used distribution versions, tokenizer files/revision/counter metadata and loaded module origins; record actual provider usage separately. Offline validation records its actual environment."
    )
    output.mkdir(parents=True, exist_ok=False)
    for name in required:
        write(output, name, values[name])
    for name in ("build_matrix.py", "validate_dryrun.py"):
        (output / name).write_bytes(rooted_path(code_root, name).read_bytes())
    manifest["input_artifacts"] = {
        name: sha(output / name) for name in required + ("build_matrix.py", "validate_dryrun.py")
    }
    write(output, "manifest.json", manifest)
    print(
        json.dumps(
            {
                "cases": len(values["cases.json"]["cases"]),
                "source_default": policy,
                "source_files": len(manifest["freeze"]["source_files"]),
                "live_calls": 0,
                "manifest_sha256": sha(output / "manifest.json"),
            }
        )
    )


if __name__ == "__main__":
    main()
