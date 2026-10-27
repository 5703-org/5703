"""Actual API/PG scope diagnosis, no provider calls or fabricated saved memory."""
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.modules.answering.models import AnswerRequest,Job
from app.modules.learning_state.models import MemoryEntry,MemoryWriteEvent
from .test_memory_preview_v3 import authored,preview


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    def deny(*a,**kw):pytest.fail('No model dispatch allowed in deterministic memory verification')
    monkeypatch.setattr('generation.adapters.LLMAdapter._call',deny)
    monkeypatch.setattr('generation.adapters.open_provider',deny)


@pytest.mark.parametrize('source,expected_scope',[
    ('I prefer concise explanations.','global'),
    ('For chemistry, I prefer concise explanations.','chemistry'),
    ('From now on, I prefer concise chemistry explanations.','global'),
])
def test_exact_native_source_is_saved_without_extraction_but_embedded_scope_is_not_fixed(runtime,source,expected_scope):
    email,owner,_=authored(runtime,[]);headers=runtime.headers(email)
    session=runtime.client.post('/api/v1/sessions',headers=headers,json={'title':'Durable statement scope verification'}).json()['data']
    r=runtime.client.post(f"/api/v1/sessions/{session['id']}/messages",headers={**headers,'Idempotency-Key':str(uuid4())},json={'content':source})
    assert r.status_code==202
    receipt=r.json()['data']
    try:
        with runtime.db() as db:
            req=db.get(AnswerRequest,receipt['request_id'])
            entry=db.scalar(select(MemoryEntry).where(MemoryEntry.owner_id==owner))
            assert entry.content==source and entry.scope==expected_scope
            event=db.scalar(select(MemoryWriteEvent).where(MemoryWriteEvent.source_message_id==req.user_message_id))
            assert event.status=='applied'
            assert not list(db.scalars(select(Job).where(Job.kind=='memory',Job.owner_id==owner)))
            identity=entry.id
        unrelated=preview(runtime,email,'Explain photosynthesis in biology.')
        assert identity not in [x['id'] for x in unrelated['entries']]
        if expected_scope=='global':
            # Existing saved-profile precedence suppresses global detail_level.
            # Mis-scoping is real, but this does not demonstrate cross-topic leakage.
            assert {'id':identity,'reason':'saved_profile_default'} in unrelated['excluded']
        else:
            related=preview(runtime,email,'Explain acid chemistry.')
            assert identity in [x['id'] for x in related['entries']]
        assert not preview(runtime,'student2@example.com','Explain acid chemistry.')['entries']
    finally:
        assert runtime.client.post(f"/api/v1/jobs/{receipt['job_id']}/cancel",headers=headers).status_code==200
