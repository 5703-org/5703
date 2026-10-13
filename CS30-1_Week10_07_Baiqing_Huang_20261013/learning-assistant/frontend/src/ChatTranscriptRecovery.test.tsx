import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Chat } from './Chat';
import { api, ApiError, post } from './api';
import type { Answer, Job, MessagePage, Session } from './types';

// Product transports are mocked throughout. No real network or model request runs.
vi.mock('./api', async importOriginal => {
  const original = await importOriginal<typeof import('./api')>();
  return { ...original, api: { ...original.api, session: vi.fn(), messages: vi.fn(), send: vi.fn(), job: vi.fn(), evidence: vi.fn(), feedback: vi.fn() }, post: vi.fn(), put: vi.fn() };
});

const session: Session = { id: 'session-one', title: 'Saved conversation', status: 'active', version: 1, created_at: '', updated_at: '' };
const props = {
  sessionId: session.id, userId: 'user-one', profile: null,
  capabilities: { model_mode: 'mock' as const, chat_ready: true, evaluation_ready: false, missing_reasons: { chat: [], evaluation: ['No evaluation data'] }, providers: [], feature_flags: {}, contract_versions: [] },
  onCreated: vi.fn(), refreshSessions: vi.fn(async () => {}), onOverlay: vi.fn(),
};
const draftKey = 'cs30.draft.user-one.session-one';

function savedAnswer(id: string, text: string): Answer {
  return {
    answer_mode: 'textbook', source_provenance: 'textbook_evidence', id,
    request_id: `request-${id}`, job_id: 'job-one', message_id: `message-${id}`,
    mode: 'interactive_chat', response_schema: 'chat_response_v1', status: 'answered', model_mode: 'mock',
    response: { schema_version: 'chat_response_v1', response_type: 'answer', answer_text: `${text} [ev_001]`, short_answer: text, citations: ['ev_001'], refusal_reason: null, follow_up_questions: [], confidence: null },
    evidence: [{ evidence_id: 'ev_001', chunk_id: 'chunk-one', asset_id: 'asset-one', processing_id: 'processing-one', source_title: 'Authored source', section: 'Section 1', pages: [4], locator: 'page 4', text: 'Authored permitted passage.', text_hash: 'authored-hash', context_order: 0 }],
    profile_snapshot: null, conversation_snapshot: null, timing: {}, can_regenerate: true,
  };
}

const previousAnswer = savedAnswer('answer-previous', 'Previously saved response.');
const completedAnswer = savedAnswer('answer-current', 'Completed response is now available.');
const hintAnswer: Answer = {
  ...savedAnswer('answer-hint', 'Consider which process involves water.'),
  teaching_mode: 'hint', task_id: 'task-one', help_level: 1,
  learning_task: {
    id: 'task-one', session_id: session.id, question: 'Compare diffusion and osmosis.',
    task_type: 'concept_comparison', teaching_mode: 'hint', help_level: 1, state: 'active', version: 3,
    pending_tutor_question_id: 'question-current', pending_tutor_question: 'Which process specifically involves water?',
    pending_tutor_question_version: 2, expected_response_kind: 'concept', current_step: 1,
    turn_role: 'user_question', last_attempt_evaluation: null,
  },
};
const completedJob: Job = {
  id: 'job-one', request_id: 'request-current', state: 'succeeded', stage: 'completed',
  error: null, answer_id: completedAnswer.id, can_retry: false, created_at: '', updated_at: '',
};

function history(answer: Answer, activeJob: string | null = null): MessagePage {
  return {
    items: [{ id: answer.message_id!, session_id: session.id, sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: answer.id, answer, request_id: answer.request_id, created_at: '' }],
    next_after_sequence: null, active_job_id: activeJob, latest_job_id: null,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function expectNoSubmission() {
  expect(api.send).not.toHaveBeenCalled();
  expect(post).not.toHaveBeenCalled();
  expect(props.onCreated).not.toHaveBeenCalled();
}

beforeEach(() => {
  sessionStorage.clear();
  vi.resetAllMocks();
  props.refreshSessions.mockResolvedValue(undefined);
  vi.mocked(api.session).mockResolvedValue(session);
  vi.mocked(api.messages).mockResolvedValue(history(previousAnswer));
  vi.mocked(api.job).mockResolvedValue(completedJob);
});

afterEach(cleanup);

describe('conversation transcript recovery', () => {
  it('retains session error priority after an early history rejection and recovers without submitting work', async () => {
    const lookup = deferred<Session>();
    const firstHistory = deferred<MessagePage>();
    vi.mocked(api.session).mockReturnValueOnce(lookup.promise);
    vi.mocked(api.messages).mockReturnValueOnce(firstHistory.promise);
    render(<Chat {...props} />);
    await waitFor(() => {
      expect(api.session).toHaveBeenCalledWith(session.id);
      expect(api.messages).toHaveBeenCalledWith(session.id, 0);
    });
    // Do not catch this in the test: production must handle the early rejection.
    await act(async () => {
      firstHistory.reject(new ApiError('CONNECTION_ERROR', 'Early history lookup interrupted.'));
    });
    expect(screen.queryByText('Early history lookup interrupted.')).toBeNull();
    expect(screen.queryByText('Previously saved response.', { exact: false })).toBeNull();
    await act(async () => {
      lookup.reject(new ApiError('CONNECTION_ERROR', 'Saved conversation lookup interrupted.'));
    });

    await screen.findByText('Saved conversation lookup interrupted.');
    const reload = await screen.findByRole('button', { name: 'Reload conversation' });
    expect(vi.mocked(api.messages).mock.calls).toEqual([[session.id, 0]]);
    expect(screen.queryByText('Early history lookup interrupted.')).toBeNull();
    expect(screen.queryByText('Previously saved response.', { exact: false })).toBeNull();
    expectNoSubmission();

    fireEvent.click(reload);
    await screen.findByText('Previously saved response.', { exact: false });
    expect(vi.mocked(api.session).mock.calls).toEqual([[session.id], [session.id]]);
    expect(vi.mocked(api.messages).mock.calls).toEqual([[session.id, 0], [session.id, 0]]);
    expect(screen.queryByText('Saved conversation lookup interrupted.')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Reload conversation' })).toBeNull();
    expectNoSubmission();
  });

  it('retries an initial history failure and retains the saved composer draft', async () => {
    sessionStorage.setItem(draftKey, 'My unsent explanation.');
    vi.mocked(api.messages).mockRejectedValueOnce(new ApiError('CONNECTION_ERROR', 'Saved history interrupted.'));
    render(<Chat {...props} />);

    await screen.findByText('Saved history interrupted.');
    const input = screen.getByRole('textbox', { name: 'Message Learning Assistant' }) as HTMLTextAreaElement;
    expect(input.value).toBe('My unsent explanation.');
    fireEvent.click(await screen.findByRole('button', { name: 'Reload conversation' }));

    await screen.findByText('Previously saved response.', { exact: false });
    expect(input.value).toBe('My unsent explanation.');
    expect(sessionStorage.getItem(draftKey)).toBe('My unsent explanation.');
    expect(vi.mocked(api.messages).mock.calls).toEqual([[session.id, 0], [session.id, 0]]);
    expectNoSubmission();
  });

  it('keeps transcript recovery while the draft changes and binds only an explicitly submitted learner reply to the recovered task', async () => {
    vi.mocked(api.messages)
      .mockRejectedValueOnce(new ApiError('CONNECTION_ERROR', 'Tutor history interrupted.'))
      .mockResolvedValue(history(hintAnswer));
    sessionStorage.setItem(`${draftKey}.teaching`, JSON.stringify({ task_id: 'task-one', task_version: 1, pending_tutor_question_id: 'question-old', pending_tutor_question_version: 1 }));
    // This independent explicit submit is a mocked transport receipt, never a model call.
    vi.mocked(api.send).mockRejectedValue(new ApiError('CONFLICT', 'Authored submission stopped after binding inspection.', 409));
    render(<Chat {...props} />);

    await screen.findByText('Tutor history interrupted.');
    const input = screen.getByRole('textbox', { name: 'Message Learning Assistant' }) as HTMLTextAreaElement;
    fireEvent.change(input, { target: { value: 'Osmosis.' } });
    expectNoSubmission();
    fireEvent.click(await screen.findByRole('button', { name: 'Reload conversation' }));

    await screen.findByText('Which process specifically involves water?');
    expect(input.value).toBe('Osmosis.');
    expect((screen.getByRole('combobox', { name: 'Teaching style' }) as HTMLSelectElement).value).toBe('hint');
    expectNoSubmission();

    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await screen.findByText('Authored submission stopped after binding inspection.');
    expect(api.send).toHaveBeenCalledTimes(1);
    expect(api.send).toHaveBeenCalledWith(session.id, 'Osmosis.', true, expect.any(String), 'textbook', {
      task_id: 'task-one', task_version: 3,
      pending_tutor_question_id: 'question-current', pending_tutor_question_version: 2,
    });
    expect(post).not.toHaveBeenCalled();
    expect(props.onCreated).not.toHaveBeenCalled();
    expect(input.value).toBe('Osmosis.');
  });

  it('keeps a failed retry recoverable and prevents another reload while the current retry is pending', async () => {
    const retry = deferred<MessagePage>();
    vi.mocked(api.messages)
      .mockRejectedValueOnce(new ApiError('CONNECTION_ERROR', 'Initial history interrupted.'))
      .mockReturnValueOnce(retry.promise)
      .mockResolvedValue(history(previousAnswer));
    render(<Chat {...props} />);

    await screen.findByText('Initial history interrupted.');
    fireEvent.click(await screen.findByRole('button', { name: 'Reload conversation' }));
    await waitFor(() => expect(api.messages).toHaveBeenCalledTimes(2));
    const waitingButton = screen.getByRole('button', { name: 'Reload conversation' }) as HTMLButtonElement;
    expect(waitingButton.disabled).toBe(true);
    fireEvent.click(waitingButton);
    expect(api.messages).toHaveBeenCalledTimes(2);
    expectNoSubmission();

    await act(async () => {
      retry.reject(new ApiError('CONNECTION_ERROR', 'Retry history interrupted.'));
      await retry.promise.catch(() => undefined);
    });
    await screen.findByText('Retry history interrupted.');
    await waitFor(() => expect((screen.getByRole('button', { name: 'Reload conversation' }) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole('button', { name: 'Reload conversation' }));
    await screen.findByText('Previously saved response.', { exact: false });
    expect(api.messages).toHaveBeenCalledTimes(3);
    expectNoSubmission();
  });

  it('recovers a completed job history refresh without losing the prior answer or unsent draft', async () => {
    sessionStorage.setItem(draftKey, 'Unsent follow-up reasoning.');
    vi.mocked(api.messages)
      .mockResolvedValueOnce(history(previousAnswer, completedJob.id))
      .mockRejectedValueOnce(new ApiError('CONNECTION_ERROR', 'Completed history refresh interrupted.'))
      .mockResolvedValue(history(completedAnswer));
    render(<Chat {...props} />);

    await screen.findAllByText('Completed history refresh interrupted.');
    expect(screen.getByText('Previously saved response.', { exact: false })).toBeTruthy();
    const input = screen.getByRole('textbox', { name: 'Message Learning Assistant' }) as HTMLTextAreaElement;
    expect(input.value).toBe('Unsent follow-up reasoning.');
    expectNoSubmission();
    fireEvent.click(await screen.findByRole('button', { name: 'Reload conversation' }));

    await screen.findByText('Completed response is now available.', { exact: false });
    expect(screen.queryByText('Previously saved response.', { exact: false })).toBeNull();
    expect(input.value).toBe('Unsent follow-up reasoning.');
    expect(sessionStorage.getItem(draftKey)).toBe('Unsent follow-up reasoning.');
    expect(api.job).toHaveBeenCalledWith(completedJob.id);
    expect(vi.mocked(api.messages).mock.calls.every(([id]) => id === session.id)).toBe(true);
    expectNoSubmission();
  });

  it('retains an independent submission failure when the pending transcript reload later succeeds', async () => {
    const retry = deferred<MessagePage>();
    vi.mocked(api.messages)
      .mockRejectedValueOnce(new ApiError('CONNECTION_ERROR', 'Earlier history load interrupted.'))
      .mockReturnValueOnce(retry.promise);
    // This explicit user action has only an authored mocked rejection receipt.
    vi.mocked(api.send).mockRejectedValue(new ApiError('CONFLICT', 'Independent submission rejected.', 409));
    render(<Chat {...props} />);

    await screen.findByText('Earlier history load interrupted.');
    fireEvent.click(await screen.findByRole('button', { name: 'Reload conversation' }));
    await waitFor(() => expect(api.messages).toHaveBeenCalledTimes(2));
    expectNoSubmission();

    const input = screen.getByRole('textbox', { name: 'Message Learning Assistant' }) as HTMLTextAreaElement;
    fireEvent.change(input, { target: { value: 'My independent question.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await screen.findByText('Independent submission rejected.');
    expect(api.send).toHaveBeenCalledTimes(1);
    expect(post).not.toHaveBeenCalled();
    expect(props.onCreated).not.toHaveBeenCalled();

    await act(async () => {
      retry.resolve(history(previousAnswer));
      await retry.promise;
    });
    await screen.findByText('Previously saved response.', { exact: false });
    expect(screen.getByText('Independent submission rejected.')).toBeTruthy();
    expect(screen.queryByText('Earlier history load interrupted.')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Reload conversation' })).toBeNull();
    expect(input.value).toBe('My independent question.');
    expect(vi.mocked(api.messages).mock.calls).toEqual([[session.id, 0], [session.id, 0]]);
    expect(api.send).toHaveBeenCalledTimes(1);
    expect(post).not.toHaveBeenCalled();
    expect(props.onCreated).not.toHaveBeenCalled();
  });
});
