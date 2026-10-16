import { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { request } from './api';
import { Button, DataDetails, Empty, ErrorNotice, Loading, Modal, titleCase } from './components';
import type { components } from './generated/api';

export type FailureSummary = components['schemas']['FailureSummary'];
export type FailureDetail = components['schemas']['FailureDetail'];
type FailurePage = components['schemas']['FailurePage'];

function EvidenceCounts({ counts }: { counts: FailureSummary['counts'] }) {
  return <dl className="diagnostic-counts">{(['candidates', 'submitted', 'cited'] as const).map(key => <div key={key}><dt>{key === 'candidates' ? 'Retrieved candidates' : key === 'submitted' ? 'Submitted to model' : 'Actually cited'}</dt><dd>{counts?.[key] ?? 'Not recorded'}</dd></div>)}</dl>;
}

export function FailuresPage() {
  const [page, setPage] = useState<FailurePage | null>(null); const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null); const [state, setState] = useState(''); const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null); const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null);
    request<FailurePage>(`/admin/failures?limit=50&offset=${offset}${state ? `&state=${encodeURIComponent(state)}` : ''}`, { signal: controller.signal }).then(value => { if (!controller.signal.aborted) setPage(value); }).catch(caught => { if (!controller.signal.aborted) setError(caught); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [offset, state, revision]);
  return <div className="content-page">
    <span className="eyebrow">Administration</span><h1>Response diagnostics</h1>
    <p className="page-intro">Inspect recorded answers, failures, refusals and clarification requests. A refusal or clarification is a recorded response, not a provider failure.</p>
    <div className="admin-toolbar"><label className="admin-search">Outcome<select value={state} onChange={event => { setState(event.target.value); setOffset(0); }}><option value="">All diagnostic outcomes</option><option value="answered">Answered</option><option value="all">All requests</option><option value="error">Failed</option><option value="cancelled">Cancelled</option><option value="refused">Refused</option><option value="clarification">Clarification</option></select></label><Button disabled={loading} onClick={() => setRevision(value => value + 1)}><RefreshCw size={17} />Refresh</Button></div>
    <ErrorNotice error={error} />{loading ? <Loading>Loading response diagnostics…</Loading> : !error && page && <>
      <p className="secondary">{page.total} recorded outcome{page.total === 1 ? '' : 's'}</p><div className="record-list">{page.items.map(item => <article className="record" key={item.request_id} data-request-id={item.request_id}>
        <div className="record-header"><h2 className="record-title">{item.question || 'Question not recorded'}</h2><span className="record-status">{titleCase(item.response_type || item.state)}</span></div>
        <p className="secondary">{item.created_at} · {item.model?.provider || 'Provider not recorded'}{item.model?.model ? ` / ${item.model.model}` : ''}</p>
        {item.error_message && <p>{item.error_message}</p>}<EvidenceCounts counts={item.counts} /><Button onClick={() => setSelected(item.request_id)}>Inspect response</Button>
      </article>)}</div>{page.items.length === 0 && <Empty title="No matching outcomes">No records were returned for this filter.</Empty>}
      <nav className="pagination" aria-label="Diagnostic pages"><Button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>Previous</Button><span>{page.total ? `${page.offset + 1}–${page.offset + page.items.length} of ${page.total}` : '0 results'}</span><Button disabled={page.offset + page.items.length >= page.total} onClick={() => setOffset(offset + 50)}>Next</Button></nav>
    </>}{selected && <FailureViewer requestId={selected} onClose={() => setSelected(null)} />}
  </div>;
}

function FailureViewer({ requestId, onClose }: { requestId: string; onClose: () => void }) {
  const [detail, setDetail] = useState<FailureDetail | null>(null); const [error, setError] = useState<unknown>(null); const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setDetail(await request<FailureDetail>(`/admin/failures/${requestId}`)); }
    catch (caught) { setError(caught); }
    finally { setLoading(false); }
  }, [requestId]);
  useEffect(() => { void load(); }, [load]);
  return <Modal title="Response diagnostics" onClose={onClose} wide>
    <ErrorNotice error={error} action={<Button onClick={load} disabled={loading}>Try again</Button>} />{loading ? <Loading>Loading the recorded trace…</Loading> : detail && <div className="stack">
      <div><h3>{detail.question || 'Question not recorded'}</h3><p className="secondary">{titleCase(detail.response_type || detail.state)} · Request {detail.request_id}</p></div>
      {detail.error_message && <p className="error-text">{detail.error_code}: {detail.error_message}</p>}
      <EvidenceCounts counts={detail.counts} /><p className="secondary">Candidates were retrieved. Submitted passages reached the model. Cited sources were used in the saved response. Missing historical counts remain unrecorded.</p>
      {detail.retrieval_query && <section><h3>Prepared retrieval question</h3><p className="preserve-lines">{detail.retrieval_query}</p></section>}
      {detail.answer_text && <section><h3>Recorded response</h3><p className="preserve-lines">{detail.answer_text}</p>{detail.refusal_reason && <p className="secondary">Reason: {detail.refusal_reason}</p>}</section>}
      <section><h3>Recorded stages</h3>{detail.stages?.length ? <ol className="diagnostic-stages">{detail.stages.map((stage, index) => <li key={`${stage.stage}-${index}`}><strong>{titleCase(stage.stage)}</strong> · {stage.status}{typeof stage.detail === 'string' && <p>{stage.detail}</p>}{stage.detail && typeof stage.detail === 'object' ? <DataDetails title="Stage details" data={stage.detail} /> : null}</li>)}</ol> : <p className="secondary">Stage detail was not recorded.</p>}</section>
      <DataDetails title="Budget and attempts" data={{ budget: detail.budget, attempts: detail.attempts }} /><DataDetails title="Source and request identities" data={{ http_trace_id: detail.http_trace_id, request_id: detail.request_id, session_id: detail.session_id, owner_id: detail.owner_id, model: detail.model, evidence: detail.evidence }} />
    </div>}
  </Modal>;
}
