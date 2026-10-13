import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Chat } from './Chat';
import type { Answer, Job, MessagePage, Session } from './types';

const session: Session = {
  id: 'checker-session', title: 'Checker correction control', status: 'active',
  version: 1, created_at: '', updated_at: '',
};
const props = {
  sessionId: session.id, userId: 'checker-fixture-user', profile: null,
  capabilities: null, onCreated: vi.fn(), refreshSessions: vi.fn(async () => {}),
  onOverlay: vi.fn(),
};
const previousAnswer: Answer = {
  id: 'previous-answer', request_id: 'previous-request', job_id: 'previous-job',
  message_id: 'previous-message', answer_mode: 'textbook',
  source_provenance: 'textbook_evidence', mode: 'interactive_chat',
  response_schema: 'chat_response_v1', status: 'answered', model_mode: 'mock',
  response: {
    schema_version: 'chat_response_v1', response_type: 'answer',
    answer_text: 'Previously published explanation.', short_answer: null,
    citations: [], refusal_reason: null, follow_up_questions: [], confidence: null,
  },
  evidence: [], profile_snapshot: null, conversation_snapshot: null,
  timing: {}, can_regenerate: true,
};
const running: Job = {
  id: 'correction-job', request_id: 'correction-request', state: 'running',
  stage: 'checker_contract_repair', error: null, answer_id: null, can_retry: false,
  created_at: '', updated_at: '',
};
const failed: Job = {
  ...running, state: 'failed', stage: 'failed', can_retry: true,
  error: {
    code: 'CHECKER_INCONSISTENT',
    message: 'The checker returned inconsistent support metadata; no answer was published',
    details: { issue_codes: ['RELATION_ASSESSED_FRAGMENT_MISMATCH'] },
  },
};

function history(terminal: boolean): MessagePage {
  return {
    items: [{
      id: 'previous-message', session_id: session.id, sequence: 2,
      role: 'assistant', content: '', state: 'answered', active_answer_id: previousAnswer.id,
      answer: previousAnswer, request_id: previousAnswer.request_id, created_at: '',
    }],
    next_after_sequence: null,
    active_job_id: terminal ? null : running.id,
    latest_job_id: terminal ? failed.id : null,
  };
}

function envelope(data: unknown): Response {
  return new Response(JSON.stringify({ data, meta: { trace_id: 'checker-control' } }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => { sessionStorage.clear(); vi.clearAllMocks(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('checker correction terminal state', () => {
  it('retains the published answer and edited draft without automatically retrying a failed source check', async () => {
    let terminal = false;
    let jobRequests = 0;
    let finishCorrection!: (job: Job) => void;
    const finished = new Promise<Job>(resolve => { finishCorrection = resolve; });
    const pendingKey = `cs30.pending.${props.userId}.${session.id}`;
    sessionStorage.setItem(pendingKey, 'The previous submitted question.');
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const route = String(input);
      if ((init?.method || 'GET') !== 'GET') throw new Error('This control must not submit or retry work.');
      if (route === `/api/v1/sessions/${session.id}`) return envelope(session);
      if (route === `/api/v1/sessions/${session.id}/messages?after_sequence=0&limit=100`) return envelope(history(terminal));
      if (route === `/api/v1/jobs/${running.id}`) {
        jobRequests += 1;
        return envelope(terminal ? failed : jobRequests === 1 ? running : await finished);
      }
      throw new Error(`Unexpected fixture transport: ${route}`);
    });
    vi.stubGlobal('fetch', fetcher);
    render(<Chat {...props} />);

    await screen.findByText('Restoring the source check…');
    expect(screen.getByText(previousAnswer.response.answer_text as string)).toBeTruthy();
    expect(document.querySelector('.generation-status')?.getAttribute('data-progress-state')).toBe('running');
    const composer = screen.getByRole('textbox', { name: 'Message Learning Assistant' });
    fireEvent.change(composer, { target: { value: 'A new unsent draft typed while checking.' } });
    await waitFor(() => expect(jobRequests).toBe(2), { timeout: 2000 });

    await act(async () => { terminal = true; finishCorrection(failed); });
    await screen.findByText('The response could not be completed.');
    expect(screen.getByText(failed.error!.message)).toBeTruthy();
    expect(screen.getByText('CHECKER_INCONSISTENT')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Retry response' })).toBeTruthy();
    expect(screen.getByText(previousAnswer.response.answer_text as string)).toBeTruthy();
    expect(document.querySelector('[data-answer-id]')?.getAttribute('data-answer-id')).toBe(previousAnswer.id);
    expect((composer as HTMLTextAreaElement).value).toBe('A new unsent draft typed while checking.');
    expect(sessionStorage.getItem(`cs30.draft.${props.userId}.${session.id}`)).toBe('A new unsent draft typed while checking.');
    expect(sessionStorage.getItem(pendingKey)).toBeNull();
    expect(screen.queryByText('Restoring the source check…')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Stop generation' })).toBeNull();
    expect(document.querySelectorAll('[data-answer-id]')).toHaveLength(1);
    expect(fetcher.mock.calls.every(([, init]) => (init?.method || 'GET') === 'GET')).toBe(true);
    await waitFor(() => expect(props.refreshSessions).toHaveBeenCalledTimes(1));
  });
});

