"""Build a complete local runtime handover and eight disjoint assigned source packs."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from dotenv import dotenv_values
from scripts.release.package import included, ROOT, verify
from scripts.release.common import file_hash

MEMBERS = [
    (
        "Xianshu Zhang",
        "540612426",
        "INT",
        10,
        [1, 11, 12],
        "Integration, contracts, release and documentation",
    ),
    (
        "Hongle Yang",
        "540252369",
        "DAT",
        12,
        [],
        "Official sources, processing, quality and corpus publication",
    ),
    (
        "Chengzhou Liu",
        "540931958",
        "RET",
        11,
        [4],
        "Real embeddings, retrieval and contextual query preparation",
    ),
    (
        "Sijin Lu",
        "540627888",
        "GEN",
        11,
        [5],
        "Provider protocols, generation, token budgets and citation validation",
    ),
    (
        "Pengyuan Xia",
        "550267474",
        "PER",
        9,
        [7],
        "Learner preferences and independent presentation studies",
    ),
    (
        "Zeping Liao",
        "540626434",
        "BE",
        17,
        [2, 3, 8],
        "Accounts, model settings, durable chat, diagnostics and operations",
    ),
    (
        "Baiqing Huang",
        "540976443",
        "FE",
        12,
        [6],
        "Learner and administrator UI, sources and responsive interaction",
    ),
    (
        "Chong Zhang",
        "530668840",
        "QA",
        14,
        [9, 10],
        "Evaluation, regression verification and acceptance evidence",
    ),
]


def owner(path):
    stem = Path(path).stem
    if path.startswith("frontend/"):
        return 6
    if path.startswith(("backend/app/modules/knowledge/", "pipelines/")):
        return 1
    if path.startswith("backend/app/modules/experiment/"):
        return 7
    if path.startswith("backend/"):
        return 5
    if path == "conversation/query.py" or path.startswith("retrieval/"):
        return 2
    if path.startswith("conversation/"):
        return 5
    if path.startswith("generation/"):
        return 3
    if path.startswith("personalisation/"):
        return 4
    if path.startswith(("evaluation/", "configs/evaluation/")) or path == "requirements-sciq.lock":
        return 7
    if path.startswith("configs/corpus/") or path.startswith("requirements-embeddings"):
        return 2
    if path.startswith("docs/delivery/by_owner/"):
        return next(i for i, m in enumerate(MEMBERS) if m[0].lower().replace(" ", "-") == stem)
    if path.startswith("docs/"):
        if any(k in stem for k in ("responsive", "ui_", "ui-", "frontend", "keyboard")):
            return 6
        if any(k in stem for k in ("profile", "personalisation")):
            return 4
        if any(
            k in stem
            for k in ("retrieval", "real_embeddings", "r0_review", "ret10", "chunking_comparison")
        ):
            return 2
        if any(
            k in stem
            for k in (
                "openstax",
                "corpus",
                "source_ocr",
                "source-inspection",
                "frontmatter",
                "data_rebuild",
            )
        ):
            return 1
        if any(k in stem for k in ("evaluation", "sciq", "test_plan", "evaluator")):
            return 7
        if any(
            k in stem
            for k in ("model-administration", "runbook", "data_model", "conversation_design")
        ):
            return 5
    if path.startswith("tests/"):
        if any(
            k in stem
            for k in (
                "model_settings",
                "failure_diagnostics",
                "operations",
                "runtime_faults",
                "account",
                "conversation",
            )
        ):
            return 5
        if any(k in stem for k in ("generation", "adapter", "mock_evidence", "provider")):
            return 3
        if any(k in stem for k in ("pipeline", "publisher", "source_recovery", "corpus_runtime")):
            return 1
        if "retrieval" in stem:
            return 2
        if "profile" in stem:
            return 4
        return 7
    if path.startswith("scripts/"):
        if any(
            k in stem for k in ("sciq", "live_answering", "chat_journeys", "all", "python_quality")
        ):
            return 7
        if any(
            k in stem for k in ("retrieval", "e5", "prepare_r3", "compare_chunking", "r0_review")
        ):
            return 2
        if any(
            k in stem
            for k in (
                "openstax",
                "publisher",
                "ocr",
                "transcription",
                "frontmatter",
                "supplement",
                "chemistry",
                "anatomy",
            )
        ):
            return 1
        if stem in {
            "backup",
            "restore",
            "common",
            "worker_interruption",
            "restored_source_visibility",
            "chat_performance",
        }:
            return 5
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--resources", type=Path, required=True)
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    full = destination / "CS30-1_Complete_Runnable_Project_20260913.zip"
    if full.exists():
        raise ValueError("Choose a new delivery directory; earlier deliveries are preserved")
    env = dotenv_values(ROOT / ".env")
    public_defaults = dotenv_values(ROOT / ".env.example")
    protected = [
        value.encode()
        for key, value in env.items()
        if value
        and len(value) >= 16
        and any(x in key for x in ("KEY", "PASSWORD", "TOKEN"))
        and (key == "LLM_API_KEY" or value != public_defaults.get(key))
    ]
    source_files = sorted(
        (p for p in ROOT.rglob("*") if p.is_file() and included(p)),
        key=lambda p: p.relative_to(ROOT).as_posix(),
    )
    # Public, dated evidence is included; raw deployment backups and private runs
    # are excluded by the source predicate and the explicit resource allowlist.
    entries = []
    assets = []
    required_resources = [
        "official-corpus/MANIFEST.json",
        "official-corpus/corpus.jsonl.gz",
        "huggingface/models--intfloat--e5-small-v2/snapshots/ffb93f3bd4047442299a41ebb6fa998a38507c52/model.safetensors",
        "huggingface/models--cross-encoder--ms-marco-MiniLM-L6-v2/snapshots/233902d25c440f23af6f7d6e94d2946bac0bee0a/model.safetensors",
        "huggingface/deepseek-v4-flash-0731-tokenizer/7872f01b1d1fe23eabc4c98b48bffcef5a386062/SOURCE_MANIFEST.json",
    ]
    if any(not (args.resources / item).is_file() for item in required_resources):
        raise ValueError("Required corpus or pinned model resources are missing")
    if not any(path.is_file() for path in (args.resources / "tiktoken").glob("*")):
        raise ValueError("The verified tiktoken cache is missing")
    for prefix, target in [
        ("official-corpus", "resources/official-corpus"),
        ("huggingface", "artifacts/huggingface"),
        ("tiktoken", "artifacts/tiktoken"),
    ]:
        root = args.resources / prefix
        for path in sorted(root.rglob("*")):
            if path.is_file():
                assets.append((path, target + "/" + path.relative_to(root).as_posix()))
    if not assets:
        raise ValueError("The complete delivery requires the real corpus and model resources")
    manifest = {
        "version": "cs30-complete-runnable-handover-v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "English source/docs/tests, four official books and source recovery artifacts, preserved real E5 releases, pinned E5/reranker/tokenizer assets. New local installation uses its own accounts and provider credentials.",
        "runtime": "Windows x64, Python3.13, Node/npm, Docker PostgreSQL, NVIDIA CUDA device for the preserved corpus configuration",
        "startup": "powershell -ExecutionPolicy Bypass -File scripts/release/start_local.ps1 -Install",
        "answer_model_mode": "New install starts explicit mock answers with real retrieval; administrator configures/tests/enables a live provider.",
        "exclusions": [
            "existing .env and secret/key files",
            "existing users/conversations/feedback and encrypted provider records",
            "private SciQ references and result exports",
            "installed dependencies and browser profiles",
        ],
        "files": [],
    }
    with zipfile.ZipFile(full, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=4) as archive:
        for path in source_files:
            value = path.read_bytes()
            relative = path.relative_to(ROOT).as_posix()
            if any(secret in value for secret in protected):
                raise ValueError("A deployment secret was detected in candidate file: " + relative)
            record = {
                "path": relative,
                "bytes": len(value),
                "sha256": hashlib.sha256(value).hexdigest(),
                "category": "source_and_public_evidence",
            }
            manifest["files"].append(record)
            archive.writestr("learning-assistant/" + relative, value)
            if relative.split("/", 1)[0] not in {"evidence", "artifacts"}:
                entries.append({**record, "owner_index": owner(relative)})
        for path, relative in assets:
            # Scan the explicitly allowed resources too, including binary assets,
            # with overlap so a secret crossing a read boundary is detected.
            overlap = max((len(value) for value in protected), default=1) - 1
            tail = b""
            with path.open("rb") as resource:
                while block := resource.read(1024 * 1024):
                    scan = tail + block
                    if any(secret in scan for secret in protected):
                        raise ValueError(
                            "A deployment secret was detected in resource: " + relative
                        )
                    tail = scan[-overlap:] if overlap else b""
            record = {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": file_hash(path),
                "category": "verified_runtime_resource",
            }
            manifest["files"].append(record)
            archive.write(path, "learning-assistant/" + relative, compress_type=zipfile.ZIP_STORED)
        archive.writestr(
            "learning-assistant/PACKAGE_MANIFEST.json", json.dumps(manifest, indent=2) + "\n"
        )
    verification = verify(full)
    archives = [
        {"path": full.name, "sha256": file_hash(full), "bytes": full.stat().st_size, **verification}
    ]
    inventory = {
        "schema": "eight-assigned-workstreams-v2",
        "created_at": manifest["created_at"],
        "scope": "Disjoint whole-file assignment; accountability is not a claim of independent personal authorship. Codex is the shared implementation executor.",
        "merge_order": [MEMBERS[i][0] for i in (0, 5, 1, 2, 4, 3, 6, 7)],
        "shared_runtime": full.name,
        "files": [{**entry, "owner": MEMBERS[entry["owner_index"]][0]} for entry in entries],
    }
    for index, (name, sid, prefix, count, chats, domain) in enumerate(MEMBERS):
        selected = [e for e in entries if e["owner_index"] == index]
        task_ids = [f"{prefix}-{number:02}" for number in range(1, count + 1)] + [
            f"CHAT-{number:02}" for number in chats
        ]
        slug = name.replace(" ", "_")
        package = destination / f"CS30-1_{index + 1:02}_{slug}_20260913.zip"
        readme = f"# {name}: assigned development handover\n\nStudent ID: {sid}. Area: {domain}.\n\nThis package contains {len(selected)} assigned project files. Use the complete runnable package for shared infrastructure, dependencies, corpus and model assets. These eight module packages are disjoint contributions to one application.\n\nOriginal task IDs: {', '.join(task_ids)}. The authoritative current states and evidence are in `docs/execution/tasks.json`, `acceptance.json`, and `ui_acceptance.json` in the full project. Assignment records responsibility and review scope; Codex performed the shared implementation.\n\n## Integration\n\n1. Keep a copy of the complete project and its history.\n2. Review `OWNED_FILES.json` and copy `repo_files/` into a separate working checkout, preserving relative paths.\n3. Merge the eight packages in the order recorded in `EIGHT_MEMBER_INVENTORY.json`. Every source path has one owner.\n4. Install from the complete package with `scripts/release/start_local.ps1 -Install`. Configure a new provider through Administration > Models.\n5. Run the documented software checks and inspect the real-live evidence and outstanding independent review in the upgrade record.\n\nThe full package includes hashes for every source/resource. Keys and existing learner records are excluded. Member packages do not include duplicate shared model weights.\n"
        with zipfile.ZipFile(
            package, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as archive:
            archive.writestr(slug + "/README.md", readme)
            archive.writestr(
                slug + "/OWNED_FILES.json",
                json.dumps(
                    {
                        "owner": name,
                        "student_id": sid,
                        "domain": domain,
                        "task_ids": task_ids,
                        "files": selected,
                    },
                    indent=2,
                )
                + "\n",
            )
            for entry in selected:
                value = (ROOT / entry["path"]).read_bytes()
                if hashlib.sha256(value).hexdigest() != entry["sha256"]:
                    raise ValueError("Source changed after full-package freeze: " + entry["path"])
                archive.writestr(slug + "/repo_files/" + entry["path"], value)
        with zipfile.ZipFile(package) as archive:
            for entry in selected:
                if (
                    hashlib.sha256(archive.read(slug + "/repo_files/" + entry["path"])).hexdigest()
                    != entry["sha256"]
                ):
                    raise ValueError("Member package verification failed")
        archives.append(
            {
                "path": package.name,
                "sha256": file_hash(package),
                "bytes": package.stat().st_size,
                "assigned_files": len(selected),
                "owner": name,
                "status": "passed",
            }
        )
    if len(entries) != len({e["path"] for e in entries}):
        raise ValueError("Member paths overlap")
    inventory["owner_counts"] = {
        MEMBERS[i][0]: n for i, n in Counter(e["owner_index"] for e in entries).items()
    }
    (destination / "EIGHT_MEMBER_INVENTORY.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "PACKAGE_VERIFICATION.json").write_text(
        json.dumps(
            {
                "created_at": manifest["created_at"],
                "source_count": len(entries),
                "member_union_exact": True,
                "archives": archives,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "archives": len(archives),
                "source_files": len(entries),
                "full_package": str(full),
                "full_bytes": full.stat().st_size,
            }
        )
    )


if __name__ == "__main__":
    main()
