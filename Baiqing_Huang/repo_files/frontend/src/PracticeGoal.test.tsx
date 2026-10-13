import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { api, ApiError, post, request } from './api';
import { Chat } from './Chat';
import { PracticeList, PracticeWorkspace } from './StudyPractice';
import { practicePath } from './practice-navigation';
import type { Answer, Capabilities, Session } from './types';
import type { PracticeItem, PracticeProgress } from './study-types';

vi.mock('./api', async original => ({
  ...await original<typeof import('./api')>(),
  api: { session: vi.fn(), messages: vi.fn(), send: vi.fn(), job: vi.fn(), evidence: vi.fn(), feedback: vi.fn() },
  request: vi.fn(), post: vi.fn(), put: vi.fn(),
}));

const source = { release_id: 'release', document_id: 'book', processing_id: 'processing', source_unit_id: 'unit', text_hash: 'source-sha', start: 0, end: null };
const item: PracticeItem = { id: 'item/with ? space', title: 'Isolated continuity fixture', kind: 'short', prompt: 'Explain the named condition.', options: [], concepts: ['fixture'], conditions: [], source, item_revision: 1, validation: { status: 'passed' } };
const progress: PracticeProgress = { item_id: item.id, version: 4, current_step: 1, current_step_prompt: null, total_steps: 1, help_level: 0, state: 'awaiting_attempt', attempts: [], hints: [], full_explanation: null };
const goalId = 'goal/with ? space';
const session: Session = { id: 'tutor-session', title: 'Owned tutor', status: 'active', version: 1, created_at: '', updated_at: '' };
const capabilities: Capabilities = { model_mode: 'mock', chat_ready: true, evaluation_ready: false, missing_reasons: { chat: [], evaluation: [] }, providers: [], feature_flags: {}, contract_versions: [] };
const answer: Answer = {
  id: 'answer', request_id: 'request', job_id: 'job', message_id: 'message', mode: 'interactive_chat',
  response_schema: 'chat_response_v1', status: 'answered', model_mode: 'mock', answer_mode: 'textbook', source_provenance: 'textbook_evidence',
  response: { schema_version: 'chat_response_v1', response_type: 'answer', answer_text: 'A local software fixture.', short_answer: 'Fixture', citations: [], refusal_reason: null, follow_up_questions: [], confidence: null },
  evidence: [], profile_snapshot: null, conversation_snapshot: null, timing: {}, can_regenerate: false,
  learning_task: { id: 'task', session_id: session.id, question: item.prompt, task_type: 'concept', teaching_mode: 'hint', help_level: 0, state: 'active', version: 3, pending_tutor_question_id: 'pending', pending_tutor_question: 'Name the condition.', pending_tutor_question_version: 1, expected_response_kind: 'explanation', current_step: 1, turn_role: 'user_question', last_attempt_evaluation: null, practice_item_id: item.id, practice_goal_id: goalId, practice_progress_version: 4 },
};

beforeEach(() => {
  vi.resetAllMocks(); sessionStorage.clear();
  vi.mocked(request).mockImplementation(async path => path.endsWith('/progress') ? progress : item);
});
afterEach(cleanup);

describe('owned practice goal continuity', () => {
  it.each([
    [item.id, goalId, '/learn/practice/item%2Fwith%20%3F%20space/goal/goal%2Fwith%20%3F%20space'],
    ['unit🧬', 'goal#one', '/learn/practice/unit%F0%9F%A7%AC/goal/goal%23one'],
    ['one', null, '/learn/practice/one'],
    ['one', undefined, '/learn/practice/one'],
  ])('encodes item %s and optional goal %s as separate route segments', (itemId, goal, expected) => {
    expect(practicePath(itemId!, goal)).toBe(expected);
  });

  it('opens goal-filtered practice with the selected goal in the route', async () => {
    vi.mocked(request).mockResolvedValue([item]); const go = vi.fn();
    render(<PracticeList goalId={goalId} unitId="owned-unit" go={go} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Start practice' }));
    expect(go).toHaveBeenCalledExactlyOnceWith(practicePath(item.id, goalId));
    expect(vi.mocked(request).mock.calls[0][0]).toBe('/learning/practice?goal_id=goal%2Fwith+%3F+space&unit_id=owned-unit');
  });

  it('sends the selected goal and records only the returned owned tutor task', async () => {
    const go = vi.fn(); vi.mocked(post).mockResolvedValue({ session_id: session.id, task_id: 'task', task_version: 3, practice_progress_version: 4, teaching_mode: 'hint', source, goal_id: goalId });
    render(<PracticeWorkspace itemId={item.id} userId="owner" goalId={goalId} go={go} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Continue with the tutor' }));
    await waitFor(() => expect(go).toHaveBeenCalledWith('/chat/tutor-session'));
    expect(post).toHaveBeenCalledExactlyOnceWith('/learning/practice/item%2Fwith%20%3F%20space/tutor', { expected_version: 4, goal_id: goalId });
    expect(JSON.parse(sessionStorage.getItem('cs30.draft.owner.tutor-session.teaching')!)).toEqual({ teaching_mode: 'hint', task_action: 'continue', task_id: 'task', task_version: 3 });
  });

  it.each([undefined, 'foreign-goal'])('retains practice when the saved tutor goal is %s', async returnedGoal => {
    const go = vi.fn(); vi.mocked(post).mockResolvedValue({ session_id: session.id, task_id: 'task', task_version: 3, practice_progress_version: 4, teaching_mode: 'hint', source, goal_id: returnedGoal });
    render(<PracticeWorkspace itemId={item.id} userId="owner" goalId={goalId} go={go} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Continue with the tutor' }));
    await screen.findByText('The tutor did not retain the selected learning goal. Reload saved practice and try again.');
    expect(go).not.toHaveBeenCalled(); expect(sessionStorage.getItem('cs30.draft.owner.tutor-session.teaching')).toBeNull();
  });

  it('keeps the plain practice request compatible with a legacy goal-free response', async () => {
    const go = vi.fn(); vi.mocked(post).mockResolvedValue({ session_id: session.id, task_id: 'task', task_version: 3, practice_progress_version: 4, teaching_mode: 'hint', source });
    render(<PracticeWorkspace itemId={item.id} userId="owner" go={go} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Continue with the tutor' }));
    await waitFor(() => expect(go).toHaveBeenCalledWith('/chat/tutor-session'));
    expect(post).toHaveBeenCalledExactlyOnceWith('/learning/practice/item%2Fwith%20%3F%20space/tutor', { expected_version: 4 });
  });

  it('returns from an actual saved chat task to the encoded goal-scoped practice route', async () => {
    vi.mocked(api.session).mockResolvedValue(session);
    vi.mocked(api.messages).mockResolvedValue({ items: [{ id: 'message', session_id: session.id, sequence: 2, role: 'assistant', content: '', state: 'answered', active_answer_id: answer.id, answer, request_id: answer.request_id, created_at: '' }], next_after_sequence: null, active_job_id: null, latest_job_id: null });
    render(<Chat sessionId={session.id} userId="owner" profile={null} capabilities={capabilities} onCreated={vi.fn()} refreshSessions={vi.fn(async () => {})} onOverlay={vi.fn()} />);
    expect((await screen.findByRole('link', { name: 'Return to practice' })).getAttribute('href')).toBe(practicePath(item.id, goalId));
  });

  it('replays a lost attempt with its original goal, revision and request identity', async () => {
    vi.mocked(post).mockRejectedValue(new ApiError('CONNECTION_ERROR', 'Saved receipt unavailable.'));
    const view = render(<PracticeWorkspace itemId={item.id} userId="owner" goalId={goalId} go={vi.fn()} />);
    fireEvent.change(await screen.findByLabelText('Your explanation'), { target: { value: 'Work under the selected goal.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' })); await screen.findByText('Saved receipt unavailable.');
    const original = vi.mocked(post).mock.calls[0][1]; view.unmount();
    render(<PracticeWorkspace itemId={item.id} userId="owner" goalId={goalId} go={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Check saved attempt' }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(vi.mocked(post).mock.calls[1][1]).toEqual(original);
    expect(original).toEqual(expect.objectContaining({ goal_id: goalId, expected_version: 4 }));
  });
});
