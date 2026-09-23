import { useEffect, useRef, useState, type FormEvent } from 'react';
import { BookOpen, Check, Pencil, Trash2 } from 'lucide-react';
import { patch, post, request } from './api';
import { Button, ErrorNotice, Loading, Modal, titleCase } from './components';
import type { MemoryEntry, MemoryNotice, MemorySettings, MemorySource, MemorySummary, MemoryProcessing, LearnerStatePreview } from './learning-types';

const memoryPath = (id: string) => `/me/memories/${encodeURIComponent(id)}`;

export function MemoryPage() {
  const [settings, setSettings] = useState<MemorySettings | null>(null);
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState('');
  const [editing, setEditing] = useState<MemoryEntry | null>(null);
  const [deleting, setDeleting] = useState<MemoryEntry | null>(null);
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [summary, setSummary] = useState<MemorySummary | null>(null);
  const [processing, setProcessing] = useState<MemoryProcessing[]>([]);
  const [overviewError, setOverviewError] = useState<unknown>(null);
  const generation = useRef(0);
  const refreshOverview = async (current = generation.current) => {
    try {
      const [overview, stages] = await Promise.all([request<MemorySummary>('/me/memory/summary'), request<MemoryProcessing[]>('/me/memory/processing')]);
      if (current === generation.current) { setSummary(overview); setProcessing(stages); setOverviewError(null); }
    } catch (caught) { if (current === generation.current) { setSummary(null); setOverviewError(caught); } }
  };

  const load = async () => {
    const current = ++generation.current; setLoading(true); setError(null);
    try {
      const [nextSettings, nextEntries] = await Promise.all([
        request<MemorySettings>('/me/memory/settings'), request<MemoryEntry[]>('/me/memories'),
      ]);
      if (current === generation.current) { setSettings(nextSettings); setEntries(nextEntries.filter(item => item.status !== 'deleted')); await refreshOverview(current); }
    } catch (caught) { if (current === generation.current) setError(caught); }
    finally { if (current === generation.current) setLoading(false); }
  };
  useEffect(() => { void load(); return () => { generation.current++; }; }, []);

  const toggle = async () => {
    if (!settings || busy) return;
    setBusy(true); setError(null); setNotice('');
    try {
      const saved = await patch<MemorySettings>('/me/memory/settings', { enabled: !settings.enabled, version: settings.version });
      setSettings(saved); setNotice(saved.enabled ? 'Learning memory enabled.' : 'Learning memory disabled. Saved entries remain available to manage.');
      await refreshOverview();
    } catch (caught) { setError(caught); }
    finally { setBusy(false); }
  };
  const remove = async () => {
    if (!deleting || busy) return;
    setBusy(true); setError(null);
    try {
      await request(memoryPath(deleting.id), { method: 'DELETE', body: JSON.stringify({ version: deleting.version }) });
      setEntries(items => items.filter(item => item.id !== deleting.id)); setDeleting(null);
      setNotice('Memory deleted. Its original chat message is unchanged.');
      await refreshOverview();
    } catch (caught) { setError(caught); }
    finally { setBusy(false); }
  };

  return <div className="content-page settings-page"><span className="eyebrow">Your learning experience</span><h1>Learning memory</h1>
    <p className="page-intro">Keep learning preferences, goals and attributable observations across conversations. Inspect, correct or erase each saved entry.</p>
    <ErrorNotice error={error} action={<Button disabled={busy} onClick={load}>Reload memory</Button>} />
    {loading ? <Loading>Loading your learning memory…</Loading> : <>
      {settings && <section className="memory-settings"><label className="inline-check"><input type="checkbox" checked={settings.enabled} disabled={busy} onChange={toggle} /><strong>Use learning memory</strong></label>
        <p className="secondary">When enabled, explicit lasting statements can be saved. A request for this turn stays temporary. Turning your profile off also disables memory for that turn.</p>
        <p className="secondary">Your current request takes priority. A relevant subject preference overrides a global setting. Observations describe their recorded evidence; a single result does not establish mastery.</p>
      </section>}
      {notice && <p className="saved" role="status"><Check size={17} />{notice}</p>}
      <ErrorNotice error={overviewError} action={<Button disabled={busy} onClick={() => { void refreshOverview(); }}>Refresh memory overview</Button>} />
      {summary && summary.enabled === settings?.enabled && <section className="stack"><h2>Memory summary</h2><p className="secondary">{summary.active_count} active {summary.active_count === 1 ? 'entry' : 'entries'} · {summary.enabled ? 'Available for relevant questions' : 'Not used while disabled'}</p><p className="source-passage">{summary.summary || 'No active learning memories.'}</p></section>}
      <MemoryPreview enabled={Boolean(settings?.enabled)} onSource={setSourceId} revision={summary?.version || ''} />
      {processing.length > 0 && <details><summary>Recent memory processing</summary><div className="record-list">{processing.map(stage => <article className="record" key={stage.event_id}><strong>{titleCase(stage.status.replaceAll('_', ' '))}</strong><p className="secondary">{new Date(stage.created_at).toLocaleString()} · Event {stage.sequence}</p>{stage.operations.map((operation, index) => <p key={index}>{titleCase((operation.operation || 'NO_OP').replaceAll('_', ' '))}: {titleCase((operation.reason || 'unchanged').replaceAll('_', ' '))}</p>)}{stage.error && <p role="alert">{stage.error.code}: {stage.error.message}</p>}</article>)}</div></details>}
      <div className="section-heading"><h2>Saved entries</h2><Button onClick={load} disabled={busy}>Refresh</Button></div>
      {!entries.length ? <p className="secondary">No learning memories saved.</p> : <div className="record-list">{entries.map(entry => <article key={entry.id} className="record memory-entry">
        <div className="record-header"><h3>{titleCase(entry.category.replaceAll('_', ' '))}</h3><span className="record-status">{titleCase(entry.status)}</span></div>
        <p className="memory-content">{entry.content}</p>
        <p className="secondary">Scope: {entry.scope} · Revision {entry.version}{entry.expires_at ? ` · Expires ${new Date(entry.expires_at).toLocaleString()}` : ''}</p>
        <p className="secondary">Updated {new Date(entry.updated_at).toLocaleString()}</p>
        <p className="secondary">{titleCase((entry.verification || 'legacy_unverified').replaceAll('_', ' '))}{entry.field_key ? ` · ${titleCase(entry.field_key.replaceAll('_', ' '))}` : ' · Edit to confirm a typed field before use'}</p>
        {entry.category === 'assessment_performance' && <p className="secondary">This records one assessment. Its evidence and scoring basis remain separate from broader proficiency.</p>}
        {entry.provenance && Object.keys(entry.provenance).length > 0 && <details><summary>Evidence and verification</summary><dl className="metadata">{Object.entries(entry.provenance).map(([key, value]) => <div key={key}><dt>{titleCase(key.replaceAll('_', ' '))}</dt><dd className="source-passage">{typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}</dd></div>)}</dl></details>}
        <div className="record-actions"><Button disabled={!entry.source_message_id || busy} onClick={() => setSourceId(entry.id)}><BookOpen size={16} />View source message</Button><Button disabled={busy} onClick={() => setEditing(entry)}><Pencil size={16} />Edit</Button><Button disabled={busy} onClick={() => { setError(null); setDeleting(entry); }}><Trash2 size={16} />Delete</Button></div>
      </article>)}</div>}
    </>}
    {editing && <MemoryEditor entry={editing} onClose={() => setEditing(null)} onSaved={saved => { setEntries(items => items.map(item => item.id === saved.id ? saved : item)); setEditing(null); setNotice('Memory updated.'); void refreshOverview(); }} />}
    {sourceId && <MemorySourceViewer memoryId={sourceId} onClose={() => setSourceId(null)} />}
    {deleting && <Modal title="Delete this memory?" onClose={() => { if (!busy) setDeleting(null); }}><div className="stack"><p>The saved memory and its derived content will be removed. This action keeps the original chat message and cannot restore the deleted memory.</p><ErrorNotice error={error} /><div className="form-actions"><Button className="primary" disabled={busy} onClick={remove}>{busy ? 'Deleting…' : 'Delete memory'}</Button><Button disabled={busy} onClick={() => setDeleting(null)}>Keep memory</Button></div></div></Modal>}
  </div>;
}

function MemoryPreview({ enabled, onSource, revision }: {enabled: boolean; onSource: (id: string) => void; revision: string}) {
  const [question, setQuestion] = useState(''); const [profile, setProfile] = useState(true);
  const [state, setState] = useState<LearnerStatePreview | null>(null); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  const epoch = useRef(0);
  useEffect(() => { epoch.current++; setState(null); }, [enabled, revision]);
  const preview = async (event: FormEvent) => {
    event.preventDefault(); if (busy) return; setBusy(true); setError(null); const current = epoch.current;
    try { const result = await post<LearnerStatePreview>('/me/memory/preview', {question: question.trim(), use_profile: profile}); if (epoch.current === current) setState(result); }
    catch (caught) { if (epoch.current === current) setError(caught); } finally { setBusy(false); }
  };
  return <details><summary>Preview memory for a question</summary><form className="stack" onSubmit={preview}><p className="secondary">Inspect applicable learner state without saving memory or calling an answer model.</p><label>Question for memory preview<textarea rows={2} required maxLength={4000} value={question} onChange={event => { epoch.current++; setQuestion(event.target.value); setState(null); }} /></label><label className="inline-check"><input type="checkbox" checked={profile} onChange={event => { epoch.current++; setProfile(event.target.checked); setState(null); }} />Use profile for this preview</label><Button type="submit" disabled={busy || !enabled || !question.trim()}>{busy ? 'Preparing preview…' : 'Preview learner state'}</Button><ErrorNotice error={error} />{state && enabled && <div className="stack" aria-live="polite"><p>{state.enabled ? `Topics: ${state.query_topics.join(', ') || 'No subject identified'}` : 'Memory is not used for this preview.'}</p>{state.fields.length === 0 && <p>No applicable memory fields.</p>}{state.fields.map((field, index) => <article className="record" key={index}><strong>{titleCase(field.field_key.replaceAll('_', ' '))}</strong><p>{field.content || state.entries.find(entry => entry.id === field.source.memory_id)?.content || 'Current request instruction'}</p><p className="secondary">{field.scope} · {titleCase(field.verification.replaceAll('_', ' '))}</p>{field.source.memory_id && <Button type="button" onClick={() => onSource(field.source.memory_id!)}>Inspect source</Button>}</article>)}{state.excluded.length > 0 && <p className="secondary">Excluded: {state.excluded.map(item => titleCase(item.reason.replaceAll('_', ' '))).join('; ')}</p>}</div>}</form></details>;
}

function MemoryEditor({ entry, onSaved, onClose }: { entry: MemoryEntry; onSaved: (entry: MemoryEntry) => void; onClose: () => void }) {
  const [content, setContent] = useState(entry.content || ''); const [scope, setScope] = useState(entry.scope);
  const [field, setField] = useState(entry.field_key || '');
  const fields = entry.category === 'preference' ? ['detail_level', 'explanation_order', 'examples', 'analogies', 'terminology', 'format'] : entry.category === 'goal' ? ['learning_goal'] : entry.category === 'course_context' ? ['course'] : entry.category === 'self_reported_observation' ? ['difficulty', 'confidence'] : entry.category === 'assessment_performance' ? ['assessment_result'] : [];
  const [expiry, setExpiry] = useState(entry.expires_at?.slice(0, 10) || '');
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  const save = async (event: FormEvent) => {
    event.preventDefault(); if (busy) return; setBusy(true); setError(null);
    try { onSaved(await patch<MemoryEntry>(memoryPath(entry.id), { version: entry.version, content: content.trim(), scope: scope.trim(), expires_at: expiry === (entry.expires_at?.slice(0, 10) || '') ? entry.expires_at : expiry ? new Date(`${expiry}T23:59:59Z`).toISOString() : null, ...(field ? {field_key: field} : {}) })); }
    catch (caught) { setError(caught); } finally { setBusy(false); }
  };
  return <Modal title="Edit learning memory" onClose={() => { if (!busy) onClose(); }}><form className="stack" onSubmit={save}><label>Memory<textarea required maxLength={2000} rows={5} value={content} onChange={e => setContent(e.target.value)} /></label>{fields.length > 0 && <label>Memory field<select value={field} onChange={event => setField(event.target.value)}><option value="">Use the recognized field</option>{fields.map(value => <option key={value} value={value}>{titleCase(value.replaceAll('_', ' '))}</option>)}</select></label>}<label>Scope<input required maxLength={200} value={scope} onChange={e => setScope(e.target.value)} /><small>Use global for a lasting preference, or name its subject or goal.</small></label><label>Expiry date (optional)<input type="date" value={expiry} onChange={e => setExpiry(e.target.value)} /></label><p className="secondary">Editing revision {entry.version}. A newer revision must be reloaded before saving.</p>{entry.category === 'assessment_performance' && <p className="secondary">Editing an assessment changes its status to recorded, unconfirmed. Its prior score does not verify your correction.</p>}<ErrorNotice error={error} /><Button type="submit" className="primary" disabled={busy || !content.trim() || !scope.trim()}>{busy ? 'Saving…' : 'Save memory'}</Button></form></Modal>;
}

function MemorySourceViewer({ memoryId, onClose }: { memoryId: string; onClose: () => void }) {
  const [source, setSource] = useState<MemorySource | null>(null); const [error, setError] = useState<unknown>(null);
  useEffect(() => { let current = true; request<MemorySource>(`${memoryPath(memoryId)}/source`).then(value => { if (current) setSource(value); }).catch(caught => { if (current) setError(caught); }); return () => { current = false; }; }, [memoryId]);
  return <Modal title="Memory source message" onClose={onClose}><ErrorNotice error={error} />{source ? <p className="source-passage">{source.content}</p> : !error && <Loading>Loading the original message…</Loading>}</Modal>;
}

export function MemorySavedNotice({ memoryId, version, onRemoved }: { memoryId: string; version: number; onRemoved?: () => void }) {
  const [removed, setRemoved] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  const undo = async () => {
    if (busy) return; setBusy(true); setError(null);
    try { await post(`${memoryPath(memoryId)}/undo`, { version }); setRemoved(true); onRemoved?.(); }
    catch (caught) { setError(caught); } finally { setBusy(false); }
  };
  return <div className="memory-notice"><p role="status">{removed ? 'Saved memory removed.' : 'A learning preference or goal was saved.'}</p>{!removed && <Button disabled={busy} onClick={undo}>{busy ? 'Removing…' : 'Undo memory save'}</Button>}<ErrorNotice error={error} /></div>;
}

export function SessionMemoryNotices({ sessionId, messageId, excludedIds = [] }: { sessionId: string; messageId: string; excludedIds?: string[] }) {
  const [notices, setNotices] = useState<MemoryNotice[]>([]); const [error, setError] = useState<unknown>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let cancelled = false; let timer: ReturnType<typeof setTimeout>; let reads = 0;
    setNotices([]); setError(null);
    const refresh = async () => {
      try {
        const saved = await request<MemoryNotice[]>(`/sessions/${encodeURIComponent(sessionId)}/memory-notices`);
        if (cancelled) return;
        setNotices(saved.filter(notice => notice.source_message_id === messageId && notice.action === 'undo_save')); setError(null);
        // Memory extraction has its own bounded job and can finish after the answer.
        if (++reads < 20 && !saved.some(notice => notice.source_message_id === messageId)) timer = setTimeout(refresh, 5000);
      } catch (caught) { if (!cancelled) setError(caught); }
    };
    void refresh(); return () => { cancelled = true; clearTimeout(timer); };
  }, [sessionId, messageId, retry]);
  return <>{notices.filter(notice => !excludedIds.includes(notice.memory_id)).map(notice => <MemorySavedNotice key={`${notice.memory_id}:${notice.version}`} memoryId={notice.memory_id} version={notice.version} onRemoved={() => setNotices(items => items.filter(item => item.memory_id !== notice.memory_id))} />)}<ErrorNotice error={error} action={<Button onClick={() => setRetry(value => value + 1)}>Refresh memory status</Button>} /></>;
}
