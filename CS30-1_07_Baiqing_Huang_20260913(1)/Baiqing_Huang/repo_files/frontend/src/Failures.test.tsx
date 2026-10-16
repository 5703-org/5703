import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { FailuresPage, type FailureDetail, type FailureSummary } from './Failures';
import { ApiError, request } from './api';

vi.mock('./api', async importOriginal => ({ ...await importOriginal<typeof import('./api')>(), request: vi.fn() }));
const record: FailureSummary = { request_id: 'request-1', session_id: 'session-1', owner_id: 'owner-1', question: 'A recorded question', state: 'refused', response_type: 'refusal', error_code: null, error_message: null, created_at: '2026-09-13T01:00:00Z', model: { provider: 'mock', model: 'mock-v1' }, counts: { candidates: 8, submitted: 3, cited: 0 } };
beforeEach(() => {
  vi.clearAllMocks();
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
});
afterEach(cleanup);

describe('response diagnostics', () => {
  it('distinguishes candidate/submitted/cited counts and unrecorded historical data', async () => {
    vi.mocked(request).mockResolvedValue({ items: [record, { ...record, request_id: 'historical', question: 'Historical question', counts: { candidates: null, submitted: null, cited: null } }], total: 2, offset: 0, limit: 50 });
    render(<FailuresPage />);
    await screen.findByText('A recorded question');
    expect(screen.getAllByText('Not recorded')).toHaveLength(3);
    expect(screen.getByText('8')).toBeTruthy(); expect(screen.getByText('3')).toBeTruthy(); expect(screen.getByText('0')).toBeTruthy();
    expect(screen.getAllByText('Actually cited')).toHaveLength(2);
  });

  it('loads safe persisted detail and applies actual outcome filters', async () => {
    const detail: FailureDetail = { ...record, http_trace_id: 'trace-1', stages: [{ stage: 'retrieving', status: 'completed', detail: 'Eight candidates' }], budget: {}, attempts: [], retrieval_query: 'Prepared question', evidence: { candidate_chunk_ids: ['candidate'], submitted_chunk_ids: ['submitted'], cited_chunk_ids: [] }, answer_text: 'The available sources do not support this question.', refusal_reason: 'NO_EVIDENCE' };
    vi.mocked(request).mockImplementation(async path => path === '/admin/failures/request-1' ? detail : { items: [record], total: 1, offset: 0, limit: 50 });
    render(<FailuresPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Inspect response' }));
    await screen.findByText('Prepared question');
    expect(request).toHaveBeenCalledWith('/admin/failures/request-1');
    expect(screen.getByText('Eight candidates')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Close response diagnostics' }));
    fireEvent.change(screen.getByRole('combobox', { name: 'Outcome' }), { target: { value: 'error' } });
    await screen.findByText('A recorded question');
    expect(request).toHaveBeenLastCalledWith('/admin/failures?limit=50&offset=0&state=error', expect.any(Object));
  });

  it('shows forbidden errors instead of an empty successful diagnostic list', async () => {
    vi.mocked(request).mockRejectedValue(new ApiError('FORBIDDEN', 'Administrator access required.', 403));
    render(<FailuresPage />);
    await screen.findByRole('alert');
    expect(screen.queryByText('No matching outcomes')).toBeNull();
    expect(screen.queryByText('0 results')).toBeNull();
  });
});
