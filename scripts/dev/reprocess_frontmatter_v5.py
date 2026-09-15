"""Plan, queue and inspect a separate four-book parser-v5 rebuild without activation."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.db.session import init_engine
from app.modules.identity.repository import get_user_by_email
from app.modules.knowledge import service
from app.modules.knowledge.models import CorpusRelease, ProcessingRun
from app.modules.answering.models import Job


ROOT = Path("evidence/openstax/v5")


def save(path, value, *, immutable=False):
    content = json.dumps(value, indent=2, ensure_ascii=False, default=str)
    if path.exists() and immutable:
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise RuntimeError(f"Immutable evidence already exists: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "queue", "status"))
    args = parser.parse_args()
    ROOT.mkdir(exist_ok=True)
    settings = Settings()
    engine = init_engine(settings.database_url)
    if engine.dialect.name != "postgresql":
        raise RuntimeError("This operation requires actual PostgreSQL")
    plan_path, registry_path = ROOT / "processing-plan.json", ROOT / "processing-registry.json"
    with Session(engine, expire_on_commit=False) as db:
        if args.action == "plan":
            db.execute(text("SET TRANSACTION READ ONLY"))
            if plan_path.exists():
                print("Existing immutable v5 plan retained")
                return
            source = json.loads(
                Path("evidence/openstax/processing-registry.json").read_text(encoding="utf-8")
            )
            books = []
            for book in source["books"]:
                old = db.get(ProcessingRun, book["processing_id"])
                if old.state != "ready" or service.digest(old.configuration) != old.config_hash:
                    raise RuntimeError(
                        "Prior reviewed processing is not ready with its exact configuration"
                    )
                proposed = {**old.configuration, "parser_revision": "pypdf_bookmarks_v5"}
                differences = [
                    k
                    for k in set(old.configuration) | set(proposed)
                    if old.configuration.get(k) != proposed.get(k)
                ]
                if differences != ["parser_revision"]:
                    raise RuntimeError(
                        "Only the parser revision may differ from the reviewed v4 configuration"
                    )
                books.append(
                    {
                        **book,
                        "prior_processing_id": old.id,
                        "prior_config_hash": old.config_hash,
                        "prior_configuration": old.configuration,
                        "proposed_configuration": proposed,
                        "proposed_config_hash": service.digest(proposed),
                        "changed_configuration_fields": differences,
                    }
                )
            value = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "planned_not_queued",
                "source_registry": "evidence/openstax/processing-registry.json",
                "purpose": "Correct synthetic frontmatter section labels; retain every existing source-specific review and image transcript.",
                "parser_revision": "pypdf_bookmarks_v5",
                "books": books,
                "activation": "No activation or historical record update is performed by this utility.",
            }
            value["plan_hash"] = service.digest(value)
            save(plan_path, value, immutable=True)
            print(
                json.dumps(
                    {
                        "status": value["status"],
                        "books": len(books),
                        "plan_hash": value["plan_hash"],
                    }
                )
            )
            return
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        if service.digest({k: v for k, v in plan.items() if k != "plan_hash"}) != plan["plan_hash"]:
            raise RuntimeError("Immutable v5 plan changed")
        if args.action == "queue":
            if registry_path.exists():
                raise RuntimeError(
                    "A v5 registry already exists; inspect status rather than requeue"
                )
            if service.DEFAULT_CONFIG["parser_revision"] != plan["parser_revision"]:
                raise RuntimeError("Current runtime does not match the planned parser")
            actor = get_user_by_email(db, "admin@example.com")
            if actor is None or actor.status != "active" or actor.role.name != "admin":
                raise RuntimeError("Active local administrator required")
            release_plan = json.loads(
                (ROOT / "release-configuration-plan.json").read_text(encoding="utf-8")
            )
            spec_path = Path(release_plan["configuration_path"])
            if (
                hashlib.sha256(spec_path.read_bytes()).hexdigest()
                != release_plan["configuration_file_sha256"]
            ):
                raise RuntimeError("The prepared release configuration changed")
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            baseline = db.get(CorpusRelease, release_plan["baseline_release_id"])
            if spec["values"] != {
                **baseline.configuration,
                "parser_revision": "pypdf_bookmarks_v5",
            }:
                raise RuntimeError(
                    "Only the parser revision may change in the new release configuration"
                )
            config = service.config_create(db, spec["kind"], spec["name"], spec["values"])
            books = []
            for book in plan["books"]:
                old = db.get(ProcessingRun, book["prior_processing_id"])
                if (
                    old.config_hash != book["prior_config_hash"]
                    or old.configuration != book["prior_configuration"]
                ):
                    raise RuntimeError("Historical source configuration changed")
                run, job = service.queue_process(
                    db,
                    book["document_id"],
                    actor.id,
                    book["proposed_configuration"],
                    exclusions=book["proposed_configuration"].get("exclusions", {}),
                )
                if (
                    run.id == old.id
                    or run.config_hash != book["proposed_config_hash"]
                    or run.document_version_id != old.document_version_id
                ):
                    raise RuntimeError("A distinct exactly planned processing run is required")
                books.append(
                    {
                        **{
                            k: v
                            for k, v in book.items()
                            if k not in ("prior_configuration", "proposed_configuration")
                        },
                        "processing_id": run.id,
                        "job_id": job.id,
                        "config_hash": run.config_hash,
                    }
                )
            db.commit()
            value = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "plan_hash": plan["plan_hash"],
                "configuration_id": config.id,
                "configuration": config.values,
                "configuration_file": spec_path.as_posix(),
                "configuration_file_sha256": release_plan["configuration_file_sha256"],
                "books": books,
            }
            save(registry_path, value, immutable=True)
            print(
                json.dumps(
                    {
                        "queued": [
                            {
                                "slug": b["slug"],
                                "processing_id": b["processing_id"],
                                "job_id": b["job_id"],
                            }
                            for b in books
                        ]
                    }
                )
            )
            return
        db.execute(text("SET TRANSACTION READ ONLY"))
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        results = []
        for book in registry["books"]:
            run, job = db.get(ProcessingRun, book["processing_id"]), db.get(Job, book["job_id"])
            row = {
                "slug": book["slug"],
                "processing_id": run.id,
                "state": run.state,
                "job_state": job.state,
                "counts": {k: v for k, v in run.counts.items() if k != "source_unit_hashes"},
                "error": run.error or job.error,
            }
            if run.state in ("ready", "quarantined"):
                save(
                    ROOT / f"{book['slug']}-quality.json",
                    service.processing_quality(db, run.id),
                    immutable=True,
                )
                save(
                    ROOT / f"{book['slug']}-diff.json",
                    service.processing_diff(db, book["prior_processing_id"], run.id),
                    immutable=True,
                )
            results.append(row)
        save(
            ROOT / "processing-status.json",
            {"observed_at": datetime.now(timezone.utc).isoformat(), "books": results},
        )
        print(json.dumps(results))


if __name__ == "__main__":
    main()
