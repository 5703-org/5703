import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ApiError, post, request } from './api';
import { PracticeWorkspace, ReviewQueue } from './StudyPractice';
import type { PracticeAttempt, PracticeFeedback, PracticeItem, PracticeProgress, PracticeResponse, ReviewItem } from './study-types';

vi.mock('./api', async original => ({ ...await original<typeof import('./api')>(), request: vi.fn(), post: vi.fn() }));
const item: PracticeItem = { id: 'question', title: 'Independent software fixture', kind: 'mcq', prompt: 'Select the named option.', options: [{ id: 'A', text: 'First option' }, { id: 'B', text: 'Second option' }], concepts: ['fixture'], conditions: [], source: { release_id: 'release', document_id: 'book', processing_id: 'processing', source_unit_id: 'unit', text_hash: 'hash', start: 0, end: null }, item_revision: 1, validation: { status: 'passed' } };
const initial: PracticeProgress = { item_id: item.id, version: 0, current_step: 1, current_step_prompt: null, total_steps: 1, help_level: 0, state: 'awaiting_attempt', attempts: [], hints: [], full_explanation: null };
const practiceReview: ReviewItem = { id: 'review-one', target_type: 'practice_item', item_id: item.id, note_id: null, title: item.title, concepts: ['fixture'], due_at: '2026-09-01T00:00:00Z', error_categories: ['unit_mismatch'], attempt_count: 2, correct_count: 0, graded_count: 2, pending_count: 0, recent_attempt_count: 2, recent_graded_count: 2, recent_pending_count: 0, recent_error_counts: { unit_mismatch: 2 }, suggested_item_id: 'related-question', scheduling_reason: 'Review the unit after a partial attempt.', version: 4 };
const personalReview: ReviewItem = { ...practiceReview, id: 'card-review', target_type: 'personal_review_card', item_id: null, note_id: 'note/with space', title: 'My transport card', card_content: 'A **personal** explanation of transport.', card_source: item.source, concepts: ['transport'], error_categories: [], attempt_count: 0, correct_count: 0, graded_count: 0, pending_count: 0, recent_attempt_count: 0, recent_graded_count: 0, recent_pending_count: 0, recent_error_counts: {}, suggested_item_id: null, scheduling_reason: 'Due for your first recall.', version: 3 };
let progress: PracticeProgress;
function responses(question = item) { vi.mocked(request).mockImplementation(async path => path.endsWith('/progress') ? progress : question); }
beforeEach(() => { vi.resetAllMocks(); sessionStorage.clear(); progress = structuredClone(initial); responses(); });
afterEach(cleanup);
const props = { itemId: item.id, userId: 'owned-user', go: vi.fn() };
const pendingFeedback: PracticeFeedback = { outcome: 'pending_review', message: 'Your work was saved and is awaiting review.', grading_method: 'pending_model_assessment_v1', error_categories: [], covered_point_ids: [], missing_point_ids: [], semantic_correctness_verified: null };
const modelFeedback: PracticeFeedback = { ...pendingFeedback, outcome: 'correct', message: 'The model assessment accepted this step.', grading_method: 'model_assessment_v1' };
function textAttempt(): PracticeAttempt {
  return { id: 'saved-attempt', item_id: item.id, item_revision: 1, progress_version: 1, response: { selection: [], text: 'My saved step explanation.', value: null, unit: '', step: 1 }, feedback: pendingFeedback, created_at: '2026-10-03T00:00:00Z' };
}

describe('practice state and server grading boundaries', () => {
  it.each(['pending_review', 'superseded'] as const)('keeps text and ignores unapplied model feedback when assessment is %s', async status => {
    responses({ ...item, kind: 'step' }); progress = { ...initial, current_step_response_kind: 'text', total_steps: 2 };
    const saved = { ...textAttempt(), assessment: { id: 'assessment', status, method: 'model_assessment_v1' as const, feedback: modelFeedback, applied_progress_version: null } };
    vi.mocked(post).mockResolvedValue(saved);
    render(<PracticeWorkspace {...props} />); const input = await screen.findByLabelText('Your work for this step');
    fireEvent.change(input, { target: { value: saved.response.text } }); fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' }));
    await screen.findByRole('heading', { name: status === 'superseded' ? 'Assessment superseded' : 'Pending review' });
    expect((input as HTMLTextAreaElement).value).toBe(saved.response.text);
    expect(screen.getByText('Step 1 of 2')).toBeTruthy(); expect(screen.queryByRole('heading', { name: 'Correct' })).toBeNull();
    expect(screen.queryByText(modelFeedback.message)).toBeNull(); expect(screen.queryByText('All steps are saved. Review your attempts or choose another practice question.')).toBeNull();
    expect(JSON.parse(sessionStorage.getItem('cs30.draft.learning.owned-user.question')!).text).toBe(saved.response.text);
  });
  it('uses only an applied model assessment to grade and clear a completed text step', async () => {
    responses({ ...item, kind: 'step' }); progress = { ...initial, current_step_response_kind: 'text', total_steps: 2 };
    const saved: PracticeAttempt = { ...textAttempt(), assessment: { id: 'assessment', status: 'applied', method: 'model_assessment_v1', feedback: modelFeedback, applied_progress_version: 2 } };
    vi.mocked(post).mockImplementation(async () => { progress = { ...progress, version: 2, current_step: 2, attempts: [saved] }; return saved; });
    render(<PracticeWorkspace {...props} />); fireEvent.change(await screen.findByLabelText('Your work for this step'), { target: { value: saved.response.text } }); fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' }));
    await screen.findByRole('heading', { name: 'Correct' }); await screen.findByText('Step 2 of 2');
    expect((screen.getByLabelText('Your work for this step') as HTMLTextAreaElement).value).toBe('');
    expect(screen.getByText(modelFeedback.message)).toBeTruthy(); expect(screen.queryByText(pendingFeedback.message)).toBeNull();
    expect(screen.getByText('Model assessment against the saved question and textbook source.')).toBeTruthy(); expect(saved.feedback).toEqual(pendingFeedback);
  });
  it('labels historical keyword feedback and does not clear a text step using that old grade', async () => {
    responses({ ...item, kind: 'step' }); progress = { ...initial, current_step_response_kind: 'text', total_steps: 2 };
    const saved: PracticeAttempt = { ...textAttempt(), feedback: { ...modelFeedback, grading_method: 'deterministic_rules_v2' } };
    vi.mocked(post).mockResolvedValue(saved);
    render(<PracticeWorkspace {...props} />); const input = await screen.findByLabelText('Your work for this step'); fireEvent.change(input, { target: { value: saved.response.text } }); fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' }));
    await screen.findByRole('heading', { name: 'Historical keyword result: Correct' }); expect((input as HTMLTextAreaElement).value).toBe(saved.response.text);
    expect(screen.getByText('Earlier keyword rules produced this historical feedback.')).toBeTruthy(); expect(screen.queryByText('Model assessment against the saved question and textbook source.')).toBeNull();
  });
  it('shows failed model checking as pending review without correctness or error-point labels', async () => {
    responses({ ...item, kind: 'short' });
    const saved: PracticeAttempt = { ...textAttempt(), response: { ...textAttempt().response, step: null }, assessment: { id: 'failed-check', status: 'pending_review', method: 'model_assessment_v1', applied_progress_version: null, feedback: { ...modelFeedback, error_categories: ['unapplied_error'], missing_point_ids: ['unapplied-point'] } } };
    vi.mocked(post).mockResolvedValue(saved);
    render(<PracticeWorkspace {...props} />); const input = await screen.findByLabelText('Your explanation'); fireEvent.change(input, { target: { value: saved.response.text } }); fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' }));
    await screen.findByRole('heading', { name: 'Pending review' }); expect((input as HTMLTextAreaElement).value).toBe(saved.response.text);
    expect(screen.getByText('Your work is saved. This attempt has no grade and does not complete the step.')).toBeTruthy();
    expect(document.body.textContent).not.toContain('Unapplied Error'); expect(document.body.textContent).not.toContain('unapplied-point'); expect(screen.queryByRole('heading', { name: 'Correct' })).toBeNull();
  });
  it('uses graded review denominators and reports pending counts separately', async () => {
    vi.mocked(request).mockResolvedValue([{ ...practiceReview, attempt_count: 5, correct_count: 1, graded_count: 2, pending_count: 3, recent_attempt_count: 4, recent_graded_count: 1, recent_pending_count: 3, recent_error_counts: { unit_mismatch: 1 } }]);
    render(<ReviewQueue go={vi.fn()} />);
    expect(await screen.findByText(/1 correct of 2 graded attempts · 3 pending review/)).toBeTruthy();
    expect(screen.getByText('1 of 1 recent graded attempts: Unit mismatch')).toBeTruthy(); expect(screen.getByText('3 recent attempts pending review.')).toBeTruthy();
    expect(screen.queryByText(/1 correct of 5/)).toBeNull(); expect(screen.queryByText(/1 of 4 recent/)).toBeNull();
  });
  it.each(['mcq', 'multiselect', 'short', 'numeric', 'step'] as const)('submits an exact %s response without exposing private grading rules', async kind => {
    responses({ ...item, kind }); if (kind === 'step') progress = { ...initial, current_step: 2, total_steps: 3, current_step_prompt: 'Calculate this step.', current_step_response_kind: 'numeric', expected_unit: 'mL' };
    vi.mocked(post).mockRejectedValue(new ApiError('RULE_CHECK_FAILED', 'Preserved attempt failure.'));
    render(<PracticeWorkspace {...props} />); await screen.findByRole('button', { name: 'Check my attempt' });
    let expected: PracticeResponse = { selection: [], text: '', value: null, unit: '', step: kind === 'step' ? 2 : null };
    if (kind === 'mcq' || kind === 'multiselect') { fireEvent.click(screen.getByLabelText('First option')); expected.selection = ['A']; if (kind === 'multiselect') { fireEvent.click(screen.getByLabelText('Second option')); expected.selection.push('B'); } }
    else if (kind === 'short') { fireEvent.change(screen.getByLabelText('Your explanation'), { target: { value: 'My independent reasoning.' } }); expected.text = 'My independent reasoning.'; }
    else { fireEvent.change(screen.getByLabelText('Numeric value'), { target: { value: '2.5' } }); fireEvent.change(screen.getByLabelText('Unit'), { target: { value: 'mL' } }); expected.value = 2.5; expected.unit = 'mL'; }
    fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' })); await screen.findByText('Preserved attempt failure.');
    expect(post).toHaveBeenCalledExactlyOnceWith('/learning/practice/question/attempts', { idempotency_key: expect.any(String), response: expected, expected_version: 0 });
    expect(screen.queryByText('Correct answer')).toBeNull(); expect(screen.queryByRole('heading', { name: 'Full explanation' })).toBeNull();
  });
  it('restores a failed draft and reuses its request identity after remount', async () => {
    responses({ ...item, kind: 'short' }); vi.mocked(post).mockRejectedValue(new ApiError('CONNECTION_ERROR', 'Receipt unavailable.'));
    const view = render(<PracticeWorkspace {...props} />); await screen.findByLabelText('Your explanation'); fireEvent.change(screen.getByLabelText('Your explanation'), { target: { value: 'Work that must survive.' } }); fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' })); await screen.findByText('Receipt unavailable.');
    const first = vi.mocked(post).mock.calls[0][1]; view.unmount(); render(<PracticeWorkspace {...props} />); await screen.findByLabelText('Your explanation'); expect((screen.getByLabelText('Your explanation') as HTMLTextAreaElement).value).toBe('Work that must survive.'); fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' })); await waitFor(() => expect(post).toHaveBeenCalledTimes(2)); expect(vi.mocked(post).mock.calls[1][1]).toEqual(first);
  });
  it('fetches a full explanation only after the explicit help action succeeds', async () => {
    render(<PracticeWorkspace {...props} />); await screen.findByRole('button', { name: 'Show full explanation' }); expect(document.body.textContent).not.toContain('Private full solution');
    vi.mocked(post).mockImplementation(async () => { progress = { ...initial, version: 1, full_explanation: 'Private full solution.' }; return progress; });
    fireEvent.click(screen.getByRole('button', { name: 'Show full explanation' })); await screen.findByText('Private full solution.'); expect(post).toHaveBeenCalledExactlyOnceWith('/learning/practice/question/help', { action: 'full_explanation', expected_version: 0 });
  });
  it('opens the owned tutor from saved practice with task/version and source bindings', async () => {
    const go = vi.fn(); vi.mocked(post).mockResolvedValue({ session_id: 'tutor-session', task_id: 'tutor-task', task_version: 3, practice_progress_version: 0, teaching_mode: 'hint', source: item.source });
    render(<PracticeWorkspace {...props} go={go} />); fireEvent.click(await screen.findByRole('button', { name: 'Continue with the tutor' }));
    await waitFor(() => expect(go).toHaveBeenCalledWith('/chat/tutor-session'));
    expect(post).toHaveBeenCalledExactlyOnceWith('/learning/practice/question/tutor', { expected_version: 0 });
    expect(JSON.parse(sessionStorage.getItem('cs30.draft.owned-user.tutor-session.teaching')!)).toEqual({ teaching_mode: 'hint', task_action: 'continue', task_id: 'tutor-task', task_version: 3 });
    expect(JSON.parse(sessionStorage.getItem('cs30.draft.owned-user.tutor-session.reading-context')!)).toEqual({ scope: 'chapter', document_id: 'book', source_unit_id: 'unit' });
  });
  it('retains the practice workspace when tutoring creation fails', async () => {
    const go = vi.fn(); vi.mocked(post).mockRejectedValue(new ApiError('VERSION_CONFLICT', 'Reload saved practice before opening its tutor.', 409));
    render(<PracticeWorkspace {...props} go={go} />); fireEvent.click(await screen.findByRole('button', { name: 'Continue with the tutor' }));
    await screen.findByText('Reload saved practice before opening its tutor.'); expect(go).not.toHaveBeenCalled(); expect(sessionStorage.getItem('cs30.draft.owned-user.tutor-session.teaching')).toBeNull();
  });
  it('shows completed step work without offering an invalid extra step submission', async () => {
    responses({ ...item, kind: 'step' }); progress = { ...initial, state: 'completed', current_step: 2, total_steps: 2, current_step_response_kind: null };
    render(<PracticeWorkspace {...props} />); await screen.findByText('All steps are saved. Review your attempts or choose another practice question.');
    expect(screen.queryByRole('form', { name: 'Practice response' })).toBeNull(); expect(screen.getByRole('button', { name: 'Show full explanation' })).toBeTruthy(); expect(post).not.toHaveBeenCalled();
  });
  it('replays the original step and version when a saved attempt lost its receipt before reload', async () => {
    responses({ ...item, kind: 'step' }); progress = { ...initial, current_step_response_kind: 'text', total_steps: 2 };
    vi.mocked(post).mockRejectedValue(new ApiError('CONNECTION_ERROR', 'Receipt lost.'));
    const view = render(<PracticeWorkspace {...props} />); await screen.findByLabelText('Your work for this step'); fireEvent.change(screen.getByLabelText('Your work for this step'), { target: { value: 'Step one work.' } }); fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' })); await screen.findByText('Receipt lost.'); const original = vi.mocked(post).mock.calls[0][1]; view.unmount();
    progress = { ...progress, version: 1, current_step: 2 }; render(<PracticeWorkspace {...props} />); await screen.findByText('Step 2 of 2'); fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' })); await waitFor(() => expect(post).toHaveBeenCalledTimes(2)); expect(vi.mocked(post).mock.calls[1][1]).toEqual(original); expect(original).toEqual(expect.objectContaining({ expected_version: 0, response: expect.objectContaining({ step: 1 }) }));
  });
  it('rejects non-finite numeric input before a request', async () => {
    responses({ ...item, kind: 'numeric' }); render(<PracticeWorkspace {...props} />); await screen.findByLabelText('Numeric value'); fireEvent.change(screen.getByLabelText('Numeric value'), { target: { value: 'Infinity' } }); fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' })); await screen.findByText('Enter a finite numeric value.'); expect(post).not.toHaveBeenCalled();
  });
  it.each(['text', 'numeric'] as const)('recovers a lost %s step receipt after the next step changes input kind', async originalKind => {
    responses({ ...item, kind: 'step' }); progress = { ...initial, current_step_response_kind: originalKind, total_steps: 2 };
    vi.mocked(post).mockRejectedValue(new ApiError('CONNECTION_ERROR', 'Receipt lost after saving.'));
    const view = render(<PracticeWorkspace {...props} />); await screen.findByRole('button', { name: 'Check my attempt' });
    if (originalKind === 'text') fireEvent.change(screen.getByLabelText('Your work for this step'), { target: { value: 'Ready.' } });
    else { fireEvent.change(screen.getByLabelText('Numeric value'), { target: { value: '5' } }); fireEvent.change(screen.getByLabelText('Unit'), { target: { value: 'mL' } }); }
    fireEvent.click(screen.getByRole('button', { name: 'Check my attempt' })); await screen.findByText('Receipt lost after saving.');
    const original = vi.mocked(post).mock.calls[0][1]; view.unmount();
    progress = { ...progress, version: 1, current_step: 2, current_step_response_kind: originalKind === 'text' ? 'numeric' : 'text' };
    render(<PracticeWorkspace {...props} />); await screen.findByText('Step 2 of 2');
    // The new input is empty/required; recovery must bypass that unrelated form.
    expect((screen.getByLabelText(originalKind === 'text' ? 'Numeric value' : 'Your work for this step') as HTMLInputElement).value).toBe('');
    fireEvent.click(screen.getByRole('button', { name: 'Check saved attempt' }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2)); expect(vi.mocked(post).mock.calls[1][1]).toEqual(original);
    expect(original).toEqual(expect.objectContaining({ expected_version: 0, response: expect.objectContaining({ step: 1 }) }));
  });
  it('shows saved server feedback and keeps review intervals version-bound', async () => {
    vi.mocked(request).mockResolvedValue([practiceReview]);
    vi.mocked(post).mockRejectedValue(new ApiError('VERSION_CONFLICT', 'Reload the latest review version.')); const go = vi.fn(); render(<ReviewQueue go={go} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Try a related question' })); expect(go).toHaveBeenCalledWith('/learn/practice/related-question'); fireEvent.click(screen.getByRole('button', { name: 'Remind me tomorrow' })); await screen.findByText('Reload the latest review version.'); expect(post).toHaveBeenCalledExactlyOnceWith('/learning/review/review-one/reschedule', { days: 1, expected_version: 4 }); expect(screen.getByText(item.title)).toBeTruthy(); fireEvent.click(screen.getByLabelText('Due today only')); await waitFor(() => expect(request).toHaveBeenCalledWith('/learning/review?due_only=false', expect.any(Object)));
  });
  it.each([['I recalled it', 'recalled'], ['I need another review', 'needs_review']] as const)('reveals a personal card and records %s with its saved version', async (button, outcome) => {
    vi.mocked(request).mockResolvedValue([personalReview]); vi.mocked(post).mockResolvedValue({ ...personalReview, version: 4 }); const go = vi.fn(); render(<ReviewQueue go={go} />);
    await screen.findByRole('button', { name: 'Reveal my note' });
    expect(screen.queryByText(/personal explanation of transport/)).toBeNull(); expect(screen.queryByRole('button', { name: button })).toBeNull(); expect(screen.queryByRole('button', { name: 'Review this question' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Open note' })); expect(go).toHaveBeenCalledWith('/learn/notes/note%2Fwith%20space');
    fireEvent.click(screen.getByRole('button', { name: 'Read source' })); expect(go).toHaveBeenCalledWith('/learn/library/book/unit/unit');
    fireEvent.click(screen.getByRole('button', { name: 'Reveal my note' })); expect(await screen.findByText(/^personal$/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: button })); await waitFor(() => expect(post).toHaveBeenCalledExactlyOnceWith('/learning/review/card-review/record', { expected_version: 3, outcome }));
    expect(await screen.findByText(outcome === 'recalled' ? 'Recall recorded.' : 'Another review recorded.')).toBeTruthy();
    await waitFor(() => expect(screen.queryByText(/^personal$/)).toBeNull());
  });
  it('keeps a card visible when recording conflicts and does not report success', async () => {
    vi.mocked(request).mockResolvedValue([personalReview]); vi.mocked(post).mockRejectedValue(new ApiError('VERSION_CONFLICT', 'Reload the latest card review.')); render(<ReviewQueue go={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Reveal my note' })); fireEvent.click(screen.getByRole('button', { name: 'I recalled it' }));
    await screen.findByText('Reload the latest card review.'); expect(screen.getByRole('heading', { name: 'My transport card' })).toBeTruthy(); expect(screen.queryByText('Recall recorded.')).toBeNull();
  });
  it('does not offer a self-report for an empty card', async () => {
    vi.mocked(request).mockResolvedValue([{ ...personalReview, card_content: '   ' }]); render(<ReviewQueue go={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Reveal my note' })); expect(screen.getByText(/has no content yet/)).toBeTruthy(); expect(screen.queryByRole('button', { name: 'I recalled it' })).toBeNull(); expect(post).not.toHaveBeenCalled();
  });
});
