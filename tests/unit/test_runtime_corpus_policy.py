from types import SimpleNamespace
import pytest
from app.core.exceptions import AppError
from app.modules.knowledge import service


class NoWrites:
    def __getattr__(self, name):
        raise AssertionError("Unexpected database operation: " + name)


def live():
    return SimpleNamespace(env="test", model_mode="live")


@pytest.mark.parametrize("values", [{}, {"embedding_provider": "mock"}])
def test_formal_configuration_rejects_development_vectors_before_database(values):
    with pytest.raises(AppError) as exc:
        service.config_create(
            NoWrites(), "retrieval", "Synthetic policy check", values, settings=live()
        )
    assert exc.value.code == "VALIDATION_FAILED"


def test_formal_default_cannot_queue_authored_release():
    with pytest.raises(AppError):
        service.queue_release(NoWrites(), "synthetic-owner", ["run"], settings=live())


@pytest.mark.parametrize("configuration", [None, {}, {"embedding_provider": "mock"}])
def test_formal_processing_rejects_development_configuration_before_database(configuration):
    with pytest.raises(AppError) as exc:
        service.queue_process(NoWrites(), "document", "owner", configuration, settings=live())
    assert exc.value.code == "VALIDATION_FAILED"


def test_processing_router_passes_current_runtime_policy(monkeypatch):
    from app.modules.knowledge import router
    settings = live()
    def capture(db, document, actor, config, exclusions, *, settings):
        assert settings is expected
        return SimpleNamespace(id="run"), None
    expected = settings
    monkeypatch.setattr(service, "queue_process", capture)
    result = router.process("document", router.ProcessInput(), SimpleNamespace(commit=lambda: None), SimpleNamespace(id="owner"), settings)
    assert result["data"]["processing_id"] == "run"


def test_worker_refuses_old_queued_development_processing_before_source_read(monkeypatch):
    from app.modules.knowledge.models import ProcessingRun
    run = SimpleNamespace(id="run", state="registered", configuration={"embedding_provider": "mock"}, error=None)
    class QueuedOnly:
        def get(self, model, identity):
            assert model is ProcessingRun and identity == "run"
            return run
        def rollback(self): pass
        def commit(self): pass
    monkeypatch.setattr(service, "_execution_fence", lambda *a, **k: None)
    with pytest.raises(AppError) as exc:
        service.execute_processing(QueuedOnly(), live(), "run")
    assert exc.value.code == "VALIDATION_FAILED"
    assert run.state == "failed" and run.error["code"] == "VALIDATION_FAILED"


def test_formal_activation_leaves_pointer_untouched():
    class ReadOnlyRelease(NoWrites):
        def get(self, model, identity):
            return SimpleNamespace(configuration={"embedding_provider": "mock"})

    with pytest.raises(AppError):
        service.activate(ReadOnlyRelease(), "release", settings=live())


def test_explicit_real_corpus_passes_policy_without_dispatch():
    service.require_runtime_corpus(live(), {"embedding_provider": "e5"})


def test_development_tree_can_replay_its_existing_explicit_fixtures():
    service.require_runtime_corpus(
        SimpleNamespace(env="test", model_mode="mock"), {"embedding_provider": "mock"}
    )
