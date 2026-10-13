import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { request } from './api';
import { OperationsPage, type OperationsOverview } from './Operations';
vi.mock('./api', async original => ({ ...await original<typeof import('./api')>(), request: vi.fn() }));
const queue = { queued: 2, running: 0, retry_wait: 0, failed: 1, oldest_queued_seconds: 12 };
const overview: OperationsOverview = { observed_at: '2026-09-30T00:00:00Z', database: 'up', corpus: { active_release_id: 'release', release_state: 'active', document_count: 4, chunk_vector_count: 10594 }, model: { answer: null, checker: null }, queues: { interactive: queue, background: queue }, worker_locks: { observation: 'postgres_advisory_lock', layout: 'split', interactive: { lock_observed: true }, background: { lock_observed: true } }, recent_failures: [{ job_id: 'job', request_id: 'request', kind: 'answer', error_code: 'CHECKER_TIMEOUT', updated_at: '' }], experiment_states: {}, recent_usage: { sampled_requests: 5, requests_with_usage: 2, input_tokens: 100, output_tokens: 20, scope: 'Bounded saved request counters.', cost_estimate: null } };
beforeEach(() => { vi.resetAllMocks(); }); afterEach(cleanup);
it('shows incomplete accounting and links the exact failed request without claiming worker health or a free cost', async () => {
  vi.mocked(request).mockResolvedValue(overview); const go = vi.fn(); render(<OperationsPage go={go} />); await screen.findByText('2 of 5 sampled requests have provider counters.'); expect(screen.getByText('Unavailable · tariff evidence is required')).toBeTruthy(); expect(screen.getByText('Worker lock observation: Split')).toBeTruthy(); expect(screen.getAllByText('Worker lock observed: Yes')).toHaveLength(2); expect(screen.getByText(/do not prove the worker is responsive/)).toBeTruthy(); fireEvent.click(screen.getByRole('button', { name: 'Inspect request' })); expect(go).toHaveBeenCalledWith('/admin/failures/request');
});
it('shows unknown worker lock state without claiming a stopped worker', async () => {
  vi.mocked(request).mockResolvedValue({ ...overview, worker_locks: { observation: 'unavailable', layout: 'unavailable', interactive: { lock_observed: null }, background: { lock_observed: null } } });
  render(<OperationsPage go={vi.fn()} />);
  await screen.findByText('Worker lock observation: Unavailable');
  expect(screen.getAllByText('Worker lock observed: Unknown')).toHaveLength(2);
});
it('removes a previous operational snapshot when its refresh fails', async () => {
  vi.mocked(request).mockResolvedValueOnce(overview).mockRejectedValueOnce(new Error('Operations unavailable.')); render(<OperationsPage go={vi.fn()} />); await screen.findByText('Database: Up'); fireEvent.click(screen.getByRole('button', { name: 'Refresh operations' })); await screen.findByText('Operations unavailable.'); expect(screen.queryByText('Database: Up')).toBeNull();
});
