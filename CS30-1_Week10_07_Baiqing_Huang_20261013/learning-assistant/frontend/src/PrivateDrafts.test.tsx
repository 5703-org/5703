import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { PrivateDrafts } from './PrivateDrafts';
import { ApiError, request } from './api';

vi.mock('./api', async importOriginal => ({ ...await importOriginal<typeof import('./api')>(), request: vi.fn() }));
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

it('loads drafts on explicit inspection and renders only selected text and source excerpts', async () => {
  vi.mocked(request).mockResolvedValue({ request_id: 'r/1', truncated: false, items: [{ id: 'd1', revision: 1, recorded_at: '2026-10-01', answer_text: '<script>unsafe()</script>', truncated: false, source_status: 'validated', withheld_source_count: 0, sources: [{ evidence_id: 'e1', chunk_id: 'c1', title: 'Biology', section: 'Photosynthesis', pages: [120], text_hash: 'abc', excerpts: ['Light energy changes into chemical energy.'] }], raw_model_output: 'secret provider payload', rubric: 'hidden scoring rule' }] });
  const view = render(<PrivateDrafts requestId="r/1" />);
  expect(request).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Load private drafts' }));
  await screen.findByText('<script>unsafe()</script>');
  expect(request).toHaveBeenCalledWith('/admin/failures/r%2F1/drafts', expect.objectContaining({ signal: expect.any(AbortSignal) }));
  expect(view.container.querySelector('script')).toBeNull();
  expect(screen.queryByText('secret provider payload')).toBeNull();
  expect(screen.queryByText('hidden scoring rule')).toBeNull();
  expect(screen.getByText('Light energy changes into chemical energy.')).toBeTruthy();
});

it('shows a real authorization failure and permits an explicit retry', async () => {
  vi.mocked(request).mockRejectedValueOnce(new ApiError('FORBIDDEN', 'Administrator access required.', 403));
  render(<PrivateDrafts requestId="r1" />);
  fireEvent.click(screen.getByRole('button', { name: 'Load private drafts' }));
  await screen.findByRole('alert');
  vi.mocked(request).mockResolvedValue({ request_id: 'r1', truncated: false, items: [] });
  fireEvent.click(screen.getByRole('button', { name: 'Load private drafts' }));
  await screen.findByText('No generated drafts were saved for this request.');
  expect(screen.queryByRole('alert')).toBeNull();
});
