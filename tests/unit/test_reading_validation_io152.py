"""Focused mechanical source fences; PostgreSQL I/O parity is separate evidence."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.modules.answering import service
from app.modules.learning_product import library
from generation.types import RequestBudget


def frozen_scope(text="Water crosses a membrane."):
    value = {
        "version": "reading_scope_v1",
        "scope": "chapter",
        "release_id": "release",
        "document_id": "book",
        "processing_id": "run",
        "section": "Transport",
        "allowed_chunk_ids": ["chunk"],
        "selected_chunk_ids": ["chunk"],
        "source_unit_id": "unit",
        "selection": {
            "start": 0,
            "end": len(text),
            "text": text,
            "text_hash": library.text_hash(text),
            "unit_text_hash": library.text_hash(text),
        },
    }
    return {**value, "scope_hash": library.fingerprint(value)}


def scope_rows(section="Transport", document_id="book", processing_id="run"):
    return [
        (
            SimpleNamespace(id="chunk", section=section, spans=[{"unit_id": "unit"}]),
            SimpleNamespace(id=document_id),
            SimpleNamespace(id=processing_id),
            None,
        )
    ]


class FreshTextSession:
    def __init__(self, current_text):
        self.current_text = current_text
        self.refreshes = []

    def refresh(self, unit, *, attribute_names):
        self.refreshes.append((unit.id, attribute_names))
        unit.cleaned_text = self.current_text


def selected_scope(monkeypatch, db, rows=None):
    frozen = frozen_scope()
    unit = SimpleNamespace(id="unit", processing_id="run", cleaned_text=frozen["selection"]["text"])
    monkeypatch.setattr(library, "released_rows", lambda *a, **k: (None, rows or scope_rows()))
    monkeypatch.setattr(library, "book_data", lambda *a, **k: (None, scope_rows(), [unit]))
    return frozen


def test_cached_selected_text_cannot_hide_current_change_without_epoch(monkeypatch):
    db = FreshTextSession("A changed current source sentence.")
    frozen = selected_scope(monkeypatch, db)
    with pytest.raises(AppError, match="Selected paragraph identity changed"):
        library.validate_reading_context(db, SimpleNamespace(), frozen)
    assert db.refreshes == [("unit", ["cleaned_text"])]


def test_exact_selected_text_survives_fresh_reread(monkeypatch):
    frozen = frozen_scope()
    db = FreshTextSession(frozen["selection"]["text"])
    selected_scope(monkeypatch, db)
    assert library.validate_reading_context(db, SimpleNamespace(), frozen) is frozen


@pytest.mark.parametrize(
    "rows",
    [
        scope_rows(section="Other section"),
        scope_rows(document_id="other"),
        scope_rows(processing_id="other"),
    ],
)
def test_scoped_identity_drift_is_rejected(monkeypatch, rows):
    db = FreshTextSession(frozen_scope()["selection"]["text"])
    frozen = selected_scope(monkeypatch, db, rows)
    with pytest.raises(AppError):
        library.validate_reading_context(db, SimpleNamespace(), frozen)
    assert not db.refreshes


def test_missing_visible_chunk_is_rejected(monkeypatch):
    monkeypatch.setattr(library, "released_rows", lambda *a, **k: (None, []))
    with pytest.raises(AppError):
        library.validate_reading_context(FreshTextSession(""), SimpleNamespace(), frozen_scope())


class UnitsSession:
    def __init__(self, units):
        self.units = units

    def scalars(self, statement):
        return self.units


def test_metadata_projection_preserves_whole_book_processing_ambiguity(monkeypatch):
    rows = scope_rows() + scope_rows(processing_id="second-run")
    monkeypatch.setattr(library, "released_rows", lambda *a, **k: (None, rows))
    with pytest.raises(AppError, match="ambiguous processing membership"):
        library.book_data(UnitsSession([]), SimpleNamespace(), "book", metadata_only=True)


def test_metadata_projection_preserves_missing_unit_failure(monkeypatch):
    row = scope_rows()[0]
    row[0].spans.append({"unit_id": "missing"})
    monkeypatch.setattr(library, "released_rows", lambda *a, **k: (None, [row]))
    with pytest.raises(AppError, match="membership is incomplete"):
        library.book_data(
            UnitsSession([SimpleNamespace(id="unit", processing_id="run")]),
            SimpleNamespace(),
            "book",
            metadata_only=True,
        )


def test_metadata_projection_accepts_complete_whole_book(monkeypatch):
    rows = scope_rows()
    units = [SimpleNamespace(id="unit", processing_id="run")]
    monkeypatch.setattr(library, "released_rows", lambda *a, **k: (None, rows))
    assert (
        library.book_data(UnitsSession(units), SimpleNamespace(), "book", metadata_only=True)[2]
        == units
    )


def eligible_request(**changes):
    value = dict(
        trace={},
        command={},
        mode="interactive_chat",
        state="error",
        regeneration_of=None,
        session_id=None,
        id="request",
        budget=RequestBudget().to_dict(),
    )
    return SimpleNamespace(**{**value, **changes})


def test_eligible_retry_still_requires_current_context(monkeypatch):
    def revoked(db, req):
        raise AppError("SOURCE_UNAVAILABLE")

    monkeypatch.setattr(service, "validate_learning_context", revoked)
    assert service.can_retry(UnitsSession([]), eligible_request()) is False


def test_eligible_retry_retains_exhausted_reservation(monkeypatch):
    monkeypatch.setattr(service, "validate_learning_context", lambda db, req: None)

    def previous_failure(statement):
        return (
            {"code": "MODEL_UNAVAILABLE", "details": {"retryable": True}}
            if "jobs.error" in str(statement)
            else None
        )

    db = SimpleNamespace(scalar=previous_failure)
    assert service.can_retry(db, eligible_request()) is True
    budget = RequestBudget(consumed_calls=4).to_dict()
    assert service.can_retry(db, eligible_request(state="cancelled", budget=budget)) is False
