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
const answer: Answer = { answer_mode: 'textbook', source_provenance: 'textbook_evidence', id: 'answer-one', request_id: 'request-one', job_id: 'job-one', message_id: 'message-two', mode: 'interactive_chat', response_schema: 'chat_response_v1', status: 'answered', model_mode: 'mock', response: { schema_version: 'chat_response_v1', response_type: 'answer', answer_text: 'Original successful response. [ev_001]', short_answer: 'Original answer', citations: ['ev_001'], refusal_reason: null, follow_up_questions: [], confidence: null }, evidence: [{ evidence_id: 'ev_001', chunk_id: 'chunk-one', asset_id: 'asset-one', processing_id: 'processing-one', source_title: 'Original source', section: 'Section 1', pages: [4], locator: 'page 4', text: 'Original permitted passage', text_hash: 'original-hash', context_order: 0 }], profile_snapshot: null, conversation_snapshot: null, timing: {}, can_regenerate: true };
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
  it('keeps direct teaching as the default and stores an explicit hint choice with a failed draft', async () => {
    vi.mocked(api.send).mockRejectedValue(new ApiError('CONNECTION_ERROR', 'Connection interrupted.'));
    render(<Chat {...props} />);
    await screen.findByText(/What would you like/);
    expect((screen.getByRole('combobox', { name: 'Teaching style' }) as HTMLSelectElement).value).toBe('direct');
    fireEvent.change(screen.getByRole('combobox', { name: 'Teaching style' }), { target: { value: 'hint' } });
    fireEvent.change(screen.getByRole('textbox', { name: 'Message Learning Assistant' }), { target: { value: 'Help me compare these cells.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await screen.findByText('Connection interrupted.');
    expect(api.send).toHaveBeenCalledWith('session-one', 'Help me compare these cells.', true, expect.any(String), 'textbook', { teaching_mode: 'hint' });
    expect((screen.getByRole('textbox', { name: 'Message Learning Assistant' }) as HTMLTextAreaElement).value).toBe('Help me compare these cells.');
    expect(JSON.parse(sessionStorage.getItem('cs30.draft.user-one.session-one.teaching')!)).toEqual({ teaching_mode: 'hint' });
  });
  it.each([
    ['Another hint', 'more_hint', 'hint', 'Give me another hint for this problem.'],
    ['Show full explanation', 'full_explanation', 'direct', 'Please give me the full explanation for this problem.'],
  ])('sends the explicit %s action against the persisted task', async (button, task_action, teaching_mode, text) => {
    const stored: Answer = { ...answer, teaching_mode: 'hint', task_id: 'task-one', help_level: 2 };
    vi.mocked(api.messages).mockResolvedValue({ items: [{ id: 'message-two', session_id: 'session-one', sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: stored.id, answer: stored, request_id: stored.request_id, created_at: '' }], next_after_sequence: null, active_job_id: null, latest_job_id: null });
    vi.mocked(api.send).mockResolvedValue({ request_id: 'request-new', job_id: 'job-one', user_message_id: 'message-new', poll_url: '/jobs/job-one' });
    render(<Chat {...props} />);
    fireEvent.click(await screen.findByRole('button', { name: button }));
    await waitFor(() => expect(api.send).toHaveBeenCalledWith('session-one', text, true, expect.any(String), 'textbook', { teaching_mode, task_action, task_id: 'task-one' }));
  });
  it('lets the server resolve ordinary continuation and explicitly resets a new problem to direct', async () => {
    const stored: Answer = { ...answer, teaching_mode: 'hint', task_id: 'task-one', help_level: 2 };
    vi.mocked(api.messages).mockResolvedValue({ items: [{ id: 'message-two', session_id: 'session-one', sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: stored.id, answer: stored, request_id: stored.request_id, created_at: '' }], next_after_sequence: null, active_job_id: null, latest_job_id: null });
    vi.mocked(api.send).mockRejectedValue(new ApiError('CONNECTION_ERROR', 'Connection interrupted.'));
    render(<Chat {...props} />);
    await screen.findByRole('button', { name: 'Another hint' });
    expect((screen.getByRole('combobox', { name: 'Teaching style' }) as HTMLSelectElement).value).toBe('hint');
    fireEvent.change(screen.getByRole('textbox', { name: 'Message Learning Assistant' }), { target: { value: 'How about a new topic?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await screen.findByText('Connection interrupted.');
    expect(vi.mocked(api.send).mock.calls[0]).toEqual(['session-one', 'How about a new topic?', true, expect.any(String), 'textbook']);
    fireEvent.click(screen.getByRole('button', { name: 'Start a new problem' }));
    expect((screen.getByRole('combobox', { name: 'Teaching style' }) as HTMLSelectElement).value).toBe('direct');
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await waitFor(() => expect(api.send).toHaveBeenCalledTimes(2));
    expect(api.send).toHaveBeenLastCalledWith('session-one', 'How about a new topic?', true, expect.any(String), 'textbook', { teaching_mode: 'direct', task_action: 'new' });
  });
  it('keeps physical-page and graphical limitations readable without repeating the same locator', async () => {
    vi.mocked(api.evidence).mockResolvedValue({ ...answer.evidence[0], section: 'Chapter 5 / Key Terms', pages: [145], locator: 'Chapter 5 / Key Terms; PDF physical pages 145; Figures or formulas may require viewing the original PDF.' });
    render(<EvidenceViewer answer={answer} onClose={() => {}} />);
    await screen.findByText('Original permitted passage');
    expect(document.querySelector('.source-locator')?.textContent).toBe('Chapter 5 / Key Terms; PDF physical pages 145; Figures or formulas may require viewing the original PDF.');
  });
  it('shows only actually cited sources, excluding additional submitted passages', async () => {
    const stored: Answer = { ...answer, evidence: [...answer.evidence, { ...answer.evidence[0], evidence_id: 'ev_002', text: 'Submitted but not cited' }] };
    vi.mocked(api.messages).mockResolvedValue({ items: [{ id: 'message-two', session_id: 'session-one', sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: stored.id, answer: stored, request_id: stored.request_id, created_at: '' }], next_after_sequence: null, active_job_id: null, latest_job_id: null });
    vi.mocked(api.evidence).mockResolvedValue(stored.evidence[0]);
    render(<Chat {...props} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Sources 1' }));
    await screen.findByText('Original permitted passage');
    expect(screen.queryByRole('button', { name: 'Source 2' })).toBeNull();
    expect(api.evidence).toHaveBeenCalledExactlyOnceWith('answer-one', 'ev_001');
  });
  it('treats an explicitly empty citation array as zero even when evidence was submitted', async () => {
    const stored: Answer = { ...answer, response: { ...answer.response, citations: [] } };
    vi.mocked(api.messages).mockResolvedValue({ items: [{ id: 'message-two', session_id: 'session-one', sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: stored.id, answer: stored, request_id: stored.request_id, created_at: '' }], next_after_sequence: null, active_job_id: null, latest_job_id: null });
    render(<Chat {...props} />);
    await screen.findByText('Original successful response.', { exact: false });
    expect(screen.queryByRole('button', { name: /^Sources/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /^Open source/ })).toBeNull();
  });
  it('labels missing historical citation usage and rejects an uncited initial selection', async () => {
    const stored: Answer = { ...answer, evidence: [...answer.evidence, { ...answer.evidence[0], evidence_id: 'ev_002' }] };
    vi.mocked(api.evidence).mockResolvedValue(stored.evidence[0]);
    const { unmount } = render(<EvidenceViewer answer={stored} initialId="ev_002" onClose={() => {}} />);
    await screen.findByText('Original permitted passage');
    expect(api.evidence).toHaveBeenLastCalledWith('answer-one', 'ev_001');
    unmount();
    const historical = { ...answer, response: { ...answer.response, citations: undefined } } as unknown as Answer;
    render(<EvidenceViewer answer={historical} onClose={() => {}} />);
    expect(screen.getByText('Historical stored sources. Citation usage was not recorded for this response.')).toBeTruthy();
    await screen.findByText('Original permitted passage');
  });
  it('renders stored legacy MCQ by its schema while keeping the natural-language composer', async () => {
    const historical = { ...answer, answer_mode: undefined, source_provenance: undefined, id: 'legacy-answer', mode: 'benchmark_mcq', response_schema: 'mcq_response_v1', can_regenerate: false, response: { question_id: 'legacy-question', answer: 'B', answer_text: 'Chemical energy', citations: ['ev_001'], confidence: null, refused: false, refusal_reason: null, short_explanation: 'Recorded historical explanation. [ev_001]' } } as unknown as Answer;
    vi.mocked(api.messages).mockResolvedValue({ items: [{ id: 'legacy-message', session_id: 'session-one', sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: historical.id, answer: historical, request_id: historical.request_id, created_at: '' }], next_after_sequence: null, active_job_id: null, latest_job_id: null });
    vi.mocked(api.evidence).mockResolvedValue(historical.evidence[0]);
    render(<Chat {...props} />);
    await screen.findByText('Historical MCQ result');
    expect(document.querySelector('.answer-metadata')?.textContent).toContain('Textbook sources');
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
    expect(api.send).toHaveBeenCalledWith('session-one', 'Why does it need light?', true, expect.any(String), 'textbook');
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
  it('sends natural text with the explicit source choice and profile flag after turning profiles off', async () => {
    vi.mocked(api.send).mockRejectedValue(new Error('Kept for observation'));
    render(<Chat {...props} />);
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Explain it more simply.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await waitFor(() => expect(api.send).toHaveBeenCalledWith('session-one', 'Explain it more simply.', false, expect.any(String), 'textbook'));
  });
  it('defaults to textbook sources and sends general knowledge only after an explicit accessible selection', async () => {
    const user = userEvent.setup();
    vi.mocked(api.send).mockRejectedValue(new ApiError('PROVIDER_AUTH_ERROR', 'The provider rejected the credential.', 502));
    render(<Chat {...props} />);
    const choice = screen.getByRole('combobox', { name: 'Answer source' });
    expect((choice as HTMLSelectElement).value).toBe('textbook');
    await user.selectOptions(choice, 'general_knowledge');
    expect(api.send).not.toHaveBeenCalled();
    const input = screen.getByRole('textbox', { name: 'Message Learning Assistant' });
    await user.type(input, 'What is retrieval-augmented generation?');
    await user.keyboard('{Enter}');
    await screen.findByText('The provider rejected the credential.');
    expect(api.send).toHaveBeenCalledWith('session-one', 'What is retrieval-augmented generation?', true, expect.any(String), 'general_knowledge');
    expect((input as HTMLTextAreaElement).value).toBe('What is retrieval-augmented generation?');
    expect((choice as HTMLSelectElement).value).toBe('general_knowledge');
    expect(document.querySelector('[data-answer-id]')).toBeNull();
  });
  it('retains the selected mode with a rejected draft and changes the idempotency key only when the mode changes', async () => {
    vi.mocked(api.send).mockRejectedValue(new Error('Connection lost.'));
    const first = render(<Chat {...props} />);
    const input = screen.getByRole('textbox', { name: 'Message Learning Assistant' });
    const choice = screen.getByRole('combobox', { name: 'Answer source' });
    fireEvent.change(choice, { target: { value: 'general_knowledge' } });
    fireEvent.change(input, { target: { value: 'Explain the topic.' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    await screen.findByText('Connection lost.');
    const firstKey = vi.mocked(api.send).mock.calls[0][3];
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(api.send).toHaveBeenCalledTimes(2));
    await screen.findByText('Connection lost.');
    expect(vi.mocked(api.send).mock.calls[1][3]).toBe(firstKey);
    fireEvent.change(choice, { target: { value: 'textbook' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(api.send).toHaveBeenCalledTimes(3));
    await screen.findByText('Connection lost.');
    expect(vi.mocked(api.send).mock.calls[2][3]).not.toBe(firstKey);
    expect(vi.mocked(api.send).mock.calls[2][4]).toBe('textbook');
    fireEvent.change(choice, { target: { value: 'general_knowledge' } });
    first.unmount();
    render(<Chat {...props} />);
    expect((screen.getByRole('combobox', { name: 'Answer source' }) as HTMLSelectElement).value).toBe('general_knowledge');
    expect((screen.getByRole('textbox', { name: 'Message Learning Assistant' }) as HTMLTextAreaElement).value).toBe('Explain the topic.');
  });
  it('labels saved general knowledge independently of the current selection and offers no textbook source controls', async () => {
    const stored: Answer = { ...answer, answer_mode: 'general_knowledge', source_provenance: 'model_general_knowledge_unverified', response: { ...answer.response, answer_text: 'A saved explanation from model knowledge.' } };
    vi.mocked(api.messages).mockResolvedValue({ items: [{ id: 'message-two', session_id: 'session-one', sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: stored.id, answer: stored, request_id: stored.request_id, created_at: '' }], next_after_sequence: null, active_job_id: null, latest_job_id: null });
    vi.mocked(post).mockRejectedValue(new ApiError('PROVIDER_TIMEOUT', 'The provider timed out.', 504));
    render(<Chat {...props} />);
    await screen.findByText('A saved explanation from model knowledge.');
    expect((screen.getByRole('combobox', { name: 'Answer source' }) as HTMLSelectElement).value).toBe('textbook');
    expect(screen.getByText('Model knowledge · verify independently.')).toBeTruthy();
    expect(document.querySelector('.answer-metadata')?.textContent).toContain('General knowledge');
    expect(screen.queryByRole('button', { name: /^Sources|^Stored sources|^Open source/ })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Regenerate' }));
    await screen.findByText('The provider timed out.');
    expect(post).toHaveBeenCalledWith('/answers/answer-one/regenerate', {}, expect.any(String));
    expect(screen.getByText('A saved explanation from model knowledge.')).toBeTruthy();
    expect(api.send).not.toHaveBeenCalled();
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
