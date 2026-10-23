"""Offline validation and authored mock execution; no live mode exists here."""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict, is_dataclass
import hashlib
from importlib.machinery import EXTENSION_SUFFIXES
from importlib.metadata import PackageNotFoundError, version as distribution_version
import json
from pathlib import Path, PurePosixPath
import stat
import re
import socket
import sys
import sysconfig
import urllib.request

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
BLOCKED = []
FROZEN_MANIFEST_SHA256 = None
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


def forbidden(*args, **kwargs):
    BLOCKED.append("transport")
    raise AssertionError("Offline matrix forbids transport")


def audit(event, args):
    if event in {
        "socket.connect",
        "socket.bind",
        "socket.getaddrinfo",
        "subprocess.Popen",
        "os.system",
    }:
        BLOCKED.append(event)
        raise AssertionError("Offline matrix forbids network and subprocesses")
    if event == "open":
        path, _, flags = args
        if isinstance(path, (str, bytes)) and flags & (1 | 2 | 64 | 512 | 1024):
            target = Path(path).resolve()
            if not target.is_relative_to(ROOT):
                BLOCKED.append("external_write")
                raise AssertionError("Offline matrix forbids writes outside its own folder")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def load(name):
    return json.loads(rooted_path(ROOT, name).read_bytes(), object_pairs_hook=reject_duplicate_keys)


def save(name, value):
    assert sha(rooted_path(ROOT, "manifest.json")) == FROZEN_MANIFEST_SHA256, (
        "Loaded manifest changed"
    )

    def authored_dataclass(item):
        if is_dataclass(item):
            return asdict(item)
        raise TypeError(f"Unsupported authored value: {type(item).__name__}")

    (ROOT / name).write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=authored_dataclass) + "\n",
        encoding="utf-8",
    )


def validate_manifest_paths(manifest, source_root):
    artifacts = manifest.get("input_artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(INPUT_ARTIFACTS):
        raise ValueError("Manifest must pin exactly the six authored input artifacts")
    if any(
        not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
        for value in artifacts.values()
    ):
        raise ValueError("Pin hashes must be lowercase 64-character SHA256 strings")
    for name in artifacts:
        rooted_path(ROOT, name)
    freeze = manifest.get("freeze")
    if not isinstance(freeze, dict):
        raise ValueError("Manifest freeze must be an object")
    paths = {}
    seen = set()
    for group in ("source_files", "prompt_files", "candidate_files"):
        rows = freeze.get(group)
        if not isinstance(rows, list):
            raise ValueError("Manifest pin groups must be lists")
        paths[group] = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
                raise ValueError("Pin records require exactly path and sha256")
            relative = row["path"]
            canonical_relative(relative)
            if relative in seen:
                raise ValueError("Duplicate source or prompt pin")
            seen.add(relative)
            if (
                not isinstance(row["sha256"], str)
                or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
            ):
                raise ValueError("Pin hashes must be lowercase 64-character SHA256 strings")
            rooted_path(source_root, relative)
            paths[group].append(relative)
    if paths["candidate_files"]:
        raise ValueError(
            "Use the explicit combined source root; historical override pins are excluded"
        )
    expected_sources, expected_prompts = source_inventory(source_root)
    _, expected_directories = import_root_inventory(source_root)
    directories = freeze.get("import_root_directories")
    if (
        not isinstance(directories, list)
        or any(
            not isinstance(name, str)
            or not name.isidentifier()
            or len(canonical_relative(name).parts) != 1
            for name in directories
        )
        or len(set(directories)) != len(directories)
        or sorted(directories) != expected_directories
    ):
        raise ValueError("Import-root module/package directory inventory changed")
    if set(paths["source_files"]) != set(expected_sources) or set(paths["prompt_files"]) != set(
        expected_prompts
    ):
        raise ValueError("Public source or prompt inventory changed: added or missing files")


def active_dependency_environment():
    prefix = checked_root(Path(sys.prefix))
    configured = sysconfig.get_paths()
    roots = {}
    for role in ("purelib", "platlib"):
        value = configured.get(role)
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise ValueError("Active interpreter dependency roots must be absolute directories")
        lexical = Path(value).absolute()
        if lexical == prefix or not lexical.is_relative_to(prefix):
            raise ValueError("Dependency roots must be strict descendants of active sys.prefix")
        root = checked_root(lexical)
        if root == prefix or not root.is_relative_to(prefix):
            raise ValueError("Dependency roots escaped active sys.prefix")
        roots[role] = root
    return prefix, roots


def validate_imported_origins(source_root, manifest):
    _, dependency_environment = active_dependency_environment()
    dependency_roots = set(dependency_environment.values())
    pinned = {row["path"] for row in manifest["freeze"]["source_files"]}
    for module in tuple(sys.modules.values()):
        origin = getattr(module, "__file__", None)
        if origin is None:
            continue
        lexical = Path(origin).absolute()
        dependency_root = next(
            (root for root in dependency_roots if lexical.is_relative_to(root)), None
        )
        if dependency_root is not None:
            rooted_path(dependency_root, lexical.relative_to(dependency_root).as_posix())
            continue
        if lexical.is_relative_to(source_root):
            relative = lexical.relative_to(source_root).as_posix()
            rooted_path(source_root, relative)
            if relative not in pinned:
                raise ValueError("Imported native module origin is not source-pinned")


def validate_inputs(manifest, sources, cases, rubrics, source_root, candidate_root):
    validate_manifest_paths(manifest, source_root)
    assert manifest["display_heading"] == "Review results"
    assert len(cases) == len(rubrics) == 12
    assert {row["id"] for row in cases} == {row["case_id"] for row in rubrics}
    assert len({row["id"] for row in cases}) == 12
    assert {row["route_id"] for row in manifest["preset_routes"]} == {
        "openai",
        "azure_openai",
        "anthropic",
        "gemini",
        "ollama",
        "deepseek",
        "custom",
        "mock",
        "protocol_local",
    }
    assert all(
        row["resolved_model_id"] is None and not row["access_verified"]
        for row in manifest["preset_routes"]
    )
    assert all(
        row["exact_account_available_model_id"] is None for row in manifest["vendor_candidates"]
    )
    assert manifest["review_provenance"]["human_review_status"] == "pending"
    assert manifest["review_provenance"]["semantic_quality_score"] is None
    assert not manifest["review_provenance"]["blind_human_review_claim"]
    for name, expected in manifest["input_artifacts"].items():
        assert sha(rooted_path(ROOT, name)) == expected, f"Input changed: {name}"
    for pin in manifest["freeze"]["source_files"] + manifest["freeze"]["prompt_files"]:
        assert sha(rooted_path(source_root, pin["path"])) == pin["sha256"], (
            f"Source changed: {pin['path']}"
        )
    for pin in manifest["freeze"]["candidate_files"]:
        assert sha(rooted_path(candidate_root, pin["path"])) == pin["sha256"], (
            f"Candidate changed: {pin['path']}"
        )
    for row in cases:
        copy = {key: value for key, value in row.items() if key != "input_sha256"}
        assert digest(copy) == row["input_sha256"]
        assert row["fixture_id"] in sources
        assert "rubric" not in row and "reference_answer" not in row
        assert row["human_review_status"] == "pending"
    for source in sources.values():
        assert hashlib.sha256(source["text"].encode()).hexdigest() == source["text_sha256"]
    budget = manifest["budgets"]
    stages = manifest["stages"]
    assert (
        sum(row.get("max_calls", 0) for row in stages)
        == budget["maximum_llm_or_counter_transport_attempts"]
    )
    assert (
        budget["maximum_transport_attempts_including_catalog"]
        == budget["maximum_llm_or_counter_transport_attempts"]
        + manifest["model_resolution"]["maximum_catalog_transport_attempts"]
    )
    assert (
        sum(row.get("max_active_seconds", 0) for row in stages) + 20 * 60
        == budget["maximum_total_serial_active_seconds_including_catalog"]
    )
    assert (
        sum(row.get("max_wall_seconds", 0) for row in stages)
        + manifest["model_resolution"]["catalog_max_wall_seconds"]
        == budget["maximum_total_live_wall_seconds_including_catalog"]
    )
    assert manifest["model_resolution"]["maximum_initial_catalog_transport_attempts"] == 1
    assert next(row for row in stages if row["id"] == "primary_smoke")["max_calls"] == 6
    assert (
        budget["maximum_reserved_combined_tokens_all_live_stages"]
        == budget["maximum_llm_or_counter_transport_attempts"]
        * budget["maximum_reserved_combined_input_output_tokens_per_transport"]
    )
    assert budget["actual_cost"] is None and not budget["unknown_usage_is_zero"]
    assert (
        budget["maximum_native_request_calls"] == 4
        and budget["maximum_provider_timeout_seconds"] == 60
    )


def score_proxy(response, rubric, evidence_ids, ChatResponseV1):
    if response is None:
        return {
            "contract_valid": False,
            "response_type_matches_intended_behavior": False,
            "deterministic_proxy_pass": False,
            "semantic_score": None,
            "human_rating": None,
        }
    try:
        ChatResponseV1.model_validate(response)
        valid = True
    except ValueError:
        valid = False
    body = response.get("answer_text", "") + " " + (response.get("short_answer") or "")
    text = body.casefold()
    facts = [
        any(re.search(r"\b" + re.escape(term.casefold()) + r"\b", text) for term in group)
        for group in rubric["required_text_groups"]
    ]
    forbidden = [
        pattern for pattern in rubric["forbidden_patterns"] if re.search(pattern, body, re.I)
    ]
    citations = response.get("citations", [])
    citation_valid = isinstance(citations, list) and set(citations).issubset(evidence_ids)
    if rubric["answer_requires_citation"]:
        citation_valid = citation_valid and bool(citations)
    type_match = response.get("response_type") == rubric["expected_response_type"]
    refusal_match = (
        rubric["expected_refusal_reason"] is None
        or response.get("refusal_reason") == rubric["expected_refusal_reason"]
    )
    return {
        "contract_valid": valid,
        "response_type_matches_intended_behavior": type_match,
        "required_text_group_results": facts,
        "forbidden_pattern_matches": forbidden,
        "citation_membership_valid": citation_valid,
        "refusal_reason_matches": refusal_match,
        "deterministic_proxy_pass": bool(
            valid
            and type_match
            and all(facts)
            and not forbidden
            and citation_valid
            and refusal_match
        ),
        "semantic_score": None,
        "human_rating": None,
        "scope": "Lexical/contract proxy on authored mock output; no learned-model quality claim",
    }


def main():
    global ROOT, FROZEN_MANIFEST_SHA256
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--capture-requests", action="store_true")
    args = parser.parse_args()
    source_root = candidate_root = native_root = checked_root(args.source_root)
    ROOT = checked_root(args.run_dir)
    if ROOT.is_relative_to(source_root):
        raise ValueError("Keep generated results outside the captured source root")
    if any(
        (ROOT / name).exists()
        for name in ("validation_receipt.json", "mock_dryrun.json", "prepared_requests.json")
    ):
        raise ValueError("Use a new frozen run directory; never rewrite a previous result")
    sys.addaudithook(audit)
    socket.create_connection = forbidden
    urllib.request.urlopen = forbidden
    manifest_bytes = rooted_path(ROOT, "manifest.json").read_bytes()
    FROZEN_MANIFEST_SHA256 = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes, object_pairs_hook=reject_duplicate_keys)
    validate_manifest_paths(manifest, source_root)
    active_prefix, dependency_roots = active_dependency_environment()
    script_root = checked_root(Path(__file__).absolute().parent)
    assert (
        sha(rooted_path(script_root, Path(__file__).name))
        == manifest["input_artifacts"]["validate_dryrun.py"]
    ), "Executing validator differs from the frozen validator"
    sources = {row["id"]: row for row in load("fixtures.json")["sources"]}
    cases = load("cases.json")["cases"]
    rubric_bundle = load("rubrics.json")
    rubrics = {row["case_id"]: row for row in rubric_bundle["rubrics"]}
    validate_inputs(manifest, sources, cases, list(rubrics.values()), source_root, candidate_root)
    override = {row["path"]: row["sha256"] for row in manifest["freeze"]["candidate_files"]}
    for pin in manifest["freeze"]["source_files"] + manifest["freeze"]["prompt_files"]:
        assert sha(rooted_path(native_root, pin["path"])) == override.get(
            pin["path"], pin["sha256"]
        ), f"Native snapshot drift: {pin['path']}"
    for path, expected in override.items():
        assert sha(rooted_path(native_root, path)) == expected
    sys.path.insert(0, str(native_root))
    cache_prefix = ROOT / "_disabled_bytecode_cache"
    try:
        no_reparse(cache_prefix)
    except FileNotFoundError:
        pass
    else:
        raise ValueError("Offline imports require a fresh owned bytecode prefix")
    sys.pycache_prefix = str(cache_prefix)
    from contracts.models import ChatResponseV1, EvidenceSnapshot, ReadingContext
    from conversation import query_v21, query_v22, practice_context
    from generation import GenerationRequest, GenerationService, ModelConfig
    from generation import adapters, probes
    from generation.providers import payload
    from generation.teaching_plan_v6 import freeze_generation_policy

    validate_imported_origins(source_root, manifest)
    assert (active_prefix, dependency_roots) == active_dependency_environment(), (
        "Active interpreter dependency environment changed"
    )

    adapters.open_provider = forbidden
    adapters.LLMAdapter._call = forbidden
    observed = []
    native_generate = adapters.LLMAdapter.generate

    def capture(self, messages, **kwargs):
        assert self.config.provider == "mock"
        observed.append(
            {
                "messages": deepcopy(messages),
                "schema": kwargs.get("response_schema"),
                "schema_name": kwargs.get("response_schema_name"),
            }
        )
        return native_generate(self, messages, **kwargs)

    adapters.LLMAdapter.generate = capture
    wire_shapes = []
    for route in manifest["preset_routes"]:
        config = ModelConfig(
            provider=route["provider"],
            model="authored-wire-shape-fixture",
            structured_output_mode=route["source_structured_output_mode"],
            tokenizer_provider="estimate",
            base_url=route["source_preset_base_url"],
            auth_header=route["source_auth_header"],
        )
        config.validate()
        body = payload(
            config,
            [{"role": "user", "content": "Authored offline wire shape only"}],
            ChatResponseV1.model_json_schema(),
            "chat_response_v1",
        )
        wire_shapes.append(
            {
                "route_id": route["route_id"],
                "provider": route["provider"],
                "wire_payload_sha256": digest(body),
                "status": "offline_shape_compiled",
                "resolved_model_id": None,
                "live_connectivity_tested": False,
            }
        )
    mock_config = ModelConfig(
        provider="mock", model="authored-extractive-v1", tokenizer_provider="estimate", seed=None
    )
    compatibility = []
    for role in ("answer", "checker"):
        for tier in ("basic", "structured", "project"):
            description = probes.description(mock_config, tier, role)
            result = probes.run(description, api_key=None, timeout_seconds=1)
            assert result.error is None, f"Authored mock probe failed: {role}/{tier}"
            compatibility.append(
                {
                    "role": role,
                    "tier": tier,
                    "metadata": description["metadata"],
                    "result": result,
                    "observed_mode": "explicit_authored_mock",
                    "live_provider_or_semantic_checker_tested": False,
                }
            )
    prepared_requests, records = [], []
    for case in cases:
        source = sources[case["fixture_id"]]
        text = source["text"]
        chunk_id = "synthetic_" + source["id"]
        evidence = EvidenceSnapshot(
            evidence_id="ev_001",
            chunk_id=chunk_id,
            asset_id=chunk_id,
            processing_id=chunk_id,
            source_title=source["title"],
            section=source["section"],
            pages=[1],
            locator="Authored synthetic fixture, page 1",
            text=text,
            text_hash=source["text_sha256"],
            context_order=1,
        ).model_dump()
        mapping = {
            chunk_id: {
                "document_version_id": "synthetic_version_v1",
                "processing_id": chunk_id,
                "asset_id": chunk_id,
                "chunk_text": text,
                "chunk_hash": source["text_sha256"],
                "units": [
                    {
                        "id": "synthetic_unit",
                        "page": 1,
                        "cleaned_text": text,
                        "text_hash": source["text_sha256"],
                    }
                ],
                "spans": [
                    {
                        "unit_id": "synthetic_unit",
                        "page": 1,
                        "start": 0,
                        "end": len(text),
                        "chunk_start": 0,
                        "chunk_end": len(text),
                    }
                ],
            }
        }
        reading = None
        if case["reader_selection"]:
            ReadingContext(
                scope="chapter",
                document_id=chunk_id,
                source_unit_id="synthetic_unit",
                selection={"start": 0, "end": len(text), "text": text},
            )
            reading = {
                "version": "authored_frozen_selection_v1",
                "release_id": "synthetic_release",
                "scope": "chapter",
                "document_id": chunk_id,
                "source_unit_id": "synthetic_unit",
                "section": source["section"],
                "scope_hash": source["text_sha256"],
                "selection": {"start": 0, "end": len(text), "text": text},
            }
        for producer in (query_v21, query_v22):
            prepared = producer.prepare_query(case["question"], case["history"]).model_dump()
            teaching = None
            if reading:
                prepared.update(
                    standalone_query=case["question"] + "\nTextbook section: " + source["section"],
                    needs_clarification=False,
                    intent="factual",
                    topic_relation="new_topic",
                    fallback_reason="verified_reading_selection",
                )
            understanding = producer.describe_requirements(
                case["question"], prepared, case["history"]
            )
            if case["practice_public_context"]:
                teaching = {
                    "turn_role": "user_question",
                    "teaching_mode": "hint",
                    "help_level": 1,
                    "current_problem": case["practice_public_context"]["prompt"],
                    "practice_context": deepcopy(case["practice_public_context"]),
                }
                prepared, understanding = practice_context.resolve(
                    case["question"],
                    prepared,
                    teaching,
                    policy=practice_context.VERSION,
                    preparation_version=producer.VERSION,
                )
            request = GenerationRequest(
                request_id="mock_" + case["id"] + "_" + producer.VERSION,
                mode="interactive_chat",
                condition="E1",
                question=case["question"],
                evidence=[evidence],
                history=case["history"],
                prepared_query=prepared,
                understanding=understanding,
                config=mock_config,
                enhancement_version="learning_enhancement_v1",
                reliability_policy="evidence_reliability_v5",
                generation_policy=freeze_generation_policy(),
                generation_context_policy="complementary_context_v2",
                source_block_policy="raw_definition_block_partition_v2",
                provider_output_policy="json_field_contract_v2",
                source_map=mapping,
                reading_context=reading,
                teaching_context=teaching,
            )
            frozen = asdict(request)
            assert "private_reference_answers" not in repr(frozen)
            assert "50 kPa" not in json.dumps(frozen), (
                "Evaluator reference leaked into generator input"
            )
            prepared_requests.append(
                {
                    "case_id": case["id"],
                    "variant": producer.VERSION,
                    "request_sha256": digest(frozen),
                    "request": frozen,
                }
            )
            observed.clear()
            outcome = GenerationService().generate(request)
            records.append(
                {
                    "case_id": case["id"],
                    "variant": producer.VERSION,
                    "response": outcome.response,
                    "error": outcome.error,
                    "response_origin": outcome.response_origin,
                    "model_mode": outcome.model_mode,
                    "native_budget": outcome.budget,
                    "native_token_budget": outcome.token_budget,
                    "runtime_reported_mock_usage": outcome.usage,
                    "actual_live_provider_usage": None,
                    "actual_live_provider_cost": None,
                    "science_requirement_ids": [
                        row["id"] for row in understanding["required_knowledge"]
                    ],
                    "presentation_requests": understanding.get("presentation_requests", []),
                    **(
                        {
                            "native_messages": outcome.messages,
                            "captured_mock_calls": deepcopy(observed),
                        }
                        if args.capture_requests
                        else {}
                    ),
                    "proxy_review": score_proxy(
                        outcome.response, rubrics[case["id"]], {"ev_001"}, ChatResponseV1
                    ),
                    "semantic_review": {
                        "status": "not_executed",
                        "reviewer_kind": None,
                        "score": None,
                    },
                    "human_review": {"status": "pending", "members": []},
                }
            )
    # Freeze expected authored mock limits; do not make failed quality proxies pass.
    for variant in (query_v21.VERSION, query_v22.VERSION):
        by_case = {row["case_id"]: row for row in records if row["variant"] == variant}
        assert by_case["S01"]["response"]["response_type"] == "answer"
        for identifier in ("S02", "S03", "S04", "S06", "S07"):
            assert by_case[identifier]["response"]["refusal_reason"] == "INSUFFICIENT_EVIDENCE"
        assert by_case["S09"]["response"]["response_type"] == "clarification"
        assert by_case["S09"]["native_budget"]["consumed_calls"] == 0
        assert by_case["S11"]["error"]["code"] == "SEMANTIC_CHECK_UNAVAILABLE"
        assert by_case["S11"]["native_budget"]["consumed_calls"] == 0
        restatement = next(
            row
            for row in prepared_requests
            if row["case_id"] == "S10" and row["variant"] == variant
        )
        assert (
            restatement["request"]["prepared_query"]["fallback_reason"]
            == "verified_whole_answer_restatement_v1"
        )
        assert not restatement["request"]["prepared_query"]["needs_clarification"]
    moved = next(
        row for row in records if row["case_id"] == "S02" and row["variant"] == query_v22.VERSION
    )
    assert moved["science_requirement_ids"] == ["requirement_02"]
    assert len(moved["presentation_requests"]) == 1
    # Negative controls exercise the frozen checks and evaluator separation.
    altered = deepcopy(cases)
    altered[0]["question"] += " altered"
    try:
        validate_inputs(
            manifest, sources, altered, list(rubrics.values()), source_root, candidate_root
        )
    except AssertionError:
        input_tamper_rejected = True
    else:
        raise AssertionError("Input tamper was accepted")
    citation = adapters.chat_value(
        "answer", "Photosynthesis captures light energy in sugars. [ev_999]", citations=["ev_999"]
    )
    assert not score_proxy(citation, rubrics["S01"], {"ev_001"}, ChatResponseV1)[
        "deterministic_proxy_pass"
    ]
    leaked = adapters.chat_value(
        "answer",
        "Pressure multiplied by volume remains constant; the answer is 50 kPa. [ev_001]",
        citations=["ev_001"],
    )
    assert not score_proxy(leaked, rubrics["S11"], {"ev_001"}, ChatResponseV1)[
        "deterministic_proxy_pass"
    ]
    for equivalent in ("50000 Pa", "0.05 MPa", "fifty kilopascals", "half the original pressure"):
        alternate = adapters.chat_value(
            "answer",
            "Pressure multiplied by volume remains constant; the answer is "
            + equivalent
            + ". [ev_001]",
            citations=["ev_001"],
        )
        assert not score_proxy(alternate, rubrics["S11"], {"ev_001"}, ChatResponseV1)[
            "deterministic_proxy_pass"
        ]
    assert not BLOCKED
    validate_inputs(manifest, sources, cases, list(rubrics.values()), source_root, candidate_root)
    validate_imported_origins(source_root, manifest)
    assert (active_prefix, dependency_roots) == active_dependency_environment(), (
        "Active interpreter dependency environment changed"
    )
    for pin in manifest["freeze"]["source_files"] + manifest["freeze"]["prompt_files"]:
        assert sha(rooted_path(native_root, pin["path"])) == override.get(
            pin["path"], pin["sha256"]
        )
    for path, expected in override.items():
        assert sha(rooted_path(native_root, path)) == expected
    save(
        "prepared_requests.json",
        {
            "scope": "Native deterministic preparation and public generator inputs; no evaluator references",
            "full_capture_requested": args.capture_requests,
            "requests": prepared_requests
            if args.capture_requests
            else [
                {key: value for key, value in row.items() if key != "request"}
                for row in prepared_requests
            ],
        },
    )
    save(
        "mock_dryrun.json",
        {
            "display_heading": "Review results",
            "run_kind": "offline_authored_mock",
            "live_provider_calls": 0,
            "wire_shapes": wire_shapes,
            "compatibility_probes": compatibility,
            "records": records,
            "blocked_attempts": BLOCKED,
            "semantic_quality_score": None,
            "human_review_status": "pending",
            "input_tamper_rejected": input_tamper_rejected,
            "wrong_citation_and_hint_answer_leak_rejected": True,
        },
    )
    save(
        "validation_receipt.json",
        {
            "version": "offline_matrix_validation_v1",
            "status": "passed",
            "manifest_sha256": FROZEN_MANIFEST_SHA256,
            "cases": len(cases),
            "prepared_native_requests": len(records),
            "preset_and_local_wire_shapes": len(wire_shapes),
            "explicit_mock_compatibility_probes": len(compatibility),
            "live_provider_calls": 0,
            "blocked_attempts": BLOCKED,
            "source_hashes_verified_before_and_after": True,
            "exact_source_prompt_inventory_verified": True,
            "canonical_rooted_pins_verified": True,
            "imported_native_origins_pinned": True,
            "actual_live_usage": None,
            "actual_live_cost": None,
            "human_review_status": "pending",
            "source_default_preparation_policy": manifest["freeze"][
                "source_default_preparation_policy"
            ],
            "offline_environment": {
                "python_version": sys.version,
                "python_executable_sha256": sha(Path(sys.executable)),
                "active_interpreter_prefix": str(active_prefix),
                "active_dependency_roots": {
                    role: str(path) for role, path in dependency_roots.items()
                },
                "dependency_origin_policy": "Only active sysconfig purelib/platlib roots strictly within active sys.prefix are dependency origins; regular-file and reparse guards still apply",
                "pydantic_version": distribution_version("pydantic"),
                "mock_counter": "Explicit source-pinned estimate; no provider token count or external tokenizer used",
                "module_origins": {
                    module.__name__: str(Path(module.__file__).resolve().relative_to(source_root))
                    for module in (query_v21, query_v22, practice_context, adapters, probes)
                },
            },
            "script_sha256": sha(Path(__file__)),
            "artifacts": {
                name: sha(ROOT / name)
                for name in (
                    "fixtures.json",
                    "cases.json",
                    "rubrics.json",
                    "prepared_requests.json",
                    "mock_dryrun.json",
                )
            },
        },
    )
    print(
        json.dumps(
            {
                "validated_cases": 12,
                "native_mock_requests": 24,
                "offline_wire_shapes": 9,
                "explicit_mock_probes": 6,
                "live_provider_calls": 0,
                "blocked_attempts": BLOCKED,
            }
        )
    )


if __name__ == "__main__":
    main()
