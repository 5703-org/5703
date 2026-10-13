import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError, post } from './api';
import { Button, ErrorNotice, Loading, titleCase } from './components';
import { SafeMarkdown } from './Markdown';
import { useLearningResource } from './learning-ui';
import type { PracticeAttempt, PracticeItem, PracticeProgress, PracticeResponse, PracticeTutor, ReviewItem } from './study-types';
import { effectivePracticeFeedback, isHistoricalLexicalFeedback } from './study-types';
import { readingContextKey } from './reading-context';
import { practicePath } from './practice-navigation';

export const practiceLabels = { mcq: 'Single choice', multiselect: 'Multiple choice', short: 'Short explanation', numeric: 'Number and unit', step: 'Step by step' };
function savedPracticeDraft(key: string) {
  try { const value = JSON.parse(sessionStorage.getItem(key) || '{}'); return { selection: Array.isArray(value.selection) ? value.selection.filter((id: unknown) => typeof id === 'string') as string[] : [], text: typeof value.text === 'string' ? value.text : '', value: typeof value.value === 'string' ? value.value : '', unit: typeof value.unit === 'string' ? value.unit : '' }; }
  catch { return { selection: [], text: '', value: '', unit: '' }; }
}
export function PracticeList({ go, goalId, unitId }: { go: (path: string) => void; goalId?: string; unitId?: string }) {
  const [concept, setConcept] = useState(''); const [filter, setFilter] = useState('');
  const params = new URLSearchParams(); if (goalId) params.set('goal_id', goalId); if (filter) params.set('concept', filter); if (unitId) params.set('unit_id', unitId);
  const result = useLearningResource<PracticeItem[]>(`/learning/practice?${params}`);
  return <section className="stack"><div><h1>Practice</h1><p className="page-intro">Try a question, inspect the feedback and choose your next step.</p></div>
    <form className="learning-search" onSubmit={event => { event.preventDefault(); setFilter(concept.trim()); }}><label>Find a concept<input value={concept} onChange={event => setConcept(event.target.value)} /></label><Button type="submit">Search practice</Button></form>
    <ErrorNotice error={result.error} action={<Button onClick={result.reload}>Reload practice</Button>} />{result.loading && <Loading>Loading published practice…</Loading>}
    {result.data && (result.data.length ? <div className="learning-cards">{result.data.map(item => <article className="record stack" key={item.id}><span className="eyebrow">{practiceLabels[item.kind]}</span><h2>{item.title}</h2><p className="secondary">{item.concepts.join(' · ')} · Revision {item.item_revision}</p><Button className="primary" onClick={() => go(practicePath(item.id, goalId))}>Start practice</Button></article>)}</div> : <p>No published questions match this selection.</p>)}
  </section>;
}

export function PracticeWorkspace({ itemId, userId, goalId, go }: { itemId: string; userId: string; goalId?: string; go: (path: string) => void }) {
  const item = useLearningResource<PracticeItem>(`/learning/practice/${encodeURIComponent(itemId)}`);
  const progress = useLearningResource<PracticeProgress>(`/learning/practice/${encodeURIComponent(itemId)}/progress`);
  const draftKey = `cs30.draft.learning.${userId}.${itemId}`;
  const initial = useRef(savedPracticeDraft(draftKey));
  const [selection, setSelection] = useState<string[]>(initial.current.selection); const [text, setText] = useState(initial.current.text);
  const [value, setValue] = useState(initial.current.value); const [unit, setUnit] = useState(initial.current.unit);
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  const [receipt, setReceipt] = useState<PracticeAttempt | null>(null);
  const pendingKey = `cs30.pending.learning.${userId}.${itemId}`;
  const pending = useRef<{ signature: string; key: string } | null>(null);
  const [unconfirmed, setUnconfirmed] = useState(Boolean(sessionStorage.getItem(pendingKey)));
  useEffect(() => { sessionStorage.setItem(draftKey, JSON.stringify({ selection, text, value, unit })); }, [draftKey, selection, text, value, unit]);
  useEffect(() => { try { pending.current = JSON.parse(sessionStorage.getItem(pendingKey) || 'null'); } catch { pending.current = null; } }, [pendingKey]);
  useEffect(() => { setReceipt(null); }, [itemId]);
  const submit = async (event?: FormEvent, recover = false) => {
    event?.preventDefault(); if (!item.data || !progress.data || busy) return;
    const response: PracticeResponse = { selection, text, value: value.trim() ? Number(value) : null, unit: unit.trim(), step: item.data.kind === 'step' ? progress.data.current_step : null };
    let expectedVersion = progress.data.version;
    let submittedResponse = response;
    // An accepted request can lose its receipt. Replay its original step/version
    // when the learner's work is unchanged, even after a newer progress read.
    let retryOriginal = false;
    if (pending.current) {
      try {
        const [savedItem, savedResponse, savedGoal, savedVersion] = JSON.parse(pending.current.signature) as [string, PracticeResponse, string | null, number];
        const work = (value: PracticeResponse) => JSON.stringify([value.selection, value.text, value.value, value.unit]);
        if (savedItem === itemId && savedGoal === (goalId || null) && Number.isInteger(savedVersion) && savedResponse && (recover || work(savedResponse) === work(response))) {
          retryOriginal = true; expectedVersion = savedVersion; submittedResponse = savedResponse;
        }
      } catch { /* Invalid local metadata cannot authorize a request replay. */ }
    }
    if (recover && !retryOriginal) { setError(new Error('The saved submission could not be recovered. Reload your attempts before submitting again.')); return; }
    if (pending.current && !retryOriginal) { setError(new Error('Check the saved attempt before submitting changed work.')); return; }
    if (!retryOriginal && (item.data.kind === 'numeric' || progress.data.current_step_response_kind === 'numeric') && (response.value === null || !Number.isFinite(response.value))) { setError(new Error('Enter a finite numeric value.')); return; }
    const signature = JSON.stringify([itemId, response, goalId, progress.data.version]);
    if (!retryOriginal) pending.current = { signature, key: crypto.randomUUID() };
    sessionStorage.setItem(pendingKey, JSON.stringify(pending.current)); setUnconfirmed(true);
    setBusy(true); setError(null);
    try {
      const saved = await post<PracticeAttempt>(`/learning/practice/${encodeURIComponent(itemId)}/attempts`, { idempotency_key: pending.current!.key, response: submittedResponse, expected_version: expectedVersion, ...(goalId ? { goal_id: goalId } : {}) });
      setReceipt(saved); pending.current = null; sessionStorage.removeItem(pendingKey); setUnconfirmed(false); progress.reload();
      if (item.data.kind === 'step' && effectivePracticeFeedback(saved).outcome === 'correct' && !isHistoricalLexicalFeedback(saved) && JSON.stringify([submittedResponse.text, submittedResponse.value, submittedResponse.unit, submittedResponse.selection]) === JSON.stringify([text, response.value, response.unit, selection])) { setText(''); setValue(''); setUnit(''); setSelection([]); }
    } catch (caught) { if (caught instanceof ApiError && caught.status >= 400 && caught.status < 500) { pending.current = null; sessionStorage.removeItem(pendingKey); setUnconfirmed(false); } setError(caught); } finally { setBusy(false); }
  };
  const help = async (action: 'hint' | 'full_explanation') => {
    if (!progress.data || busy) return; setBusy(true); setError(null);
    try { await post(`/learning/practice/${encodeURIComponent(itemId)}/help`, { action, expected_version: progress.data.version }); progress.reload(); }
    catch (caught) { setError(caught); } finally { setBusy(false); }
  };
  const continueWithTutor = async () => {
    if (!progress.data || busy || unconfirmed) return; setBusy(true); setError(null);
    try {
      const saved = await post<PracticeTutor>(`/learning/practice/${encodeURIComponent(itemId)}/tutor`, { expected_version: progress.data.version, ...(goalId ? { goal_id: goalId } : {}) });
      if ((saved.goal_id || null) !== (goalId || null)) throw new Error('The tutor did not retain the selected learning goal. Reload saved practice and try again.');
      const key = `cs30.draft.${userId}.${saved.session_id}`;
      sessionStorage.setItem(key, saved.teaching_mode === 'hint' ? 'Help me with the current practice step without giving the answer.' : 'Help me review this completed practice question.');
      sessionStorage.setItem(`${key}.teaching`, JSON.stringify({ teaching_mode: saved.teaching_mode, task_action: 'continue', task_id: saved.task_id, task_version: saved.task_version }));
      sessionStorage.setItem(readingContextKey(userId, saved.session_id), JSON.stringify({ scope: 'chapter', document_id: saved.source.document_id, source_unit_id: saved.source.source_unit_id }));
      go(`/chat/${encodeURIComponent(saved.session_id)}`);
    } catch (caught) { setError(caught); } finally { setBusy(false); }
  };
  return <section className="stack practice-workspace"><Button onClick={() => go('/learn/practice')}>Back to practice</Button><ErrorNotice error={item.error || progress.error || error} action={<Button disabled={busy} onClick={() => { item.reload(); progress.reload(); }}>Reload saved practice</Button>} />
    {item.loading && <Loading>Opening practice…</Loading>}{item.data && <><div><span className="eyebrow">{practiceLabels[item.data.kind]} · Revision {item.data.item_revision}</span><h1>{item.data.title}</h1></div><SafeMarkdown text={item.data.prompt} />{item.data.conditions.length > 0 && <div><h2>Given conditions</h2><ul>{item.data.conditions.map((condition, index) => <li key={index}>{condition}</li>)}</ul></div>}
      <div className="form-actions"><Button onClick={() => go(`/learn/library/${encodeURIComponent(item.data!.source.document_id)}/unit/${encodeURIComponent(item.data!.source.source_unit_id)}`)}>Read the textbook source</Button><span className="secondary">{item.data.concepts.join(' · ')}</span></div>
      {progress.loading && <Loading>Loading saved attempts…</Loading>}{progress.data && <><div className="practice-state" role="status"><strong>{progress.data.state === 'completed' ? 'Completed' : 'Your next attempt'}</strong>{item.data.kind === 'step' && <span>Step {progress.data.current_step} of {progress.data.total_steps}</span>}<span>Help level {progress.data.help_level}</span></div>
        {progress.data.current_step_prompt && <p className="source-passage">{progress.data.current_step_prompt}</p>}
        {unconfirmed && <div className="record"><p>Your last submission has no confirmed receipt. Recover its saved result before repeating that work.</p><Button disabled={busy} onClick={() => submit(undefined, true)}>Check saved attempt</Button></div>}
        {item.data.kind === 'step' && progress.data.state === 'completed' ? <p role="status">All steps are saved. Review your attempts or choose another practice question.</p> : <form className="stack" onSubmit={submit} aria-label="Practice response">
          {(item.data.kind === 'mcq' || item.data.kind === 'multiselect') ? <fieldset className="practice-options"><legend>{item.data.kind === 'mcq' ? 'Choose one answer' : 'Choose all answers that apply'}</legend>{item.data.options.map(option => <label key={option.id}><input type={item.data!.kind === 'mcq' ? 'radio' : 'checkbox'} name="practice-choice" checked={selection.includes(option.id)} disabled={busy} onChange={event => setSelection(item.data!.kind === 'mcq' ? [option.id] : event.target.checked ? [...selection, option.id] : selection.filter(id => id !== option.id))} />{option.text}</label>)}</fieldset> : (item.data.kind === 'numeric' || progress.data.current_step_response_kind === 'numeric') ? <div className="form-grid"><label>Numeric value<input inputMode="decimal" required value={value} onChange={event => setValue(event.target.value)} disabled={busy} /></label><label>Unit<input value={unit} maxLength={30} onChange={event => setUnit(event.target.value)} disabled={busy} placeholder={progress.data.expected_unit || "For example, mL"} /></label></div> : <label>{item.data.kind === 'step' ? 'Your work for this step' : 'Your explanation'}<textarea required rows={5} maxLength={8000} value={text} onChange={event => setText(event.target.value)} disabled={busy} /></label>}
          {(item.data.kind === 'short' || (item.data.kind === 'step' && progress.data.current_step_response_kind !== 'numeric')) && <p className="secondary">The configured model checks your explanation against the saved question and textbook source. If it cannot finish, your answer remains pending review.</p>}
          <Button className="primary" type="submit" disabled={busy || ((item.data.kind === 'mcq' || item.data.kind === 'multiselect') && !selection.length)}>{busy ? 'Checking your attempt…' : 'Check my attempt'}</Button>
        </form>}
        <div className="form-actions"><Button disabled={busy} onClick={() => help('hint')}>Get the next hint</Button><Button disabled={busy} onClick={() => help('full_explanation')}>Show full explanation</Button></div>
        <div className="form-actions"><Button disabled={busy || unconfirmed} onClick={continueWithTutor}>Continue with the tutor</Button><p className="secondary">Continue from your saved step, attempts and displayed hints. Submit your practice work here to record its grade.</p></div>
        {progress.data.hints.map((hint, index) => <section className="record stack" key={index}><h2>Hint {index + 1}</h2><SafeMarkdown text={hint} /></section>)}
        {progress.data.full_explanation && <section className="record stack"><h2>Full explanation</h2><SafeMarkdown text={progress.data.full_explanation} /></section>}
        {receipt && !progress.data.attempts.some(attempt => attempt.id === receipt.id) && <AttemptCard attempt={receipt} />}
        <section className="stack"><h2>Your attempts</h2>{progress.data.attempts.length ? [...progress.data.attempts].reverse().map(attempt => <AttemptCard key={attempt.id} attempt={attempt} />) : <p>No attempt saved yet.</p>}</section>
      </>}
    </>}
  </section>;
}

function AttemptCard({ attempt }: { attempt: PracticeAttempt }) {
  const feedback = effectivePracticeFeedback(attempt);
  const superseded = attempt.assessment?.status === 'superseded';
  const pendingReview = feedback.outcome === 'pending_review';
  const historical = isHistoricalLexicalFeedback(attempt);
  const label = superseded ? 'Assessment superseded' : pendingReview ? 'Pending review' : historical ? `Historical keyword result: ${titleCase(feedback.outcome)}` : titleCase(feedback.outcome);
  return <article className="record stack"><div className="record-header"><h3>{label}</h3><span className="secondary">{new Date(attempt.created_at).toLocaleString()}</span></div><p className="source-passage">{attempt.response.text || (attempt.response.value !== null ? `${attempt.response.value} ${attempt.response.unit}` : attempt.response.selection.join(', '))}</p><p>{feedback.message}</p>{!pendingReview && !superseded && feedback.error_categories.length > 0 && <p>Review: {feedback.error_categories.map(titleCase).join(', ')}</p>}{!pendingReview && !superseded && feedback.missing_point_ids.length > 0 && <p className="secondary">Knowledge points to revisit: {feedback.missing_point_ids.join(', ')}</p>}<p className="secondary">{superseded ? 'This assessment belongs to an earlier practice state and did not change your current step.' : pendingReview ? 'Your work is saved. This attempt has no grade and does not complete the step.' : feedback.grading_method === 'model_assessment_v1' ? 'Model assessment against the saved question and textbook source.' : historical ? 'Earlier keyword rules produced this historical feedback.' : 'Checked with the saved question’s choice or number rules.'}</p></article>;
}

function ReviewAttemptSummary({ item }: { item: ReviewItem }) {
  const totals = typeof item.graded_count === 'number' && typeof item.pending_count === 'number'
    ? `${item.correct_count} correct of ${item.graded_count} graded attempts · ${item.pending_count} pending review`
    : `${item.attempt_count} saved attempts · Grading totals unavailable`;
  return <>{Object.entries(item.recent_error_counts || {}).map(([category, count]) => <p key={category}>{typeof item.recent_graded_count === 'number' ? `${count} of ${item.recent_graded_count} recent graded attempts` : `${count} recent recorded errors`}: {titleCase(category)}</p>)}<p className="secondary">{totals} · {item.concepts.join(' · ')}</p>{typeof item.recent_pending_count === 'number' && item.recent_pending_count > 0 && <p className="secondary">{item.recent_pending_count} recent attempts pending review.</p>}</>;
}

export function ReviewQueue({ go }: { go: (path: string) => void }) {
  const [dueOnly, setDueOnly] = useState(true);
  const [revealed, setRevealed] = useState<string[]>([]);
  const result = useLearningResource<ReviewItem[]>(`/learning/review?due_only=${dueOnly}`);
  const [busy, setBusy] = useState<string | null>(null); const [error, setError] = useState<unknown>(null); const [notice, setNotice] = useState('');
  const reschedule = async (item: ReviewItem, days: number) => { if (busy) return; setBusy(item.id); setError(null); setNotice(''); try { await post(`/learning/review/${encodeURIComponent(item.id)}/reschedule`, { days, expected_version: item.version }); setRevealed(current => current.filter(id => id !== item.id)); result.reload(); } catch (caught) { setError(caught); } finally { setBusy(null); } };
  const record = async (item: ReviewItem, outcome: 'recalled' | 'needs_review') => { if (busy) return; setBusy(item.id); setError(null); setNotice(''); try { await post(`/learning/review/${encodeURIComponent(item.id)}/record`, { expected_version: item.version, outcome }); setRevealed(current => current.filter(id => id !== item.id)); setNotice(outcome === 'recalled' ? 'Recall recorded.' : 'Another review recorded.'); result.reload(); } catch (caught) { setError(caught); } finally { setBusy(null); } };
  return <section className="stack"><h1>Review</h1><label className="inline-check"><input type="checkbox" checked={dueOnly} onChange={event => setDueOnly(event.target.checked)} />Due today only</label><p className="page-intro">Return to questions and personal cards when they are due. The queue explains when and why each item returns.</p><ErrorNotice error={result.error || error} action={<Button onClick={result.reload}>Reload review queue</Button>} />{notice && <p role="status" className="saved">{notice}</p>}{result.loading && <Loading>Loading your review queue…</Loading>}{result.data?.length === 0 && <p>No review items are scheduled.</p>}{result.data?.map(item => <article className="record stack" key={item.id}><div className="record-header"><h2>{item.title}</h2><span>{new Date(item.due_at) <= new Date() ? 'Due now' : `Due ${new Date(item.due_at).toLocaleDateString()}`}</span></div><p>{item.scheduling_reason}</p>{item.target_type === 'personal_review_card' ? <><p className="secondary">Personal review card{item.concepts.length ? ` · ${item.concepts.join(' · ')}` : ''}</p><p>Recall your note before revealing it. Your response is a self-report.</p><div className="form-actions"><Button disabled={busy === item.id} onClick={() => setRevealed(current => current.includes(item.id) ? current.filter(id => id !== item.id) : [...current, item.id])}>{revealed.includes(item.id) ? 'Hide my note' : 'Reveal my note'}</Button>{item.note_id && <Button onClick={() => go(`/learn/notes/${encodeURIComponent(item.note_id!)}`)}>Open note</Button>}{item.card_source && <Button onClick={() => go(`/learn/library/${encodeURIComponent(item.card_source!.document_id)}/unit/${encodeURIComponent(item.card_source!.source_unit_id)}`)}>Read source</Button>}</div>{revealed.includes(item.id) && <><div className="source-passage"><SafeMarkdown text={item.card_content?.trim() ? item.card_content : 'This card has no content yet. Open the note to add your own prompt and answer.'} /></div>{item.card_content?.trim() && <div className="form-actions"><Button className="primary" disabled={!!busy} onClick={() => record(item, 'recalled')}>I recalled it</Button><Button disabled={!!busy} onClick={() => record(item, 'needs_review')}>I need another review</Button></div>}</>}</> : <><ReviewAttemptSummary item={item} />{item.error_categories.length > 0 && <p>{item.error_categories.map(titleCase).join(', ')}</p>}{(item.suggested_item_id || item.item_id) && <div className="form-actions"><Button className="primary" onClick={() => go(`/learn/practice/${encodeURIComponent((item.suggested_item_id || item.item_id)!)}`)}>{item.suggested_item_id && item.suggested_item_id !== item.item_id ? 'Try a related question' : 'Review this question'}</Button></div>}</>}<div className="form-actions"><Button disabled={!!busy} onClick={() => reschedule(item, 1)}>Remind me tomorrow</Button><Button disabled={!!busy} onClick={() => reschedule(item, 7)}>In one week</Button></div></article>)}</section>;
}
