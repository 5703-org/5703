import { afterEach, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import { Chat } from './Chat';
import type { components } from './generated/api';
import type { Answer, ChatResponse, Job, MessagePage, Session } from './types';

const session: Session = {
  id: 'repair-session', title: 'Repair contract fixture', status: 'active',
  version: 1, created_at: '', updated_at: '',
};
const props = {
  sessionId: session.id, userId: 'repair-fixture-user', profile: null,
  capabilities: null, onCreated: vi.fn(), refreshSessions: vi.fn(async () => {}),
  onOverlay: vi.fn(),
};
const protectedEquation = 'The equation is 5x - 4 = 21.';
const revisedQuestion = 'Which operation would isolate the variable term, what part of the equation would it affect, and why would you do that first?';

// These are public DTO fixtures, not model quality judgments or checker results.
const previousAnswer: Answer = {
  id: 'previous-answer', request_id: 'previous-request', job_id: 'previous-job',
  message_id: 'repair-message', answer_mode: 'textbook',
  source_provenance: 'textbook_evidence', mode: 'interactive_chat',
  response_schema: 'chat_response_v1', status: 'answered', model_mode: 'mock',
  response: {
    schema_version: 'chat_response_v1', response_type: 'answer',
    answer_text: 'Previously published explanation.', short_answer: null,
    citations: [], refusal_reason: null, follow_up_questions: [], confidence: null,
  },
  evidence: [], profile_snapshot: null, conversation_snapshot: null,
  timing: {}, can_regenerate: false,
};
const composedAnswer: Answer = {
  ...previousAnswer, id: 'composed-answer', request_id: 'repair-request',
  job_id: 'repair-job', teaching_mode: 'hint', task_id: 'repair-task', help_level: 1,
  response: {
    schema_version: 'chat_response_v1', response_type: 'answer',
    answer_text: `${protectedEquation}\n\n${revisedQuestion}`, short_answer: null,
    citations: [], refusal_reason: null, follow_up_questions: [], confidence: null,
  },
  learning_task: {
    id: 'repair-task', session_id: session.id, question: 'Choose the next step.',
    task_type: 'mathematical_selection', teaching_mode: 'hint', help_level: 1,
    state: 'active', version: 4, pending_tutor_question_id: 'revised-question',
    pending_tutor_question: revisedQuestion, pending_tutor_question_version: 3,
    expected_response_kind: 'explanation', current_step: 1,
    turn_role: 'user_question', last_attempt_evaluation: null,
  },
};

function history(answer: Answer, activeJob: string | null = null): MessagePage {
  if (answer.message_id === null) throw new Error('Fixture history requires a persisted message id.');
  return {
    items: [{
      id: answer.message_id, session_id: session.id, sequence: 2,
      role: 'assistant', content: '', state: 'answered',
      active_answer_id: answer.id, answer, request_id: answer.request_id, created_at: '',
    }],
    next_after_sequence: null, active_job_id: activeJob, latest_job_id: null,
  };
}
function envelope(data: unknown): Response {
  return new Response(JSON.stringify({ data, meta: { trace_id: 'repair-fixture' } }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => { sessionStorage.clear(); vi.clearAllMocks(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('internal repair and public chat response boundary', () => {
  it('keeps structured repair instructions outside generated learner DTOs', () => {
    type InternalField = 'claim_patch' | 'repair_plan' | 'repair_targets' | 'edits' | 'base_draft_hash';
    expectTypeOf<Extract<keyof ChatResponse, InternalField>>().toEqualTypeOf<never>();
    expectTypeOf<Extract<keyof components['schemas']['AnswerOut'], InternalField>>().toEqualTypeOf<never>();
    expectTypeOf<Extract<keyof components['schemas'], 'ClaimPatch' | 'RepairTarget' | 'BoundRepairPlan'>>().toEqualTypeOf<never>();
    expectTypeOf<components['schemas']['AnswerOut']['response']>().toEqualTypeOf<
      ChatResponse | components['schemas']['MCQResponseV1']
    >();
  });

  it('retains the published answer during recheck and loads the composed response with its synchronized tutor question', async () => {
    let published = false;
    let jobRequests = 0;
    let finishRecheck!: (job: Job) => void;
    const finishedJob = new Promise<Job>(resolve => { finishRecheck = resolve; });
    const running: Job = {
      id: 'repair-job', request_id: 'repair-request', state: 'running',
      stage: 'joint_recheck', error: null, answer_id: null, can_retry: false,
      created_at: '', updated_at: '',
    };
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const route = String(input);
      if (route === `/api/v1/sessions/${session.id}`) return envelope(session);
      if (route === `/api/v1/sessions/${session.id}/messages?after_sequence=0&limit=100`) {
        return envelope(published ? history(composedAnswer) : history(previousAnswer, running.id));
      }
      if (route === '/api/v1/jobs/repair-job') {
        jobRequests += 1;
        return envelope(jobRequests === 1 ? running : await finishedJob);
      }
      throw new Error(`Unexpected fixture transport: ${route}`);
    });
    vi.stubGlobal('fetch', fetcher);
    render(<Chat {...props} />);

    await screen.findByText('Checking the revised explanation…');
    expect(screen.getByText('Previously published explanation.')).toBeTruthy();
    expect(screen.queryByText(protectedEquation)).toBeNull();
    expect(screen.queryByRole('region', { name: 'Current tutor question' })).toBeNull();
    await waitFor(() => expect(jobRequests).toBe(2), { timeout: 2000 });

    await act(async () => {
      published = true;
      finishRecheck({ ...running, state: 'succeeded', stage: 'completed', answer_id: composedAnswer.id });
    });
    await screen.findByText(protectedEquation);
    expect(screen.queryByText('Previously published explanation.')).toBeNull();
    expect(screen.getByRole('region', { name: 'Current tutor question' }).textContent).toContain(revisedQuestion);
    expect(document.querySelector('.prose')?.textContent).toContain(revisedQuestion);
    expect(screen.queryByText('Checking the revised explanation…')).toBeNull();
    expect((screen.getByRole('combobox', { name: 'Teaching style' }) as HTMLSelectElement).value).toBe('hint');
    expect(fetcher.mock.calls.every(([route]) => !String(route).includes('patch'))).toBe(true);
  });

  it('uses the final S11 citation list rather than restoring uncited submitted evidence', async () => {
    const s11: Answer = {
      ...previousAnswer, id: 's11-answer', teaching_mode: 'hint', help_level: 1,
      response: {
        schema_version: 'chat_response_v1', response_type: 'answer',
        answer_text: 'Consider the given conditions that the amount of gas is fixed and the temperature remains constant, together with the initial and final volumes of this gas sample. Would the supplied candidate fit those conditions, what in those givens supports your judgment, and why should you establish that fit before deciding whether later use of it would be justified?',
        short_answer: null, citations: [], refusal_reason: null,
        follow_up_questions: [], confidence: 0.5,
      },
      evidence: [{
        evidence_id: 'ev_001', chunk_id: 'fictional-chunk', asset_id: 'fictional-asset',
        processing_id: 'fictional-processing', source_title: 'Fictional software fixture',
        section: 'Fixture section', pages: [1], locator: 'fixture page 1',
        text: 'Submitted context is not automatically a released citation.',
        text_hash: 'fixture-hash', context_order: 0,
      }],
    };
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const route = String(input);
      if (route === `/api/v1/sessions/${session.id}`) return envelope(session);
      if (route === `/api/v1/sessions/${session.id}/messages?after_sequence=0&limit=100`) return envelope(history(s11));
      throw new Error(`Unexpected fixture transport: ${route}`);
    });
    vi.stubGlobal('fetch', fetcher);
    render(<Chat {...props} />);

    await screen.findByText(s11.response.answer_text as string);
    expect(screen.queryByRole('button', { name: /^Sources/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /^Stored sources/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /^Open source/ })).toBeNull();
    expect(document.querySelector('.prose')?.textContent).not.toContain(s11.evidence[0].text);
    expect(fetcher.mock.calls.map(([route]) => String(route))).toEqual([
      `/api/v1/sessions/${session.id}`,
      `/api/v1/sessions/${session.id}/messages?after_sequence=0&limit=100`,
    ]);
  });
});
