import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Chat } from './Chat';
import { api, ApiError, post } from './api';
import type { Answer, Job, MessagePage, Session } from './types';

vi.mock('./api', async importOriginal => {
  const original = await importOriginal<typeof import('./api')>();
  return { ...original, api: { ...original.api, session: vi.fn(), messages: vi.fn(), send: vi.fn(), job: vi.fn(), evidence: vi.fn(), feedback: vi.fn() }, post: vi.fn(), put: vi.fn() };
});

const session: Session = { id: 'session-one', title: 'My conversation', status: 'active', version: 1, created_at: '', updated_at: '' };
const props = {
  sessionId: session.id, userId: 'user-one', profile: null,
  capabilities: { model_mode: 'mock' as const, chat_ready: true, evaluation_ready: false, missing_reasons: { chat: [], evaluation: ['No evaluation data'] }, providers: [], feature_flags: {}, contract_versions: [] },
  onCreated: vi.fn(), refreshSessions: vi.fn(async () => {}), onOverlay: vi.fn(),
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function savedAnswer(id: string, text: string): Answer {
  return {
    answer_mode: 'textbook', source_provenance: 'textbook_evidence', id,
    request_id: `request-${id}`, job_id: 'job-one', message_id: `message-${id}`,
    mode: 'interactive_chat', response_schema: 'chat_response_v1', status: 'answered', model_mode: 'mock',
    response: { schema_version: 'chat_response_v1', response_type: 'answer', answer_text: `${text} [ev_001]`, short_answer: text, citations: ['ev_001'], refusal_reason: null, follow_up_questions: [], confidence: null },
    evidence: [{ evidence_id: 'ev_001', chunk_id: 'chunk-one', asset_id: 'asset-one', processing_id: 'processing-one', source_title: 'Original source', section: 'Section 1', pages: [4], locator: 'page 4', text: 'Original permitted passage', text_hash: 'original-hash', context_order: 0 }],
    profile_snapshot: null, conversation_snapshot: null, timing: {}, can_regenerate: true,
  };
}

const previousAnswer = savedAnswer('answer-previous', 'Previously saved response.');
const completedAnswer = savedAnswer('answer-current', 'Newly completed response.');
const runningJob: Job = { id: 'job-one', request_id: 'request-current', state: 'running', stage: 'generating', error: null, answer_id: null, can_retry: false, created_at: '', updated_at: '' };

function history(answer: Answer, activeJob: string | null = null, latestJob: string | null = null, sessionId = session.id): MessagePage {
  return {
    items: [{ id: answer.message_id!, session_id: sessionId, sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: answer.id, answer, request_id: answer.request_id, created_at: '' }],
    next_after_sequence: null, active_job_id: activeJob, latest_job_id: latestJob,
  };
}

beforeEach(() => {
  sessionStorage.clear();
  vi.resetAllMocks();
  props.refreshSessions.mockResolvedValue(undefined);
  vi.mocked(api.session).mockResolvedValue(session);
  vi.mocked(api.messages).mockResolvedValue(history(completedAnswer));
  vi.mocked(api.job).mockResolvedValue({ ...runningJob, id: 'obsolete-job' });
  vi.mocked(post).mockResolvedValue({ ...runningJob, state: 'cancelled' });
});

afterEach(cleanup);

// The Stop request and the already pending status poll both reload this same
// conversation. Deferred transport responses control their order through the UI.
async function startOverlappingHistoryLoads() {
  const oldHistory = deferred<MessagePage>();
  const pendingPoll = deferred<Job>();
  vi.mocked(api.messages)
    .mockResolvedValueOnce(history(previousAnswer, runningJob.id))
    .mockReturnValueOnce(oldHistory.promise)
    .mockResolvedValueOnce(history(completedAnswer));
  vi.mocked(api.job).mockReturnValueOnce(pendingPoll.promise);
  const view = render(<Chat {...props} />);
  const stopButton = await screen.findByRole('button', { name: 'Stop generation' });
  await waitFor(() => expect(api.job).toHaveBeenCalledWith(runningJob.id));
  fireEvent.click(stopButton);
  await waitFor(() => expect(api.messages).toHaveBeenCalledTimes(2));
  expect(post).toHaveBeenCalledWith('/jobs/job-one/cancel');
  return { oldHistory, pendingPoll, view };
}

async function completeNewerHistory(pendingPoll: ReturnType<typeof deferred<Job>>) {
  await act(async () => {
    pendingPoll.resolve({ ...runningJob, state: 'succeeded', stage: 'completed', answer_id: completedAnswer.id });
    await pendingPoll.promise;
  });
  await screen.findByText('Newly completed response.', { exact: false });
  await waitFor(() => expect(props.refreshSessions).toHaveBeenCalledTimes(1));
  expect(api.messages).toHaveBeenCalledTimes(3);
  expect(screen.queryByRole('button', { name: 'Stop generation' })).toBeNull();
}

describe('same-conversation transcript request races', () => {
  it('keeps the completed answer and does not revive an old job when an earlier Stop snapshot arrives last', async () => {
    const { oldHistory, pendingPoll } = await startOverlappingHistoryLoads();
    await completeNewerHistory(pendingPoll);

    await act(async () => {
      oldHistory.resolve(history(previousAnswer, 'obsolete-job'));
      await oldHistory.promise;
    });

    expect.soft(screen.queryByText('Newly completed response.', { exact: false })).not.toBeNull();
    expect.soft(screen.queryByText('Previously saved response.', { exact: false })).toBeNull();
    expect.soft(screen.queryByRole('button', { name: 'Stop generation' })).toBeNull();
    expect.soft(vi.mocked(api.job).mock.calls.some(([id]) => id === 'obsolete-job')).toBe(false);
  });

  it('ignores an older history rejection after the newer completion has loaded successfully', async () => {
    const { oldHistory, pendingPoll } = await startOverlappingHistoryLoads();
    await completeNewerHistory(pendingPoll);

    await act(async () => {
      oldHistory.reject(new ApiError('CONNECTION_ERROR', 'Obsolete transcript request failed.'));
      await oldHistory.promise.catch(() => undefined);
    });

    expect(screen.queryByText('Obsolete transcript request failed.')).toBeNull();
    expect(screen.getByText('Newly completed response.', { exact: false })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Stop generation' })).toBeNull();
  });

  it('ignores late history after unmount without fetching its obsolete job or disturbing the next conversation', async () => {
    const { oldHistory, view } = await startOverlappingHistoryLoads();
    view.unmount();
    const nextAnswer = savedAnswer('answer-next-session', 'Next conversation response.');
    vi.mocked(api.session).mockResolvedValue({ ...session, id: 'session-two', title: 'Next conversation' });
    vi.mocked(api.messages).mockReset().mockResolvedValue(history(nextAnswer, null, null, 'session-two'));
    render(<Chat {...props} sessionId="session-two" />);
    await screen.findByText('Next conversation response.', { exact: false });

    await act(async () => {
      oldHistory.resolve(history(previousAnswer, null, 'obsolete-job'));
      await oldHistory.promise;
    });

    expect(vi.mocked(api.job).mock.calls.some(([id]) => id === 'obsolete-job')).toBe(false);
    expect(screen.getByText('Next conversation response.', { exact: false })).toBeTruthy();
    expect(screen.queryByText('Previously saved response.', { exact: false })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Stop generation' })).toBeNull();
    expect(props.refreshSessions).not.toHaveBeenCalled();
  });
});
