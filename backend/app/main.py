"""Application factory (Spec A02).

Importing this module never touches the database or the network; the app is
built explicitly, which is what makes isolated test apps possible.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import TraceMiddleware
from app.db import session as db_session
from app.platform_core.registry import register_builtin_providers


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()
    engine = db_session.init_engine(settings.database_url)
    register_builtin_providers()

    app = FastAPI(
        title=settings.app_name, version="0.1.0", docs_url="/docs", openapi_url="/openapi.json"
    )
    app.state.settings = settings
    app.state.engine = engine
    app.dependency_overrides[get_settings] = lambda: settings

    app.add_middleware(TraceMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    from app.modules.identity.accounts import router as accounts_router
    from app.modules.model_settings.router import router as model_settings_router

    app.include_router(accounts_router, prefix=settings.api_v1_prefix)
    app.include_router(model_settings_router, prefix=settings.api_v1_prefix)
    from app.modules.answering.router import router as answering_router
    from app.modules.knowledge.router import router as knowledge_router
    from app.modules.experiment.router import router as experiment_router

    app.include_router(answering_router, prefix=settings.api_v1_prefix)
    app.include_router(knowledge_router, prefix=settings.api_v1_prefix)
    app.include_router(experiment_router, prefix=settings.api_v1_prefix)

    @app.get("/live", tags=["health"])
    @app.get("/api/v1/health/live", tags=["health"])
    def live():
        return {"status": "alive"}

    @app.get("/ready", tags=["health"])
    @app.get("/api/v1/health/ready", tags=["health"])
    def ready():
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=503, content={"status": "not_ready", "checks": {"database": "down"}}
            )
        return {"status": "ready", "checks": {"database": "up"}}

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok", "env": settings.env}

    from app.core.contracts import register_response_schemas

    register_response_schemas(app)
    return app


app = create_app()
