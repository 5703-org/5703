import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ApiError, patch, post, request } from './api';
import { MemoryPage, MemorySavedNotice, SessionMemoryNotices } from './Memory';
import type { MemoryEntry } from './learning-types';

vi.mock('./api', async original => ({ ...await original<typeof import('./api')>(), request: vi.fn(), patch: vi.fn(), post: vi.fn() }));
const entry: MemoryEntry = { id: 'memory-1', category: 'goal', content: 'Prepare for biology each weekend.', scope: 'biology', source_message_id: 'message-1', status: 'active', match_policy: 'rules_only', version: 3, updated_at: '2026-09-20T01:00:00Z', expires_at: null, verification: 'legacy_unverified', writer_version: 'explicit_learning_memory_v1' };
beforeEach(() => {
  vi.clearAllMocks();
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
  vi.mocked(request).mockImplementation(async path => path === '/me/memory/settings' ? { enabled: false, version: 2, revocation_epoch: 0 } : path === '/me/memories' ? [entry] : path === '/me/memory/summary' ? {enabled: false, version: 'summary-1', active_count: 1, summary: 'Memory is disabled.', items: [], limitations: []} : path === '/me/memory/processing' ? [] : { message_id: 'message-1', session_id: 'session-1', content: 'Please remember my biology study goal.' });
});
afterEach(cleanup);

const pendingAttemptFeedback = { outcome: 'pending_review', message: 'Immutable saved pending receipt.', grading_method: 'pending_model_assessment_v1', covered_point_ids: [], missing_point_ids: [], error_categories: [], semantic_correctness_verified: null };
const appliedAttemptFeedback = { ...pendingAttemptFeedback, outcome: 'correct', message: 'Applied source-bound model feedback.', grading_method: 'model_assessment_v1' };
function modelMemoryAttempt(status: 'applied' | 'pending_review' | 'superseded') {
  const original = vi.mocked(request).getMockImplementation()!;
  vi.mocked(request).mockImplementation(async (path, init) => path === '/me/memories'
    ? [{ ...entry, category: 'assessment_performance', source_message_id: null, verification: 'model_assessed_unverified', provenance: { kind: 'practice_attempt', practice_attempt_id: 'model-attempt', verification: 'model_assessed_unverified', grading_method: 'model_assessment_v1', semantic_correctness_verified: null } }]
    : path === '/learning/practice/attempts/model-attempt'
      ? { id: 'model-attempt', item_id: 'question', item_revision: 2, progress_version: 1, response: { selection: [], text: 'My authored saved reasoning.', value: null, unit: '', step: null }, feedback: pendingAttemptFeedback, assessment: { id: 'model-assessment', status, method: 'model_assessment_v1', feedback: appliedAttemptFeedback, applied_progress_version: status === 'applied' ? 2 : null } }
      : original(path, init));
}

it('uses applied model feedback in Memory practice provenance while retaining its unverified label', async () => {
  modelMemoryAttempt('applied'); render(<MemoryPage />);
  expect(await screen.findAllByText(/Model assessed; no independent semantic verification/)).toHaveLength(2);
  expect(screen.getByText('Model assessment against the saved question and textbook source')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'View practice attempt' }));
  const modal = await screen.findByRole('dialog', { name: 'Recorded practice attempt' });
  expect(await within(modal).findByText('Correct · Question revision 2')).toBeTruthy();
  expect(within(modal).getByText(appliedAttemptFeedback.message)).toBeTruthy();
  expect(within(modal).queryByText(pendingAttemptFeedback.message)).toBeNull();
  expect(within(modal).getByText(/Model assessment against the saved question and textbook source/)).toBeTruthy();
  expect(document.body.textContent).not.toContain('model_assessed_unverified');
  expect(document.body.textContent).not.toContain('model_assessment_v1');
});

it.each(['pending_review', 'superseded'] as const)('ignores unapplied model feedback in Memory provenance when %s', async status => {
  modelMemoryAttempt(status); render(<MemoryPage />);
  fireEvent.click(await screen.findByRole('button', { name: 'View practice attempt' }));
  const modal = await screen.findByRole('dialog', { name: 'Recorded practice attempt' });
  expect(await within(modal).findByText('Pending review · Question revision 2')).toBeTruthy();
  expect(within(modal).getByText(pendingAttemptFeedback.message)).toBeTruthy();
  expect(within(modal).queryByText(appliedAttemptFeedback.message)).toBeNull();
  expect(within(modal).getByText(/This attempt has no applied grade/)).toBeTruthy();
  expect(within(modal).queryByText(/Correct · Question revision/)).toBeNull();
});

it('identifies historical keyword grading in an older free-text Memory attempt', async () => {
  const original = vi.mocked(request).getMockImplementation()!;
  vi.mocked(request).mockImplementation(async (path, init) => path === '/me/memories'
    ? [{ ...entry, category: 'assessment_performance', source_message_id: null, provenance: { kind: 'practice_attempt', practice_attempt_id: 'historical-attempt' } }]
    : path === '/learning/practice/attempts/historical-attempt'
      ? { id: 'historical-attempt', item_id: 'question', item_revision: 1, response: { selection: [], text: 'Earlier saved expression.', value: null, unit: '', step: null }, feedback: { ...appliedAttemptFeedback, grading_method: 'deterministic_rules_v2' }, assessment: null }
      : original(path, init));
  render(<MemoryPage />); fireEvent.click(await screen.findByRole('button', { name: 'View practice attempt' }));
  const modal = await screen.findByRole('dialog', { name: 'Recorded practice attempt' });
  expect(await within(modal).findByText(/Historical keyword rules produced this feedback/)).toBeTruthy();
  expect(within(modal).queryByText(/Model assessment against/)).toBeNull();
});

it('labels model-assessed Memory preview fields without implying independent semantic verification', async () => {
  const practiceEntry = { ...entry, category: 'assessment_performance', verification: 'model_assessed_unverified' };
  vi.mocked(request).mockImplementation(async path => path.endsWith('/settings') ? { enabled: true, version: 2 }
    : path === '/me/memories' ? [practiceEntry] : path.endsWith('/processing') ? []
      : { enabled: true, version: 'summary', active_count: 1, summary: 'Authored model-assessed observation.', items: [practiceEntry], limitations: [] });
  vi.mocked(post).mockResolvedValue({ enabled: true, fields: [{ field_key: 'assessment_performance', scope: 'biology', verification: 'model_assessed_unverified', source: { memory_id: entry.id } }], entries: [practiceEntry], query_topics: ['biology'], excluded: [], limitations: [] });
  render(<MemoryPage />); await screen.findByText('Authored model-assessed observation.');
  fireEvent.click(screen.getByText('Preview memory for a question'));
  fireEvent.change(screen.getByLabelText('Question for memory preview'), { target: { value: 'Explain energy input.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Preview learner state' }));
  expect(await screen.findByText('biology · Model assessed; no independent semantic verification')).toBeTruthy();
  expect(document.body.textContent).not.toContain('Model assessed unverified');
});

it('opens an owned practice attempt as assessment provenance without inventing a source message', async () => {
  const original = vi.mocked(request).getMockImplementation()!;
  vi.mocked(request).mockImplementation(async (path, init) => path === '/me/memories' ? [{ ...entry, category: 'assessment_performance', source_message_id: null, verification: 'automatic_rubric_evaluated', provenance: { kind: 'practice_attempt', practice_item_id: 'item-1', practice_attempt_id: 'attempt-1', semantic_correctness_verified: null } }] : path === '/learning/practice/attempts/attempt-1' ? { id: 'attempt-1', item_id: 'item-1', item_revision: 2, response: { selection: [], text: 'My recorded reasoning.', value: null, unit: '', step: null }, feedback: { outcome: 'partial', message: 'One required point is missing.' } } : original(path, init));
  render(<MemoryPage />); fireEvent.click(await screen.findByRole('button', { name: 'View practice attempt' })); await screen.findByText('My recorded reasoning.');
  expect(request).toHaveBeenCalledWith('/learning/practice/attempts/attempt-1'); expect((screen.getByRole('button', { name: 'View source message' }) as HTMLButtonElement).disabled).toBe(true); expect(screen.getByText(/Broader proficiency and independent semantic correctness/)).toBeTruthy();
});

it('opens practice provenance from learner-state preview through the owned attempt endpoint', async () => {
  const practiceEntry = { ...entry, category: 'assessment_performance', source_message_id: null, provenance: { kind: 'practice_attempt', practice_attempt_id: 'attempt-preview' } };
  vi.mocked(request).mockImplementation(async path => path.endsWith('/settings') ? { enabled: true, version: 2 } : path === '/me/memories' ? [practiceEntry] : path.endsWith('/processing') ? [] : path === '/learning/practice/attempts/attempt-preview' ? { id: 'attempt-preview', item_id: 'item-1', item_revision: 1, response: { text: 'The actual saved attempt.', value: null, selection: [] }, feedback: { outcome: 'partial', message: 'Recorded feedback.' } } : { enabled: true, version: 'summary', active_count: 1, summary: 'An attributable attempt.', items: [practiceEntry], limitations: [] });
  vi.mocked(post).mockResolvedValue({ enabled: true, fields: [{ field_key: 'assessment_performance', scope: 'biology', verification: 'automatic_rubric_evaluated', source: { memory_id: entry.id } }], entries: [practiceEntry], query_topics: ['biology'], excluded: [], limitations: [] });
  render(<MemoryPage />); await screen.findByText('An attributable attempt.'); fireEvent.click(screen.getByText('Preview memory for a question')); fireEvent.change(screen.getByLabelText('Question for memory preview'), { target: { value: 'Explain cells.' } }); fireEvent.click(screen.getByRole('button', { name: 'Preview learner state' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Inspect source' })); await screen.findByText('The actual saved attempt.'); expect(request).toHaveBeenCalledWith('/learning/practice/attempts/attempt-preview'); expect(request).not.toHaveBeenCalledWith('/me/memories/memory-1/source');
});

it('shows the saved opt-in state and only enables after a real successful revision response', async () => {
  let resolve: (value: unknown) => void = () => {};
  vi.mocked(patch).mockImplementation(() => new Promise(done => { resolve = done; }));
  render(<MemoryPage />);
  const checkbox = await screen.findByRole('checkbox', { name: 'Use learning memory' }) as HTMLInputElement;
  expect(checkbox.checked).toBe(false); fireEvent.click(checkbox);
  expect(checkbox.checked).toBe(false); expect(checkbox.disabled).toBe(true);
  expect(patch).toHaveBeenCalledExactlyOnceWith('/me/memory/settings', { enabled: true, version: 2 });
  resolve({ enabled: true, version: 3, revocation_epoch: 0 });
  await screen.findByText('Learning memory enabled.'); expect(checkbox.checked).toBe(true);
});

it('retains edited content and reports a version conflict without a false save', async () => {
  vi.mocked(patch).mockRejectedValue(new ApiError('VERSION_CONFLICT', 'A newer memory revision exists.', 409));
  render(<MemoryPage />); fireEvent.click(await screen.findByRole('button', { name: 'Edit' }));
  fireEvent.change(screen.getByLabelText('Memory'), { target: { value: 'Prepare every Friday.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save memory' }));
  await screen.findByText('A newer memory revision exists.');
  expect((screen.getByLabelText('Memory') as HTMLTextAreaElement).value).toBe('Prepare every Friday.');
  expect(patch).toHaveBeenCalledExactlyOnceWith('/me/memories/memory-1', { version: 3, content: 'Prepare every Friday.', scope: 'biology', expires_at: null });
  expect(screen.queryByText('Memory updated.')).toBeNull();
});

it('pauses a saved entry only after its versioned controls response and retains the content', async () => {
  vi.mocked(patch).mockResolvedValue({ ...entry, status: 'paused', version: 4, match_policy: 'rules_only' });
  render(<MemoryPage />); fireEvent.click(await screen.findByRole('button', { name: 'Pause memory' }));
  await screen.findByText('Memory paused.'); expect(screen.getByText(entry.content!)).toBeTruthy();
  expect(patch).toHaveBeenCalledExactlyOnceWith('/me/memories/memory-1/controls', { version: 3, paused: true, match_policy: 'rules_only' });
  expect(screen.getByRole('button', { name: 'Resume memory' })).toBeTruthy();
});

it('lets the learner decline semantic applicability while retaining a paused memory', async () => {
  const original = vi.mocked(request).getMockImplementation()!;
  vi.mocked(request).mockImplementation((path, options) => path === '/me/memories' ? Promise.resolve([{ ...entry, status: 'paused', match_policy: 'calibrated_semantic' }]) : original(path, options));
  vi.mocked(patch).mockResolvedValue({ ...entry, status: 'paused', version: 4, match_policy: 'rules_only' });
  render(<MemoryPage />); const checkbox = await screen.findByRole('checkbox', { name: 'Allow semantic subject matches' });
  expect((checkbox as HTMLInputElement).checked).toBe(true); fireEvent.click(checkbox);
  await screen.findByText('Memory paused.'); expect((checkbox as HTMLInputElement).checked).toBe(false);
  expect(patch).toHaveBeenCalledExactlyOnceWith('/me/memories/memory-1/controls', { version: 3, paused: true, match_policy: 'rules_only' });
});

it('keeps pause and semantic controls unchanged on a version conflict', async () => {
  vi.mocked(patch).mockRejectedValue(new ApiError('VERSION_CONFLICT', 'Reload this memory before changing its controls.', 409));
  render(<MemoryPage />); fireEvent.click(await screen.findByRole('button', { name: 'Pause memory' }));
  await screen.findByText('Reload this memory before changing its controls.');
  expect(screen.getByRole('button', { name: 'Pause memory' })).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Resume memory' })).toBeNull();
  expect(screen.queryByText('Memory paused.')).toBeNull();
});

it('fetches an authorized source only when requested and renders its text safely', async () => {
  render(<MemoryPage />); await screen.findByText(entry.content!);
  expect(request).not.toHaveBeenCalledWith('/me/memories/memory-1/source');
  vi.mocked(request).mockResolvedValueOnce({ message_id: 'message-1', session_id: 'session-1', content: '<script>secret()</script> A durable goal.' });
  fireEvent.click(screen.getByRole('button', { name: 'View source message' }));
  await screen.findByText('<script>secret()</script> A durable goal.');
  expect(request).toHaveBeenLastCalledWith('/me/memories/memory-1/source'); expect(document.querySelector('script')).toBeNull();
});

it('removes deleted content from the DOM after versioned deletion and offers no hidden restore', async () => {
  render(<MemoryPage />); fireEvent.click(await screen.findByRole('button', { name: 'Delete' }));
  expect(screen.getByRole('dialog', { name: 'Delete this memory?' })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Delete memory' }));
  await screen.findByText('Memory deleted. Its original chat message is unchanged.');
  expect(request).toHaveBeenCalledWith('/me/memories/memory-1', { method: 'DELETE', body: '{"version":3}' });
  expect(document.body.innerHTML).not.toContain(entry.content);
  expect(screen.queryByRole('button', { name: /restore/i })).toBeNull();
});

it('never shows deleted tombstone content received during history management', async () => {
  vi.mocked(request).mockImplementation(async path => path.endsWith('/settings') ? { enabled: false, version: 2, revocation_epoch: 0 } : path === '/me/memories' ? [{ ...entry, status: 'deleted', content: 'Unexpected old body' }] : path.endsWith('/processing') ? [] : {enabled: false, version: 'v1', active_count: 0, summary: 'Memory is disabled.', items: [], limitations: []});
  render(<MemoryPage />); await screen.findByText('No learning memories saved.');
  expect(document.body.innerHTML).not.toContain('Unexpected old body');
});

it('shows the actual active summary and an observable failed extraction without losing controls', async () => {
  vi.mocked(request).mockImplementation(async path => path.endsWith('/settings') ? {enabled: true, version: 2, revocation_epoch: 0} : path === '/me/memories' ? [entry] : path.endsWith('/summary') ? {enabled: true, version: 'v2', active_count: 1, summary: 'Goal (biology): Prepare for biology each weekend.', items: [entry], limitations: []} : [{event_id: 'event-1', source_message_id: 'message-1', sequence: 4, status: 'failed', operations: [], error: {code: 'MEMORY_EXTRACTION_INVALID', message: 'Memory extraction failed. Current instructions still apply.'}, created_at: entry.updated_at}]);
  render(<MemoryPage />);
  await screen.findByText('Goal (biology): Prepare for biology each weekend.');
  expect(screen.getByText(/MEMORY_EXTRACTION_INVALID/)).toBeTruthy();
  expect(screen.getByRole('button', {name: 'Edit'})).toBeTruthy();
  expect(screen.queryByText('A learning preference or goal was saved.')).toBeNull();
});

it('previews actual selected fields without submitting an answer and clears stale preview on disable', async () => {
  vi.mocked(request).mockImplementation(async path => path.endsWith('/settings') ? {enabled: true, version: 2, revocation_epoch: 0} : path === '/me/memories' ? [entry] : path.endsWith('/processing') ? [] : {enabled: true, version: 'v3', active_count: 1, summary: 'Biology goal', items: [entry], limitations: []});
  vi.mocked(post).mockResolvedValue({enabled: true, policy_version: 'query_conditioned_memory_v2', fields: [{field_key: 'learning_goal', scope: 'biology', verification: 'explicit_user_statement', source: {memory_id: 'memory-1', version: 3}}], entries: [entry], query_topics: ['biology'], excluded: [], limitations: []});
  render(<MemoryPage />); await screen.findByText('Biology goal');
  fireEvent.click(screen.getByText('Preview memory for a question'));
  fireEvent.change(screen.getByLabelText('Question for memory preview'), {target: {value: 'Explain ATP.'}});
  fireEvent.click(screen.getByRole('button', {name: 'Preview learner state'}));
  await screen.findByText('Topics: biology');
  expect(post).toHaveBeenCalledExactlyOnceWith('/me/memory/preview', {question: 'Explain ATP.', use_profile: true});
  vi.mocked(patch).mockResolvedValue({enabled: false, version: 3, revocation_epoch: 1});
  fireEvent.click(screen.getByRole('checkbox', {name: 'Use learning memory'}));
  await screen.findByText('Learning memory disabled. Saved entries remain available to manage.');
  expect(screen.queryByText('Topics: biology')).toBeNull();
});

it('keeps saved entry management available when optional overview fails', async () => {
  const original = vi.mocked(request).getMockImplementation()!;
  vi.mocked(request).mockImplementation((path, options) => path.endsWith('/summary') ? Promise.reject(new ApiError('SERVICE_UNAVAILABLE', 'Overview is unavailable.', 503)) : original(path, options));
  render(<MemoryPage />); await screen.findByText('Overview is unavailable.');
  expect(screen.getByRole('button', {name: 'Edit'})).toBeTruthy();
  expect(screen.getByRole('button', {name: 'Refresh memory overview'})).toBeTruthy();
});

it('discards an in-flight learner-state preview when profile use is turned off', async () => {
  vi.mocked(request).mockImplementation(async path => path.endsWith('/settings') ? {enabled: true, version: 2, revocation_epoch: 0} : path === '/me/memories' ? [entry] : path.endsWith('/processing') ? [] : {enabled: true, version: 'v3', active_count: 1, summary: 'Biology goal', items: [entry], limitations: []});
  let complete: (value: unknown) => void = () => {};
  vi.mocked(post).mockImplementation(() => new Promise(resolve => { complete = resolve; }));
  render(<MemoryPage />); await screen.findByText('Biology goal');
  fireEvent.click(screen.getByText('Preview memory for a question'));
  fireEvent.change(screen.getByLabelText('Question for memory preview'), {target: {value: 'Explain ATP.'}});
  fireEvent.click(screen.getByRole('button', {name: 'Preview learner state'}));
  fireEvent.click(screen.getByRole('checkbox', {name: 'Use profile for this preview'}));
  complete({enabled: true, fields: [], entries: [], query_topics: ['biology'], excluded: []});
  await waitFor(() => expect(screen.getByRole('button', {name: 'Preview learner state'})).toBeTruthy());
  expect(screen.queryByText('Topics: biology')).toBeNull();
});

it('undoes only an actual saved entry and keeps failed undo visible without claiming success', async () => {
  vi.mocked(post).mockRejectedValueOnce(new ApiError('VERSION_CONFLICT', 'This memory changed. Open learning memory to review it.', 409)).mockResolvedValueOnce({ ...entry, status: 'deleted', content: null });
  render(<MemorySavedNotice memoryId="memory-1" version={3} />);
  fireEvent.click(screen.getByRole('button', { name: 'Undo memory save' }));
  await screen.findByText('This memory changed. Open learning memory to review it.');
  expect(screen.queryByText('Saved memory removed.')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Undo memory save' }));
  await screen.findByText('Saved memory removed.');
  await waitFor(() => expect(post).toHaveBeenLastCalledWith('/me/memories/memory-1/undo', { version: 3 }));
});

it('shows a late save notice only for its source turn and never fabricates a notice while waiting', async () => {
  vi.mocked(request).mockResolvedValue([
    { memory_id: 'older-memory', version: 1, message: 'Learning memory saved.', action: 'undo_save', source_message_id: 'older-message' },
    { memory_id: 'memory-1', version: 3, message: 'Learning memory saved.', action: 'undo_save', source_message_id: 'message-1' },
  ]);
  render(<SessionMemoryNotices sessionId="session-1" messageId="message-1" />);
  await screen.findByRole('button', { name: 'Undo memory save' });
  expect(screen.getAllByRole('button', { name: 'Undo memory save' })).toHaveLength(1);
  expect(request).toHaveBeenCalledExactlyOnceWith('/sessions/session-1/memory-notices');
  fireEvent.click(screen.getByRole('button', { name: 'Undo memory save' }));
  await waitFor(() => expect(post).toHaveBeenCalledWith('/me/memories/memory-1/undo', { version: 3 }));
});
