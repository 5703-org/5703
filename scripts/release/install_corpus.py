"""Install the bundled corpus once, or verify its existing active identity."""

import argparse
import json
from pathlib import Path
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.modules.knowledge.models import ActiveCorpus, Document, ReleaseChunk, CorpusRelease
from app.modules.knowledge.service import _release_rows
from scripts.release.corpus_bundle import import_bundle, safe_path
from scripts.release.common import file_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, required=True)
    args = parser.parse_args()
    settings = Settings()
    engine = create_engine(settings.database_url)
    with engine.connect() as db:
        count = db.scalar(select(func.count()).select_from(Document))
        active = db.scalar(select(ActiveCorpus.release_id).where(ActiveCorpus.id == 1))
        vectors = (
            db.scalar(
                select(func.count())
                .select_from(ReleaseChunk)
                .where(ReleaseChunk.release_id == active)
            )
            if active
            else 0
        )
    engine.dispose()
    if not count:
        print(json.dumps(import_bundle(args.path, settings)))
        return
    manifest = json.loads((args.path / "MANIFEST.json").read_text("utf-8"))
    if active != manifest["active_release_id"] or vectors != manifest["active_vector_count"]:
        raise ValueError(
            "Existing corpus differs; no existing source or active release was changed"
        )
    for entry in manifest["files"]:
        source = safe_path(
            Path(settings.storage_root).resolve(), entry["path"].removeprefix("storage/")
        )
        if file_hash(source) != entry["sha256"]:
            raise ValueError("Installed source hash differs; existing data was not changed")
    with Session(engine) as db:
        _release_rows(db, db.get(CorpusRelease, active), require_active=True)
    engine.dispose()
    print(
        json.dumps(
            {
                "status": "already_installed",
                "active_release_id": active,
                "active_vectors": vectors,
                "source_hashes_verified": len(manifest["files"]),
            }
        )
    )


if __name__ == "__main__":
    main()
