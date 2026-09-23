import { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { request } from './api';
import { Button, DataDetails, Empty, ErrorNotice, Loading, Modal, titleCase } from './components';
import type { components } from './generated/api';

export type FailureSummary = components['schemas']['FailureSummary'];
export type FailureDetail = components['schemas']['FailureDetail'];
type FailurePage = components['schemas']['FailurePage'];
type Processing = components['schemas']['FailureProcessing'];
const countLabels = { candidates: 'Candidates before relevance', filtered: 'After relevance filter', submitted: 'Submitted to model', cited: 'Actually cited' };

function EvidenceCounts({ counts }: { counts: FailureSummary['counts'] }) {
  return <dl className="diagnostic-counts">{(['candidates', 'filtered', 'submitted', 'cited'] as const).map(key => <div key={key}><dt>{countLabels[key]}</dt><dd>{counts?.[key] ?? 'Not recorded'}</dd></div>)}</dl>;
}

function Observation({ label, value }: { label: string; value: string | number | boolean | null | undefined }) {
  return <div><dt>{label}</dt><dd>{value === null || value === undefined || value === '' ? <span className="secondary">Not recorded</span> : typeof value === 'boolean' ? value ? 'Yes' : 'No' : value}</dd></div>;
}

function ProviderAttempts({ attempts }: { attempts: FailureDetail['attempts'] }) {
  return <section><h3>Provider attempts</h3>{attempts.length ? attempts.map((attempt, index) => <details className="data-details" key={`${attempt.created_at}-${index}`}><summary>{titleCase(attempt.stage)} · {attempt.status}</summary><dl className="trace-observations">
    <Observation label="Attempt error" value={attempt.error_code} /><Observation label="Attempt duration" value={attempt.duration_ms == null ? null : `${attempt.duration_ms} ms`} /><Observation label="Recorded at" value={attempt.created_at} />
    {attempt.provider_diagnostic ? <><Observation label="Provider diagnostic stage" value={titleCase(attempt.provider_diagnostic.stage)} /><Observation label="HTTP status" value={attempt.provider_diagnostic.http_status} /><Observation label="Provider error type" value={attempt.provider_diagnostic.provider_error_type} /><Observation label="Provider error code" value={attempt.provider_diagnostic.provider_error_code} /><Observation label="Rejected parameter" value={attempt.provider_diagnostic.provider_error_parameter} /><Observation label="Provider request ID" value={attempt.provider_diagnostic.provider_request_id} /><Observation label="Finish reason" value={attempt.provider_diagnostic.finish_reason} /><Observation label="Network category" value={attempt.provider_diagnostic.network_error} /><Observation label="Transport attempted" value={attempt.provider_diagnostic.request_submitted} /></> : <Observation label="Provider diagnostic" value={null} />}
  </dl></details>) : <p className="secondary">No provider attempts were recorded.</p>}<p className="secondary">These fields identify the saved failure stage and provider receipt. Provider acceptance, usage and billing may remain unknown after a network interruption.</p></section>;
}

function ProcessingTrace({ trace, detail }: { trace: Processing | null | undefined; detail: FailureDetail }) {
  const query = trace?.understanding;
  return <details className="processing-trace">
    <summary>Processing trace</summary>
    {!trace ? <p className="secondary">Structured processing details were not recorded for this request.</p> : <div className="stack">
      {trace.memory && <section><h3>Learning memory preparation</h3><dl className="trace-observations"><Observation label="Memory context state" value={titleCase(trace.memory.status)} /><Observation label="Memory policy" value={trace.memory.policy_version} /><Observation label="Memory preparation error" value={trace.memory.error_code} /></dl><p className="secondary">Memory preparation and answer generation have separate outcomes.</p></section>}
      <section><h3>Question understanding</h3><dl className="trace-observations">
        <Observation label="Original question" value={detail.question} />
        <Observation label="Standalone retrieval question" value={query?.standalone_query} />
        <Observation label="Intent" value={query?.intent ? titleCase(query.intent) : null} />
        <Observation label="Topic relationship" value={query?.topic_relation ? titleCase(query.topic_relation) : null} />
        <Observation label="Clarification needed" value={query?.needs_clarification} />
        <Observation label="Clarification reason" value={query?.clarification_reason} />
        <Observation label="Understanding method" value={query?.method} />
      </dl>
        {!!query?.requested_facets?.length && <><h4>Requested parts</h4><ol className="diagnostic-stages">{query.requested_facets.map((facet, i) => <li key={facet.id || i}>{facet.request || facet.id}<span className="secondary">{facet.terms?.length ? ` · Terms: ${facet.terms.join(', ')}` : ''}</span></li>)}</ol></>}
        {!!query?.comparison_targets?.length && <p>Comparison targets: {query.comparison_targets.join(' / ')}</p>}
        {!!query?.negation?.length && <p>Negation: {query.negation.join(', ')}</p>}
        {!!query?.numbers?.length && <p>Numbers and units: {query.numbers.join(', ')}</p>}
        {!!query?.conditions?.length && <p>Conditions: {query.conditions.join('; ')}</p>}
        {query?.correction && <dl className="trace-observations"><Observation label="Correction replacement" value={query.correction.replacement} /><Observation label="Correction excludes" value={query.correction.excluded?.join(', ')} /><Observation label="Previous question" value={query.correction.prior_question} /></dl>}
        {!!query?.limitations?.length && <p className="secondary">{query.limitations.join(' ')}</p>}
      </section>
      <section><h3>Frozen configuration and execution</h3><dl className="trace-observations">
        <Observation label="Corpus release" value={trace.corpus_release_id} />
        <Observation label="Answer provider / model" value={[detail.model.provider, detail.model.model].filter(Boolean).join(' / ')} />
        <Observation label="Model configuration" value={detail.model.configuration_id} />
        <Observation label="Requested local device" value={trace.requested_device} />
        <Observation label="Resolved local device" value={trace.resolved_device} />
        <Observation label="Relevance policy" value={trace.relevance_policy} />
        <Observation label="Reranker" value={trace.reranker_model} />
        <Observation label="Minimum raw reranker logit" value={trace.relevance_minimum_logit} />
      </dl><p className="secondary">Relevance scores screen topic matches. They are separate from claim support.</p></section>
      {trace.facet_fallback && <section><h3>Per-part retrieval fallback</h3><dl className="trace-observations">
        <Observation label="Fallback triggered" value={trace.facet_fallback.triggered} />
        <Observation label="Fallback reason" value={trace.facet_fallback.reason ? titleCase(trace.facet_fallback.reason) : null} />
        <Observation label="Fallback policy" value={trace.facet_fallback.policy_version} />
        <Observation label="Whole-question candidates" value={trace.facet_fallback.whole_query_candidate_count} />
        <Observation label="Whole-question relevance survivors" value={trace.facet_fallback.whole_query_accepted_count} />
        <Observation label="Fallback elapsed time" value={trace.facet_fallback.elapsed_ms == null ? null : `${trace.facet_fallback.elapsed_ms} ms`} />
        <Observation label="Fallback admitted passage IDs" value={trace.facet_fallback.accepted_chunk_ids?.join(', ') || 'None recorded'} />
      </dl><p className="secondary">Each part is scored against its own query. The saved learner question stays complete. Candidate sets across parts may overlap. Whole-question work is recorded separately.</p>
        {trace.facet_fallback.attempted_facets?.map((attempt, index) => <details className="data-details" key={`${attempt.facet_id}-${index}`}><summary>Retrieved part {index + 1}{attempt.facet_id ? ` · ${attempt.facet_id}` : ''}</summary><dl className="trace-observations">
          <Observation label="Part query" value={attempt.query} /><Observation label="Part candidates" value={attempt.candidate_count} /><Observation label="Part relevance survivors" value={attempt.accepted_count} /><Observation label="Part reranker" value={attempt.model} /><Observation label="Part reranker revision" value={attempt.revision} /><Observation label="Part accepted passage IDs" value={attempt.accepted_chunk_ids?.join(', ') || 'None recorded'} />
        </dl>{!!attempt.excluded?.length && <ul className="diagnostic-stages">{attempt.excluded.map((excluded, i) => <li key={`${excluded.chunk_id}-${i}`}>{excluded.chunk_id || 'Passage ID not recorded'} · {titleCase(excluded.reason)}{excluded.score == null ? '' : ` · Part-query raw score ${excluded.score}`}</li>)}</ul>}</details>)}
      </section>}
      {trace.reuse && <section><h3>Earlier source reuse</h3><dl className="trace-observations"><Observation label="Available earlier passages" value={trace.reuse.available_count} /><Observation label="Eligible in this release" value={trace.reuse.eligible_count} /><Observation label="Rescored passage IDs" value={trace.reuse.rescored_chunk_ids?.join(', ') || 'None recorded'} /></dl></section>}
      {(trace.coverage || trace.packing || trace.citation_audit || trace.teaching) && <section><h3>Evidence and teaching observations</h3><dl className="trace-observations">
        {trace.coverage && <><Observation label="Lexical coverage estimate" value={trace.coverage.status ? titleCase(trace.coverage.status) : null} /><Observation label="Uncovered request parts" value={trace.coverage.uncovered_facet_ids?.join(', ') || 'None recorded'} /></>}
        {trace.packing && <><Observation label="Evidence packing" value={trace.packing.version} /><Observation label="Evidence text token ceiling" value={trace.packing.text_token_ceiling} /><Observation label="Duplicate passages removed" value={trace.packing.duplicate_count} /></>}
        {trace.citation_audit && <><Observation label="Citation locality check" value={trace.citation_audit.status ? titleCase(trace.citation_audit.status) : null} /><Observation label="Citation review flags" value={trace.citation_audit.flag_count} /></>}
        {trace.teaching && <><Observation label="Teaching level" value={trace.teaching.level} /><Observation label="Teaching style" value={trace.teaching.style} /><Observation label="Teaching mode" value={trace.teaching.mode ? titleCase(trace.teaching.mode) : null} /></>}
      </dl><p className="secondary">Lexical coverage and citation flags are automated observations. Independent support and teaching quality review remain separate.</p></section>}
      <section><h3>Excluded passages</h3>{trace.excluded?.length ? <ul className="diagnostic-stages">{trace.excluded.map((item, i) => <li key={`${item.stage}-${item.chunk_id}-${i}`}><span>{item.chunk_id || 'Passage ID not recorded'}</span><span> · {titleCase(item.stage)}: {titleCase(item.reason)}</span>{item.score !== null && item.score !== undefined && <span className="secondary"> · Raw reranker score {item.score}</span>}</li>)}</ul> : <p className="secondary">No passage exclusions were recorded.</p>}{trace.exclusions_truncated && <p className="secondary">Showing the first 100 recorded exclusions.</p>}</section>
      <section><h3>Measured timings</h3>{Object.keys(trace.timing_ms || {}).length ? <dl className="trace-observations">{Object.entries(trace.timing_ms || {}).map(([key, value]) => <Observation key={key} label={titleCase(key.replace(/_ms$/, ''))} value={`${value} ms`} />)}</dl> : <p className="secondary">Stage timings were not recorded.</p>}<p className="secondary">Timing scope: {trace.timing_scope || 'Not recorded'}. Stage measurements can overlap; they should not be summed.</p></section>
      <section><h3>Terminal state</h3><dl className="trace-observations"><Observation label="Request state" value={titleCase(detail.state)} /><Observation label="Recorded error code" value={detail.error_code || 'None recorded'} /><Observation label="Error diagnosis" value={detail.error_message || 'None recorded'} /></dl></section>
    </div>}
  </details>;
}

export function FailuresPage() {
  const [page, setPage] = useState<FailurePage | null>(null); const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null); const [state, setState] = useState(''); const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null); const [revision, setRevision] = useState(0);
  const [requestId, setRequestId] = useState('');
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null);
    request<FailurePage>(`/admin/failures?limit=50&offset=${offset}${state ? `&state=${encodeURIComponent(state)}` : ''}`, { signal: controller.signal }).then(value => { if (!controller.signal.aborted) setPage(value); }).catch(caught => { if (!controller.signal.aborted) setError(caught); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [offset, state, revision]);
  return <div className="content-page">
    <span className="eyebrow">Administration</span><h1>Response diagnostics</h1>
    <p className="page-intro">Inspect recorded answers, failures, refusals and clarification requests. A refusal or clarification is a recorded response, not a provider failure.</p>
    <div className="admin-toolbar"><label className="admin-search">Outcome<select value={state} onChange={event => { setState(event.target.value); setOffset(0); }}><option value="">All diagnostic outcomes</option><option value="answered">Answered</option><option value="all">All requests</option><option value="error">Failed</option><option value="cancelled">Cancelled</option><option value="refused">Refused</option><option value="clarification">Clarification</option></select></label><Button disabled={loading} onClick={() => setRevision(value => value + 1)}><RefreshCw size={17} />Refresh</Button></div>
    <form className="admin-toolbar" onSubmit={event => { event.preventDefault(); if (requestId.trim()) setSelected(requestId.trim()); }}><label className="admin-search">Request ID<input value={requestId} onChange={event => setRequestId(event.target.value)} placeholder="Inspect an answered or failed request" maxLength={160} /></label><Button type="submit" disabled={!requestId.trim()}>Inspect request</Button></form>
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
    setLoading(true); setError(null); setDetail(null);
    try { setDetail(await request<FailureDetail>(`/admin/failures/${encodeURIComponent(requestId)}`)); }
    catch (caught) { setError(caught); }
    finally { setLoading(false); }
  }, [requestId]);
  useEffect(() => { void load(); }, [load]);
  return <Modal title="Response diagnostics" onClose={onClose} wide>
    <ErrorNotice error={error} action={<Button onClick={load} disabled={loading}>Try again</Button>} />{loading ? <Loading>Loading the recorded trace…</Loading> : detail && <div className="stack">
      <div><h3>{detail.question || 'Question not recorded'}</h3><p className="secondary">{titleCase(detail.response_type || detail.state)} · Request {detail.request_id}</p></div>
      {detail.error_message && <p className="error-text">{detail.error_code}: {detail.error_message}</p>}
      <EvidenceCounts counts={detail.counts} /><p className="secondary">Candidates may combine fresh retrieval with verified earlier passages. The relevance filter screens them before evidence packing. Submitted passages reached the model. Cited sources were used in the saved response. Missing historical counts remain unrecorded.</p>
      {detail.processing?.selection_source === 'facet_fallback' && <p className="secondary">The summary counts show the distinct per-part fallback pool and its final admitted passages. The earlier whole-question attempt appears separately in the processing trace.</p>}
      <ProcessingTrace trace={detail.processing} detail={detail} />
      {detail.retrieval_query && <section><h3>Prepared retrieval question</h3><p className="preserve-lines">{detail.retrieval_query}</p></section>}
      {detail.answer_text && <section><h3>Recorded response</h3><p className="preserve-lines">{detail.answer_text}</p>{detail.refusal_reason && <p className="secondary">Reason: {detail.refusal_reason}</p>}</section>}
      <section><h3>Recorded stages</h3>{detail.stages?.length ? <ol className="diagnostic-stages">{detail.stages.map((stage, index) => <li key={`${stage.stage}-${index}`}><strong>{titleCase(stage.stage)}</strong> · {stage.status}{typeof stage.detail === 'string' && <p>{stage.detail}</p>}{stage.detail && typeof stage.detail === 'object' ? <DataDetails title="Stage details" data={stage.detail} /> : null}</li>)}</ol> : <p className="secondary">Stage detail was not recorded.</p>}</section>
      <ProviderAttempts attempts={detail.attempts} /><DataDetails title="Request budget" data={detail.budget} /><DataDetails title="Source and request identities" data={{ http_trace_id: detail.http_trace_id, request_id: detail.request_id, session_id: detail.session_id, owner_id: detail.owner_id, model: detail.model, evidence: detail.evidence }} />
    </div>}
  </Modal>;
}
