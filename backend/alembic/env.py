"""Alembic environment: URL comes from DATABASE_URL or typed Settings (Spec B02)."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import Settings  # noqa: E402
from app.db.base import Base  # noqa: E402

# Import every module that declares tables so autogenerate stays honest.
from app.modules.identity import models as _identity_models  # noqa: F401,E402
from app.modules.learning import models as _learning_models  # noqa: F401,E402
from app.platform_core import models as _platform_models  # noqa: F401,E402
from app.modules.answering import models as _answer_models
from app.modules.knowledge import models as _knowledge_models
from app.modules.experiment import models as _experiment_models
from app.modules.model_settings import models as _model_settings_models

config = context.config
if config.config_file_name is not None:
    # Migration commands can share a process with the API/worker tooling.
    # Preserve application error/trace loggers that already exist.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

config.set_main_option("sqlalchemy.url", os.environ.get("DATABASE_URL") or Settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
