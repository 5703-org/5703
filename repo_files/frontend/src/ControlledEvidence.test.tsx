import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { api, ApiError } from './api';
import { EvidenceViewer } from './Chat';
import type { Answer } from './types';
import type { CitationView } from './learning-types';

vi.mock('./api', async original => { const value = await original<typeof import('./api')>(); return { ...value, api: { ...value.api, exposure: vi.fn(), evidence: vi.fn() } }; });
const preview: CitationView = { evidence_id: 'ev_001', claim_ids: ['claim-one'], title: 'Approved hint source', source_title: null, section: null, pages: [10], segments: [{ text: 'Consider the energy change. ', highlight: false }, { text: '<b>Compare the two sides.</b>', highlight: true, fragment_ids: ['fragment-one'] }], available_actions: ['citation_opened', 'full_source_requested'], source_url: null, license: null };
const answer: Answer = { id: 'answer-one', request_id: 'request-one', job_id: 'job-one', message_id: 'message-one', mode: 'interactive_chat', response_schema: 'chat_response_v1', status: 'answered', model_mode: 'mock', answer_mode: 'textbook', source_provenance: 'textbook_evidence', response: { schema_version: 'chat_response_v1', response_type: 'answer', answer_text: 'Compare the sides. [ev_001]', short_answer: null, citations: ['ev_001'], refusal_reason: null, follow_up_questions: [], confidence: null }, evidence: [], profile_snapshot: null, conversation_snapshot: null, timing: {}, can_regenerate: false, teaching_mode: 'hint', task_id: 'task-one', help_level: 1, presentation: { id: 'presentation-one', task_id: 'task-one', teaching_mode: 'hint', help_level: 1, policy_version: 'joint-v1', content_hash: 'projection-hash', citation_views: [preview] } };
beforeEach(() => {
  vi.clearAllMocks();
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
  vi.mocked(api.exposure).mockResolvedValue({ id: 'opened-one', kind: 'citation_opened', presentation_id: 'presentation-one', citation_view: preview });
});
afterEach(cleanup);

it('keeps complete text and its URL absent until a deliberate successful full-source event', async () => {
  const full = { ...preview, title: 'Full source', segments: [{ text: 'Complete explanation with its result.', highlight: true, fragment_ids: ['fragment-one'] }], source_url: 'https://openstax.org/books/chemistry-2e', license: 'CC BY 4.0' };
  vi.mocked(api.exposure).mockResolvedValueOnce({ id: 'opened-one', kind: 'citation_opened', presentation_id: 'presentation-one', citation_view: preview }).mockResolvedValueOnce({ id: 'expanded-one', kind: 'full_source_requested', presentation_id: 'presentation-one', citation_view: full });
  render(<EvidenceViewer answer={answer} initialId="ev_001" claimId="claim-one" onClose={() => {}} />);
  await screen.findByText('<b>Compare the two sides.</b>');
  expect(document.querySelector('mark')?.textContent).toBe('<b>Compare the two sides.</b>');
  expect(document.querySelector('b')).toBeNull();
  expect(document.body.innerHTML).not.toContain('Complete explanation');
  expect(document.body.innerHTML).not.toContain('https://openstax.org');
  expect(api.evidence).not.toHaveBeenCalled();
  expect(api.exposure).toHaveBeenCalledExactlyOnceWith('answer-one', { kind: 'citation_opened', presentation_id: 'presentation-one', evidence_id: 'ev_001', claim_id: 'claim-one', surface: 'citation' }, expect.any(String));
  fireEvent.click(screen.getByRole('button', { name: 'Show complete source' }));
  await screen.findByText('Complete explanation with its result.');
  expect(api.exposure).toHaveBeenLastCalledWith('answer-one', expect.objectContaining({ kind: 'full_source_requested', surface: 'full_source', claim_id: 'claim-one' }), expect.any(String));
  expect(screen.getByRole('link', { name: 'View original source' }).getAttribute('href')).toBe(full.source_url);
});

it('preserves the approved preview after an expansion failure and reuses the same event key on retry', async () => {
  vi.mocked(api.exposure).mockResolvedValueOnce({ id: 'opened-one', kind: 'citation_opened', presentation_id: 'presentation-one', citation_view: preview }).mockRejectedValueOnce(new ApiError('EVIDENCE_UNAVAILABLE', 'This source is no longer available.', 410)).mockRejectedValueOnce(new ApiError('EVIDENCE_UNAVAILABLE', 'This source is no longer available.', 410));
  render(<EvidenceViewer answer={answer} onClose={() => {}} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Show complete source' }));
  await screen.findByText('This source is no longer available.');
  expect(screen.getByText('<b>Compare the two sides.</b>')).toBeTruthy();
  expect(screen.queryByText('Complete source requested')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Show complete source' }));
  await screen.findByText('This source is no longer available.');
  expect(vi.mocked(api.exposure).mock.calls[1][2]).toBe(vi.mocked(api.exposure).mock.calls[2][2]);
});

it('fails closed for hint records without a projection and never falls back to full legacy evidence', () => {
  render(<EvidenceViewer answer={{ ...answer, presentation: null }} onClose={() => {}} />);
  expect(screen.getByText(/approved preview for this hint is unavailable/)).toBeTruthy();
  expect(api.evidence).not.toHaveBeenCalled(); expect(api.exposure).not.toHaveBeenCalled();
});

it('keeps a source permission error visible without substituting cached preview data', async () => {
  vi.mocked(api.exposure).mockRejectedValue(new ApiError('NOT_FOUND', 'The source is unavailable.', 404));
  render(<EvidenceViewer answer={answer} onClose={() => {}} />);
  await screen.findByText('The source is unavailable.');
  expect(document.body.innerHTML).not.toContain('Compare the two sides.');
  expect(screen.queryByRole('button', { name: 'Show complete source' })).toBeNull();
});
