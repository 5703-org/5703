"""Local operator entry points for migrations, seed, corpus and recovery."""

import argparse
import json
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import Settings
from app.db.session import init_engine
from app.modules.identity import repository
from app.modules.identity.models import Role, User, Workspace, StudentProfile
from app.core.security import hash_password
from app.modules.knowledge import service as knowledge
from app.modules.knowledge.models import *
from app.modules.answering.models import Job


def migrate():
    from alembic.config import Config
    from alembic import command

    path = Path(__file__).resolve().parents[1] / "alembic.ini"
    command.upgrade(Config(str(path)), "head")


def seed(db):
    workspace = repository.get_workspace_by_slug(db, "default")
    if not workspace:
        workspace = Workspace(name="Default Workspace", slug="default")
        db.add(workspace)
        db.flush()
    for name in ("admin", "student"):
        if not repository.get_role_by_name(db, name):
            db.add(Role(name=name, description=name.title()))
    db.flush()
    for email, name, role in [
        ("admin@example.com", "Demo Admin", "admin"),
        ("student@example.com", "Demo Learner", "student"),
        ("student2@example.com", "Second Demo Learner", "student"),
    ]:
        if not repository.get_user_by_email(db, email):
            user = User(
                email=email,
                full_name=name,
                hashed_password=hash_password("Passw0rd!"),
                role_id=repository.get_role_by_name(db, role).id,
                workspace_id=workspace.id,
            )
            db.add(user)
            db.flush()
            db.add(StudentProfile(user_id=user.id))
    knowledge.config_create(
        db, "retrieval", "Default authored mock corpus", knowledge.DEFAULT_CONFIG
    )
    if not db.get(ActiveCorpus, 1):
        db.add(ActiveCorpus(id=1))
    db.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    p = sub.add_parser("seed-demo")
    p.add_argument("--confirm-dev", action="store_true", required=True)
    p = sub.add_parser("ingest")
    p.add_argument("--manifest", required=True)
    p = sub.add_parser("corpus-build")
    p.add_argument("--config", required=True)
    for name in ("corpus-activate", "corpus-rollback"):
        p = sub.add_parser(name)
        p.add_argument("--release", required=True)
    p = sub.add_parser("jobs")
    p.add_argument("--recover-stale", action="store_true")
    p = sub.add_parser("job-inspect")
    p.add_argument("--job", required=True)
    p = sub.add_parser("job-retry")
    p.add_argument("--request", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--owner", required=True)
    p = sub.add_parser("account-create")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--role", choices=["admin", "student"], default="student")
    p.add_argument("--password-env", default="CS30_NEW_PASSWORD")
    p.add_argument("--admin", default="admin@example.com")
    p = sub.add_parser("account-update")
    p.add_argument("--email", required=True)
    p.add_argument("--version", required=True, type=int)
    p.add_argument("--status", choices=["active", "deactivated"])
    p.add_argument("--password-env")
    p.add_argument("--admin", default="admin@example.com")
    p = sub.add_parser("configuration-create")
    p.add_argument("--file", required=True)
    p.add_argument("--admin", default="admin@example.com")
    p = sub.add_parser("source-visibility")
    p.add_argument("--document", required=True)
    p.add_argument("--action", required=True, choices=["deactivate", "restore", "revoke"])
    p.add_argument("--admin", default="admin@example.com")
    p = sub.add_parser("feedback-review")
    p.add_argument("--feedback", required=True)
    p.add_argument("--state", required=True, choices=["pending", "reviewed", "actioned"])
    p.add_argument("--note", default="")
    p.add_argument("--issue")
    p.add_argument("--admin", default="admin@example.com")
    p = sub.add_parser("cleanup")
    p.add_argument("--plan")
    p.add_argument("--apply-manifest")
    p = sub.add_parser("processing-quality")
    p.add_argument("--processing", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("processing-diff")
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--output", required=True)
    args = parser.parse_args()
    settings = Settings()
    if args.command == "migrate":
        migrate()
        return
    engine = init_engine(settings.database_url)
    with sessionmaker(bind=engine, expire_on_commit=False)() as db:
        from app.operations import admin_user, password_from_env

        if args.command == "seed-demo":
            if settings.env not in ("dev", "test", "demo"):
                raise SystemExit(
                    "Demo seeding is only available in development/test/demo environments"
                )
            seed(db)
            print("Development demo accounts seeded; repeated seed is idempotent.")
        elif args.command == "ingest":
            path = Path(args.manifest).resolve()
            manifest = json.loads(path.read_text(encoding="utf-8"))
            admin = repository.get_user_by_email(
                db, manifest.get("admin_email", "admin@example.com")
            )
            if not admin or admin.status != "active" or admin.role.name != "admin":
                raise SystemExit("An existing admin account is required")
            for asset in manifest["assets"]:
                source = (path.parent / asset["path"]).resolve()
                raw = source.read_bytes()
                import hashlib

                if asset.get("sha256") and asset["sha256"] != hashlib.sha256(raw).hexdigest():
                    raise SystemExit("Manifest source SHA-256 mismatch: " + source.name)
                if asset.get("size_bytes") is not None and asset["size_bytes"] != len(raw):
                    raise SystemExit("Manifest source size mismatch: " + source.name)
                doc, version, duplicate = knowledge.ingest(
                    db,
                    settings,
                    admin.id,
                    source.name,
                    raw,
                    asset["title"],
                    asset.get("edition", ""),
                    asset.get("source_url", ""),
                    asset.get("license", "Not specified"),
                )
                run, job = knowledge.queue_process(
                    db, doc.id, admin.id, asset.get("configuration"), asset.get("exclusions")
                )
                db.commit()
                print(
                    json.dumps(
                        {
                            "document_id": doc.id,
                            "version_id": version.id,
                            "processing_id": run.id,
                            "job_id": job.id,
                            "duplicate": duplicate,
                        }
                    )
                )
        elif args.command == "corpus-build":
            cfg = json.loads(Path(args.config).read_text())
            admin = repository.get_user_by_email(db, "admin@example.com")
            release, job = knowledge.queue_release(
                db,
                admin.id,
                cfg["processing_run_ids"],
                cfg.get("configuration_id"),
                cfg.get("name", "Corpus release"),
            )
            db.commit()
            print(json.dumps({"release_id": release.id, "job_id": job.id}))
        elif args.command in ("corpus-activate", "corpus-rollback"):
            knowledge.activate(db, args.release)
            db.commit()
            print("Activated " + args.release)
        elif args.command == "jobs":
            if args.recover_stale:
                from app.worker import recover_stale

                print(
                    json.dumps({"recovered": recover_stale(engine, settings.worker_stale_seconds)})
                )
            print(
                json.dumps(
                    [
                        {"id": j.id, "state": j.state, "kind": j.kind, "error": j.error}
                        for j in db.scalars(select(Job).order_by(Job.created_at.desc()).limit(100))
                    ]
                )
            )
        elif args.command == "job-inspect":
            from app.modules.answering.models import AnswerRequest, Attempt

            job = db.get(Job, args.job)
            if not job:
                raise SystemExit("Job not found")
            request = db.get(AnswerRequest, job.request_id) if job.request_id else None
            print(
                json.dumps(
                    {
                        "id": job.id,
                        "kind": job.kind,
                        "state": job.state,
                        "stage": job.stage,
                        "error": job.error,
                        "budget": request.budget if request else None,
                        "attempts": [
                            {
                                "id": a.id,
                                "sequence": a.sequence,
                                "phase": a.payload.get("phase"),
                                "stage": a.payload.get("stage"),
                                "error": a.payload.get("error"),
                            }
                            for a in db.scalars(
                                select(Attempt)
                                .where(Attempt.job_id == job.id)
                                .order_by(Attempt.sequence)
                            )
                        ],
                    }
                )
            )
        elif args.command == "job-retry":
            from app.modules.answering.service import retry

            owner = repository.get_user_by_email(db, args.owner)
            if not owner or owner.status != "active":
                raise SystemExit("An active request owner is required")
            print(json.dumps(retry(db, owner, args.request, args.key)))
        elif args.command == "account-create":
            from app.modules.identity.accounts import AccountCreate, create_user

            body = AccountCreate(
                email=args.email,
                full_name=args.name,
                role=args.role,
                password=password_from_env(args.password_env),
            )
            print(json.dumps(create_user(body, db, admin_user(db, args.admin))["data"]))
        elif args.command == "account-update":
            from app.modules.identity.accounts import AccountUpdate, update_user

            user = repository.get_user_by_email(db, args.email)
            if not user:
                raise SystemExit("Account not found")
            body = AccountUpdate(
                version=args.version,
                status=args.status,
                password=password_from_env(args.password_env) if args.password_env else None,
            )
            print(json.dumps(update_user(user.id, body, db, admin_user(db, args.admin))["data"]))
        elif args.command == "configuration-create":
            from app.modules.knowledge.router import ConfigInput, create_config

            body = ConfigInput.model_validate(
                json.loads(Path(args.file).read_text(encoding="utf-8"))
            )
            print(json.dumps(create_config(body, db, admin_user(db, args.admin))["data"]))
        elif args.command == "source-visibility":
            from app.modules.knowledge.router import change_visibility

            admin_user(db, args.admin)
            print(json.dumps(change_visibility(db, args.document, args.action)["data"]))
        elif args.command == "feedback-review":
            from app.modules.answering.router import ReviewInput, review

            body = ReviewInput(review_state=args.state, review_note=args.note, issue=args.issue)
            print(json.dumps(review(args.feedback, body, db, admin_user(db, args.admin))["data"]))
        elif args.command == "cleanup":
            from app.operations import cleanup_plan, apply_cleanup

            if bool(args.plan) == bool(args.apply_manifest):
                raise SystemExit("Choose --plan OUTPUT.json or --apply-manifest REVIEWED.json")
            if args.plan:
                result = cleanup_plan(db, settings)
                Path(args.plan).write_text(json.dumps(result, indent=2), encoding="utf-8")
                print(
                    json.dumps(
                        {
                            "dry_run": True,
                            "candidate_count": len(result["candidates"]),
                            "plan": args.plan,
                        }
                    )
                )
            else:
                print(
                    json.dumps(
                        apply_cleanup(
                            db,
                            settings,
                            json.loads(Path(args.apply_manifest).read_text(encoding="utf-8")),
                        )
                    )
                )
        elif args.command in ("processing-quality", "processing-diff"):
            result = (
                knowledge.processing_quality(db, args.processing)
                if args.command == "processing-quality"
                else knowledge.processing_diff(db, args.before, args.after)
            )
            Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps({"exported": args.output, "kind": args.command}))


if __name__ == "__main__":
    main()
