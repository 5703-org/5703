"""Administrator-only immutable model settings endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from contracts.http import Envelope
from app.api.v1.deps import require_roles
from app.core.config import Settings, get_settings
from app.core.responses import ok
from app.db.session import get_db
from app.modules.identity.models import User
from . import service
from .schemas import (
    ActivationInput,
    ConfigurationSave,
    ConnectionTestOut,
    EnvironmentInput,
    ModelConfigurationOut,
    ModelSettingsState,
    ProviderPreset,
)

router = APIRouter(prefix="/admin/model-configurations", tags=["model-settings"])


@router.get("/presets", response_model=Envelope[list[ProviderPreset]])
def presets(actor: User = Depends(require_roles("admin"))):
    return ok(service.presets())


@router.get("", response_model=Envelope[ModelSettingsState])
def configurations(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_roles("admin")),
):
    return ok(service.state(db, settings, actor))


@router.post("", status_code=201, response_model=Envelope[ModelConfigurationOut])
def create(
    body: ConfigurationSave,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_roles("admin")),
):
    return ok(service.save(db, settings, actor, body))


@router.post("/use-environment", response_model=Envelope[ModelSettingsState])
def use_environment(
    body: EnvironmentInput,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_roles("admin")),
):
    return ok(service.activate(db, settings, actor, None, None, body.expected_active_version))


@router.get("/{configuration_id}", response_model=Envelope[ModelConfigurationOut])
def get_configuration(
    configuration_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    active = db.get(service.ActiveModelConfiguration, actor.workspace_id)
    return ok(
        service.output(
            db,
            service.owned(db, configuration_id, actor),
            active.configuration_id if active else None,
        )
    )


@router.post(
    "/{configuration_id}/versions", status_code=201, response_model=Envelope[ModelConfigurationOut]
)
def create_version(
    configuration_id: str,
    body: ConfigurationSave,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_roles("admin")),
):
    return ok(service.save(db, settings, actor, body, configuration_id))


@router.post("/{configuration_id}/test", response_model=Envelope[ConnectionTestOut])
def test_configuration(
    configuration_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_roles("admin")),
):
    return ok(service.run_test(db, settings, actor, configuration_id))


@router.post("/{configuration_id}/activate", response_model=Envelope[ModelSettingsState])
def activate_configuration(
    configuration_id: str,
    body: ActivationInput,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_roles("admin")),
):
    return ok(
        service.activate(
            db, settings, actor, configuration_id, body.test_id, body.expected_active_version
        )
    )
