import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Chat, EvidenceViewer } from './Chat';
import { api, ApiError, post } from './api';
import type { Answer, Session } from './types';

vi.mock('./api', async importOriginal => {
  const original = await importOriginal<typeof import('./api')>();
  return { ...original, api: { ...original.api, session: vi.fn(), messages: vi.fn(), send: vi.fn(), job: vi.fn(), evidence: vi.fn(), feedback: vi.fn() }, post: vi.fn(), put: vi.fn() };
});
const session: Session = { id: 'session-one', title: 'My conversation', status: 'active', version: 1, created_at: '', updated_at: '' };
const props = { sessionId: 'session-one', userId: 'user-one', profile: null, capabilities: { model_mode: 'mock' as const, chat_ready: true, evaluation_ready: false, missing_reasons: { chat: [], evaluation: ['No evaluation data'] }, providers: [], feature_flags: {}, contract_versions: [] }, onCreated: vi.fn(), refreshSessions: vi.fn(async () => {}), onOverlay: vi.fn() };
const answer: Answer = { id: 'answer-one', request_id: 'request-one', job_id: 'job-one', message_id: 'message-two', mode: 'interactive_chat', response_schema: 'chat_response_v1', status: 'answered', model_mode: 'mock', response: { schema_version: 'chat_response_v1', response_type: 'answer', answer_text: 'Original successful response. [ev_001]', short_answer: 'Original answer', citations: ['ev_001'], refusal_reason: null, follow_up_questions: [], confidence: null }, evidence: [{ evidence_id: 'ev_001', chunk_id: 'chunk-one', asset_id: 'asset-one', processing_id: 'processing-one', source_title: 'Original source', section: 'Section 1', pages: [4], locator: 'page 4', text: 'Original permitted passage', text_hash: 'original-hash', context_order: 0 }], profile_snapshot: null, conversation_snapshot: null, timing: {}, can_regenerate: true };
beforeEach(() => {
  sessionStorage.clear(); vi.clearAllMocks();
  vi.mocked(api.session).mockResolvedValue(session);
  vi.mocked(api.messages).mockResolvedValue({ items: [], next_after_sequence: null, active_job_id: null, latest_job_id: null });
  vi.mocked(api.job).mockResolvedValue({ id: 'job-one', request_id: 'request-one', state: 'running', stage: 'generating', error: null, answer_id: null, can_retry: false, created_at: '', updated_at: '' });
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); this.querySelector<HTMLButtonElement>('button')?.focus(); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
});
afterEach(cleanup);
describe('chat lifecycle controls', () => {
  it('renders stored legacy MCQ by its schema while keeping the natural-language composer', async () => {
    const historical: Answer = { ...answer, id: 'legacy-answer', mode: 'benchmark_mcq', response_schema: 'mcq_response_v1', can_regenerate: false, response: { question_id: 'legacy-question', answer: 'B', answer_text: 'Chemical energy', citations: ['ev_001'], confidence: null, refused: false, refusal_reason: null, short_explanation: 'Recorded historical explanation. [ev_001]' } };
    vi.mocked(api.messages).mockResolvedValue({ items: [{ id: 'legacy-message', session_id: 'session-one', sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: historical.id, answer: historical, request_id: historical.request_id, created_at: '' }], next_after_sequence: null, active_job_id: null, latest_job_id: null });
    vi.mocked(api.evidence).mockResolvedValue(historical.evidence[0]);
    render(<Chat {...props} />);
    await screen.findByText('Historical MCQ result');
    expect(screen.getByText('B. Chemical energy')).toBeTruthy();
    expect(screen.getByText('Recorded historical explanation.', { exact: false })).toBeTruthy();
    expect(screen.getByRole('textbox', { name: 'Message Learning Assistant' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Regenerate' })).toBeNull();
    expect(api.send).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Open source 1' }));
    await screen.findByText('Original permitted passage');
    expect(api.evidence).toHaveBeenCalledWith('legacy-answer', 'ev_001');
  });
  it('renders a refused legacy MCQ without inventing a selected option', async () => {
    const historical: Answer = { ...answer, id: 'legacy-refusal', mode: 'benchmark_mcq', response_schema: 'mcq_response_v1', can_regenerate: false, response: { question_id: 'legacy-unanswered', answer: null, answer_text: null, citations: [], confidence: null, refused: true, refusal_reason: 'NO_EVIDENCE', short_explanation: 'Historical record: no source supported an option.' }, evidence: [] };
    vi.mocked(api.messages).mockResolvedValue({ items: [{ id: 'legacy-message', session_id: 'session-one', sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: historical.id, answer: historical, request_id: historical.request_id, created_at: '' }], next_after_sequence: null, active_job_id: null, latest_job_id: null });
    render(<Chat {...props} />);
    await screen.findByText('Historical MCQ result');
    expect(screen.getByText('Historical record: no source supported an option.')).toBeTruthy();
    expect(document.querySelector('.prose')?.textContent).not.toContain('null');
    expect(screen.queryByRole('button', { name: /^Sources/ })).toBeNull();
    expect(api.send).not.toHaveBeenCalled();
  });
  it('preserves a draft when the server rejects a busy session', async () => {
    vi.mocked(api.send).mockRejectedValue(new ApiError('SESSION_BUSY', 'Another response is already running.', 409));
    render(<Chat {...props} />);
    const input = screen.getByRole('textbox', { name: 'Message Learning Assistant' });
    fireEvent.change(input, { target: { value: 'Why does it need light?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await screen.findByText('Another response is already running.');
    expect((input as HTMLTextAreaElement).value).toBe('Why does it need light?');
    expect(api.send).toHaveBeenCalledWith('session-one', 'Why does it need light?', true, expect.any(String));
  });
  it.each([false, true])('reveals a rejected submission unless the user started reading older messages: %s', async readingOlder => {
    vi.mocked(api.messages).mockResolvedValue({ items: [{ id: 'message-two', session_id: 'session-one', sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: answer.id, answer, request_id: answer.request_id, created_at: '' }], next_after_sequence: null, active_job_id: null, latest_job_id: null });
    let rejectSubmission: (error: Error) => void = () => {};
    vi.mocked(api.send).mockImplementation(() => new Promise((_resolve, reject) => { rejectSubmission = reject; }));
    render(<Chat {...props} />);
    await screen.findByText('Original successful response.', { exact: false });
    const transcript = screen.getByTestId('transcript');
    // jsdom has no layout. Model the height added by pending/error feedback and
    // the browser's clamped scrollTop; real viewport bounds have separate e2e proof.
    const height = () => 1200 + (screen.queryByRole('alert') ? 180 : 0) + (document.querySelector('.generation-status') ? 60 : 0);
    let scrollTop = 700;
    Object.defineProperties(transcript, {
      clientHeight: { configurable: true, get: () => 500 },
      scrollHeight: { configurable: true, get: height },
      scrollTop: { configurable: true, get: () => scrollTop, set: value => { scrollTop = Math.max(0, Math.min(value, height() - 500)); } },
    });
    fireEvent.scroll(transcript);
    const input = screen.getByRole('textbox', { name: 'Message Learning Assistant' });
    fireEvent.change(input, { target: { value: 'Retain this question after the actual request fails.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    expect(api.send).toHaveBeenCalledTimes(1);
    if (readingOlder) {
      transcript.scrollTop = 120;
      fireEvent.scroll(transcript);
    }
    await act(async () => { rejectSubmission(new ApiError('SESSION_BUSY', 'Another response is already running.', 409)); });
    expect(screen.getByRole('alert').textContent).toContain('Another response is already running.');
    expect((input as HTMLTextAreaElement).value).toBe('Retain this question after the actual request fails.');
    expect(transcript.scrollTop).toBe(readingOlder ? 120 : transcript.scrollHeight - transcript.clientHeight);
    if (readingOlder) expect(screen.getByRole('button', { name: 'Jump to latest' })).toBeTruthy();
  });
  it('does not submit Enter while composing IME or Shift+Enter', async () => {
    render(<Chat {...props} />);
    const input = screen.getByRole('textbox', { name: 'Message Learning Assistant' });
    fireEvent.change(input, { target: { value: 'A question' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter', isComposing: true });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter', shiftKey: true });
    expect(api.send).not.toHaveBeenCalled();
  });
  it('deduplicates rapid submissions and reuses a key after a lost response', async () => {
    let reject: (error: Error) => void = () => {};
    vi.mocked(api.send).mockImplementation(() => new Promise((_resolve, rejectCall) => { reject = rejectCall; }));
    render(<Chat {...props} />);
    const input = screen.getByRole('textbox', { name: 'Message Learning Assistant' });
    fireEvent.change(input, { target: { value: 'What is photosynthesis?' } });
    fireEvent.keyDown(input, { key: 'Enter' }); fireEvent.keyDown(input, { key: 'Enter' });
    expect(api.send).toHaveBeenCalledTimes(1);
    const key = vi.mocked(api.send).mock.calls[0][3];
    reject(new Error('Connection lost.'));
    await screen.findByText('Connection lost.');
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(vi.mocked(api.send).mock.calls[1][3]).toBe(key);
  });
  it('sends only natural text and the profile flag after turning profiles off', async () => {
    vi.mocked(api.send).mockRejectedValue(new Error('Kept for observation'));
    render(<Chat {...props} />);
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Explain it more simply.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await waitFor(() => expect(api.send).toHaveBeenCalledWith('session-one', 'Explain it more simply.', false, expect.any(String)));
  });
  it('keeps the previous successful answer when regeneration fails', async () => {
    vi.mocked(api.messages).mockResolvedValue({ items: [{ id: 'message-two', session_id: 'session-one', sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: answer.id, answer, request_id: answer.request_id, created_at: '' }], next_after_sequence: null, active_job_id: null, latest_job_id: null });
    vi.mocked(post).mockRejectedValue(new ApiError('REGENERATION_UNAVAILABLE', 'The source is no longer available.', 409));
    render(<Chat {...props} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Regenerate' }));
    await screen.findByText('The source is no longer available.');
    expect(screen.getByText('Original successful response.', { exact: false })).toBeTruthy();
    expect(document.querySelector('[data-answer-id="answer-one"]')).not.toBeNull();
  });
});
describe('evidence availability', () => {
  it('uses the original evidence endpoint and never substitutes cached source text on 410', async () => {
    vi.mocked(api.evidence).mockRejectedValue(new ApiError('EVIDENCE_UNAVAILABLE', 'This source was revoked.', 410));
    render(<EvidenceViewer answer={answer} onClose={vi.fn()} />);
    await screen.findByText('This source was revoked.');
    expect(api.evidence).toHaveBeenCalledWith('answer-one', 'ev_001');
    expect(screen.queryByText('Original permitted passage')).toBeNull();
  });
  it('displays complete original source content and provenance', async () => {
    vi.mocked(api.evidence).mockResolvedValue(answer.evidence[0]);
    render(<EvidenceViewer answer={answer} onClose={vi.fn()} />);
    await screen.findByText('Original permitted passage');
    expect(screen.getByText('Original source')).toBeTruthy();
    expect(screen.getByText('original-hash', { exact: false })).toBeTruthy();
    expect(screen.queryByText('OpenStax / Rice University · Access for free at openstax.org')).toBeNull();
  });
  it.each(['https://openstax.org/books/chemistry-2e/pages/preface', 'https://assets.openstax.org/oscms-prodcms/media/documents/chemistry-2e_-_WEB.pdf'])('attributes the saved official source %s and preserves its extraction note', async sourceUrl => {
    vi.mocked(api.evidence).mockResolvedValue({ ...answer.evidence[0], source_url: sourceUrl, license: 'CC BY-NC-SA 4.0', locator: 'PDF physical pages 17. Figures or formulas may require viewing original PDF.' });
    render(<EvidenceViewer answer={answer} onClose={vi.fn()} />);
    await screen.findByText('OpenStax / Rice University · Access for free at openstax.org');
    const link = screen.getByRole('link', { name: 'View original source' });
    expect(link.getAttribute('href')).toBe(sourceUrl);
    expect(link.getAttribute('target')).toBe('_blank');
    expect(link.getAttribute('rel')).toBe('noopener noreferrer');
    expect(screen.getByText('Figures or formulas may require viewing original PDF.', { exact: false }).className).toBe('source-locator');
  });
  it.each([null, 'https://example.org/authored-fixture', 'https://openstax.org.example.com/source', 'https://example.com/?source=openstax.org', 'http://openstax.org/source', 'javascript:alert(1)', 'not a URL'])('does not infer publisher attribution from a title or invalid source URL %s', async sourceUrl => {
    vi.mocked(api.evidence).mockResolvedValue({ ...answer.evidence[0], source_title: 'A fixture discussing OpenStax', source_url: sourceUrl });
    render(<EvidenceViewer answer={answer} onClose={vi.fn()} />);
    await screen.findByText('Original permitted passage');
    expect(screen.queryByText('OpenStax / Rice University · Access for free at openstax.org')).toBeNull();
    expect(screen.queryByRole('link', { name: 'View original source' })).toBeNull();
  });
});
