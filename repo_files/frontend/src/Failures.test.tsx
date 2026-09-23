import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { FailuresPage, type FailureDetail, type FailureSummary } from './Failures';
import { ApiError, request } from './api';

vi.mock('./api', async importOriginal => ({ ...await importOriginal<typeof import('./api')>(), request: vi.fn() }));
const record: FailureSummary = { request_id: 'request-1', session_id: 'session-1', owner_id: 'owner-1', question: 'A recorded question', state: 'refused', response_type: 'refusal', error_code: null, error_message: null, created_at: '2026-09-13T01:00:00Z', model: { provider: 'mock', model: 'mock-v1' }, counts: { candidates: 8, filtered: 5, submitted: 3, cited: 0 } };
beforeEach(() => {
  vi.clearAllMocks();
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
});
afterEach(cleanup);

describe('response diagnostics', () => {
  it('shows typed provider errors and separate memory status without rendering raw diagnostic payloads', async () => {
    const diagnostic = { stage: 'http' as const, http_status: 400, provider_error_type: 'invalid_request_error', provider_error_code: 'unsupported_parameter', provider_error_parameter: 'max_tokens', provider_request_id: 'req_public_fixture', finish_reason: null, network_error: null, request_submitted: true, message: 'private echoed prompt', raw_body: 'private provider body' };
    const detail: FailureDetail = { ...record, state: 'error', stages: [], budget: {}, attempts: [{ stage: 'generation', status: 'failed', error_code: 'PROVIDER_HTTP_ERROR', duration_ms: 99, created_at: record.created_at, provider_diagnostic: diagnostic }], evidence: {}, processing: { understanding: {}, exclusions_truncated: false, memory: { status: 'unavailable', policy_version: 'learning_memory_v2', error_code: 'MEMORY_PREPARATION_UNAVAILABLE' } } };
    vi.mocked(request).mockImplementation(async path => path === '/admin/failures/request-1' ? detail : { items: [record], total: 1, offset: 0, limit: 50 });
    render(<FailuresPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Inspect response' }));
    await screen.findByText('Provider attempts');
    expect(screen.getByText('unsupported_parameter')).toBeTruthy();
    expect(screen.getByText('max_tokens')).toBeTruthy();
    expect(screen.getByText('req_public_fixture')).toBeTruthy();
    expect(screen.getByText('MEMORY_PREPARATION_UNAVAILABLE')).toBeTruthy();
    expect(screen.queryByText('private echoed prompt')).toBeNull();
    expect(screen.queryByText('private provider body')).toBeNull();
  });
  it('distinguishes candidates, relevance survivors, submitted and cited counts from unknown history', async () => {
    vi.mocked(request).mockResolvedValue({ items: [record, { ...record, request_id: 'historical', question: 'Historical question', counts: { candidates: null, submitted: null, cited: null } }], total: 2, offset: 0, limit: 50 });
    render(<FailuresPage />);
    await screen.findByText('A recorded question');
    expect(screen.getAllByText('Not recorded')).toHaveLength(4);
    expect(screen.getByText('8')).toBeTruthy(); expect(screen.getByText('3')).toBeTruthy(); expect(screen.getByText('0')).toBeTruthy();
    expect(screen.getAllByText('Actually cited')).toHaveLength(2);
    expect(screen.getByText('5')).toBeTruthy();
    expect(screen.getAllByText('After relevance filter')).toHaveLength(2);
  });

  it('loads safe persisted detail and applies actual outcome filters', async () => {
    const detail: FailureDetail = { ...record, http_trace_id: 'trace-1', stages: [{ stage: 'retrieving', status: 'completed', detail: 'Eight candidates' }], budget: {}, attempts: [], retrieval_query: 'Prepared question', evidence: { candidate_chunk_ids: ['candidate'], submitted_chunk_ids: ['submitted'], cited_chunk_ids: [] }, answer_text: 'The available sources do not support this question.', refusal_reason: 'NO_EVIDENCE' };
    vi.mocked(request).mockImplementation(async path => path === '/admin/failures/request-1' ? detail : { items: [record], total: 1, offset: 0, limit: 50 });
    render(<FailuresPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Inspect response' }));
    await screen.findByText('Prepared question');
    expect(request).toHaveBeenCalledWith('/admin/failures/request-1');
    expect(screen.getByText('Eight candidates')).toBeTruthy();
    expect(screen.getByText('Structured processing details were not recorded for this request.')).toBeTruthy();
    expect(screen.queryByText('Per-part retrieval fallback')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Close response diagnostics' }));
    fireEvent.change(screen.getByRole('combobox', { name: 'Outcome' }), { target: { value: 'error' } });
    await screen.findByText('A recorded question');
    expect(request).toHaveBeenLastCalledWith('/admin/failures?limit=50&offset=0&state=error', expect.any(Object));
  });

  it('looks up a successful request outside the failure list and expands actual processing observations', async () => {
    const detail: FailureDetail = { ...record, request_id: 'answered-1', state: 'answered', response_type: 'answer', counts: { candidates: 8, filtered: 3, submitted: 2, cited: 1 }, stages: [], budget: {}, attempts: [], evidence: {}, processing: {
      understanding: { standalone_query: 'Compare diffusion and osmosis at 20 degrees.', intent: 'comparison', topic_relation: 'new_topic', needs_clarification: false, requested_facets: [{ id: 'part_1', request: 'Compare the two processes', terms: ['diffusion', 'osmosis'] }], comparison_targets: ['diffusion', 'osmosis'], negation: ['without'], numbers: ['20'], conditions: ['at 20 degrees'], correction: { replacement: 'osmosis', excluded: ['diffusion'], prior_question: 'Explain diffusion.' }, method: 'bounded_deterministic' },
      corpus_release_id: 'release-1', requested_device: 'auto', resolved_device: 'cpu', relevance_minimum_logit: -4, excluded: [{ chunk_id: 'chunk-7', reason: 'below_relevance_threshold', stage: 'relevance', score: -8.5 }], exclusions_truncated: false, timing_ms: { preparation_ms: 0, retrieval_ms: 450 }, timing_scope: 'worker_execution_before_answer_insert_v1',
      coverage: { status: 'partial', uncovered_facet_ids: ['part_2'], scope: 'Lexical request coverage; independent support review remains separate.' }, packing: { duplicate_count: 2, text_token_ceiling: 3000 }, citation_audit: { status: 'review_required', flag_count: 1 }, reuse: { available_count: 3, eligible_count: 1, rescored_chunk_ids: ['prior-1'] }, teaching: { level: 'beginner', style: 'socratic', mode: 'hint' },
      selection_source: 'facet_fallback', facet_fallback: { triggered: true, reason: 'fallback_completed', whole_query_candidate_count: 6, whole_query_accepted_count: 0, elapsed_ms: 250.5, accepted_chunk_ids: ['c1', 'c2', 'c8'], attempted_facets: [
        { facet_id: 'part_1', query: 'Explain osmosis.', candidate_count: 6, accepted_count: 3, model: 'pinned-reranker', revision: 'revision-1', accepted_chunk_ids: ['c1', 'c2', 'c8'], excluded: [{ chunk_id: 'c4', reason: 'below_relevance_threshold', stage: 'relevance', score: -6.5 }] },
        { facet_id: 'part_2', query: 'Give a future price.', candidate_count: 6, accepted_count: 0, accepted_chunk_ids: [] },
      ] },
    } };
    vi.mocked(request).mockImplementation(async path => path === '/admin/failures/answered-1' ? detail : { items: [], total: 0, limit: 50, offset: 0 });
    render(<FailuresPage />);
    await screen.findByText('No matching outcomes');
    fireEvent.change(screen.getByRole('textbox', { name: 'Request ID' }), { target: { value: ' answered-1 ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Inspect request' }));
    const summary = await screen.findByText('Processing trace');
    expect(request).toHaveBeenCalledWith('/admin/failures/answered-1');
    const trace = summary.closest('details')!;
    expect(trace.hasAttribute('open')).toBe(false);
    fireEvent.click(summary);
    expect(trace.hasAttribute('open')).toBe(true);
    const observations = within(trace);
    expect(observations.getByText('Compare diffusion and osmosis at 20 degrees.')).toBeTruthy();
    expect(observations.getByText('No')).toBeTruthy();
    expect(observations.getByText('cpu')).toBeTruthy();
    expect(observations.getByText('0 ms')).toBeTruthy();
    expect(observations.getByText('450 ms')).toBeTruthy();
    expect(observations.getByText('Partial')).toBeTruthy();
    expect(observations.getByText('Review required')).toBeTruthy();
    expect(observations.getByText('Hint')).toBeTruthy();
    expect(observations.getByText('prior-1')).toBeTruthy();
    expect(observations.getAllByText(/Below relevance threshold/)).toHaveLength(2);
    expect(observations.getByText(/Independent support and teaching quality review remain separate/)).toBeTruthy();
    const dialog = screen.getByRole('dialog', { name: 'Response diagnostics' });
    expect([...dialog.querySelectorAll('.diagnostic-counts dd')].map(item => item.textContent)).toEqual(['8', '3', '2', '1']);
    expect(within(dialog).getByText(/summary counts show the distinct per-part fallback pool/)).toBeTruthy();
    const wholeSurvivors = observations.getByText('Whole-question relevance survivors').closest('div')!;
    expect(within(wholeSurvivors).getByText('0')).toBeTruthy();
    const partSummary = observations.getByText('Retrieved part 1 · part_1');
    expect(partSummary.closest('details')!.hasAttribute('open')).toBe(false);
    fireEvent.click(partSummary);
    expect(partSummary.closest('details')!.hasAttribute('open')).toBe(true);
    const part = within(partSummary.closest('details')!);
    expect(part.getByText('Explain osmosis.')).toBeTruthy();
    expect(part.getByText('revision-1')).toBeTruthy();
    expect(part.getByText(/Part-query raw score -6.5/)).toBeTruthy();
  });

  it('preserves real lookup errors and safely encodes the supplied request identifier', async () => {
    vi.mocked(request).mockImplementation(async path => {
      if (path.startsWith('/admin/failures/')) throw new ApiError('NOT_FOUND', 'The request was not found.', 404);
      return { items: [], total: 0, limit: 50, offset: 0 };
    });
    render(<FailuresPage />);
    await screen.findByText('No matching outcomes');
    fireEvent.change(screen.getByRole('textbox', { name: 'Request ID' }), { target: { value: 'other/request?scope=all' } });
    fireEvent.click(screen.getByRole('button', { name: 'Inspect request' }));
    await screen.findByRole('alert');
    expect(request).toHaveBeenCalledWith('/admin/failures/other%2Frequest%3Fscope%3Dall');
    expect(screen.queryByText('Processing trace')).toBeNull();
  });

  it('shows forbidden errors instead of an empty successful diagnostic list', async () => {
    vi.mocked(request).mockRejectedValue(new ApiError('FORBIDDEN', 'Administrator access required.', 403));
    render(<FailuresPage />);
    await screen.findByRole('alert');
    expect(screen.queryByText('No matching outcomes')).toBeNull();
    expect(screen.queryByText('0 results')).toBeNull();
  });
});
