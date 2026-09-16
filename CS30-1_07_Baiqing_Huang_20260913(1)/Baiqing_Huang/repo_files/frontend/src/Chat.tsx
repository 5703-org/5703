import { useCallback, useEffect, useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Archive, ArrowDown, ArrowUp, BookOpen, Check, Copy, ExternalLink, Lightbulb, MessageCircle, MoreHorizontal, Pencil, RotateCcw, Square, ThumbsDown, ThumbsUp } from 'lucide-react';
import { api, ApiError, errorText, patch, post, put } from './api';
import { Button, DataDetails, ErrorNotice, IconButton, Loading, Modal, titleCase } from './components';
import { SafeMarkdown } from './Markdown';
import { responseSources, sourceLocator } from './sources';
import type { Answer, Capabilities, ChatResponse, Evidence, Feedback, Job, JobReceipt, MCQResponse, Message, Profile, Session } from './types';

const activeStates = new Set(['queued', 'running', 'retry_wait']);
const stages: Record<string, string> = { queued: 'Waiting to begin…', preparing: 'Understanding your question…', retrieving: 'Looking through the sources…', generating: 'Preparing an explanation…', saving: 'Saving your response…', retry_wait: 'Waiting to try again…', processing: 'Working on your question…' };
const draftKey = (userId: string, sessionId?: string) => `cs30.draft.${userId}.${sessionId || 'new'}`;
const pendingKey = (userId: string, sessionId: string) => `cs30.pending.${userId}.${sessionId}`;

export function Chat({ sessionId, navigating = false, userId, profile, capabilities, onCreated, refreshSessions, onOverlay }: { sessionId?: string; navigating?: boolean; userId: string; profile: Profile | null; capabilities: Capabilities | null; onCreated: (id: string) => void; refreshSessions: () => Promise<void>; onOverlay: (open: boolean) => void }) {
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState(() => sessionStorage.getItem(draftKey(userId, sessionId)) || '');
  const draftRef = useRef(draft); draftRef.current = draft;
  const [useProfile, setUseProfile] = useState(true);
  const [loading, setLoading] = useState(!!sessionId);
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [pollError, setPollError] = useState<unknown>(null);
  const [evidenceTarget, setEvidenceTarget] = useState<{ answer: Answer; evidenceId?: string } | null>(null);
  const [feedbackTarget, setFeedbackTarget] = useState<Answer | null>(null);
  const [menu, setMenu] = useState(false);
  const [rename, setRename] = useState(false);
  const [renameTitle, setRenameTitle] = useState('');
  const [jumpVisible, setJumpVisible] = useState(false);
  const transcript = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const nearBottom = useRef(true);
  const mounted = useRef(true);
  const pendingSubmission = useRef<{ signature: string; key: string } | null>(null);
  const lifecycleKey = useRef<{ path: string; key: string } | null>(null);
  const createdSession = useRef<string | null>(null);
  const working = navigating || submitting || !!jobId;
  const readonly = session?.status === 'archived' || session?.status === 'deleted';
  useEffect(() => () => { mounted.current = false; onOverlay(false); }, []);
  useEffect(() => { sessionStorage.setItem(draftKey(userId, sessionId), draft); }, [draft, userId, sessionId]);
  useEffect(() => { onOverlay(!!evidenceTarget || !!feedbackTarget || rename); }, [evidenceTarget, feedbackTarget, rename, onOverlay]);
  useLayoutEffect(() => { if (textarea.current) { textarea.current.style.height = 'auto'; textarea.current.style.height = `${textarea.current.scrollHeight}px`; } }, [draft]);

  const loadTranscript = useCallback(async () => {
    if (!sessionId) return;
    const current = await api.session(sessionId);
    let after = 0; const items: Message[] = []; let active: string | null = null; let latest: string | null = null;
    while (true) {
      const page = await api.messages(sessionId, after); items.push(...page.items); active = page.active_job_id; latest = page.latest_job_id;
      if (page.next_after_sequence === null) break;
      if (page.next_after_sequence <= after) throw new Error('History pagination did not advance. Please reload this conversation.');
      after = page.next_after_sequence;
    }
    if (mounted.current) { setSession(current); setMessages(items); setJobId(accepted => active || accepted); }
    if (!active && latest) {
      const historicalJob = await api.job(latest);
      if (mounted.current) { setJob(historicalJob); if (activeStates.has(historicalJob.state)) setJobId(historicalJob.id); }
    }
  }, [sessionId]);
  useEffect(() => { if (!sessionId) return; loadTranscript().catch(setError).finally(() => setLoading(false)); }, [loadTranscript, sessionId]);
  useLayoutEffect(() => {
    if (nearBottom.current && transcript.current) transcript.current.scrollTop = transcript.current.scrollHeight;
    else if (messages.length) setJumpVisible(true);
  }, [messages, job?.stage, job?.state, submitting, error, pollError]);

  useEffect(() => {
    if (!jobId || !sessionId) return;
    let cancelled = false; let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const current = await api.job(jobId); if (cancelled || !mounted.current) return;
        setJob(current); setPollError(null);
        if (!activeStates.has(current.state)) {
          if (current.state === 'failed' || current.state === 'cancelled') {
            const previous = sessionStorage.getItem(pendingKey(userId, sessionId));
            if (previous && !draftRef.current) setDraft(previous);
          }
          sessionStorage.removeItem(pendingKey(userId, sessionId));
          setJobId(null); await loadTranscript(); await refreshSessions(); return;
        }
      } catch (caught) { if (cancelled) return; setPollError(caught); }
      if (!cancelled) timer = setTimeout(poll, 750);
    };
    void poll(); return () => { cancelled = true; clearTimeout(timer); };
  }, [jobId, sessionId, loadTranscript, refreshSessions, userId]);

  const send = async (content = draft) => {
    if (!content.trim() || submittingRef.current || jobId || readonly || navigating) return;
    if (content.trim().length > 4000) { setError(new Error('Please keep your message to 4,000 characters or fewer.')); return; }
    submittingRef.current = true; setSubmitting(true); setError(null); nearBottom.current = true;
    let targetSession = sessionId || createdSession.current || undefined;
    try {
      if (!targetSession) { const created = await post<Session>('/sessions', { title: 'New chat' }); targetSession = created.id; createdSession.current = created.id; }
      const signature = JSON.stringify([targetSession, content.trim(), useProfile]);
      if (pendingSubmission.current?.signature !== signature) pendingSubmission.current = { signature, key: crypto.randomUUID() };
      const receipt = await api.send(targetSession, content.trim(), useProfile, pendingSubmission.current!.key);
      sessionStorage.setItem(pendingKey(userId, targetSession), content);
      sessionStorage.setItem(draftKey(userId, targetSession), '');
      setDraft(''); setJob(null); setJobId(receipt.job_id); pendingSubmission.current = null;
      if (!sessionId) onCreated(targetSession); else { await loadTranscript(); await refreshSessions(); }
    } catch (caught) { if (mounted.current) { setError(caught); if (!draftRef.current) setDraft(content); } }
    finally { submittingRef.current = false; if (mounted.current) { setSubmitting(false); textarea.current?.focus(); } }
  };
  const runLifecycle = async (path: string) => {
    if (submittingRef.current || jobId) return;
    submittingRef.current = true; setSubmitting(true); setError(null);
    try {
      if (lifecycleKey.current?.path !== path) lifecycleKey.current = { path, key: crypto.randomUUID() };
      const receipt = await post<JobReceipt>(path, {}, lifecycleKey.current.key);
      lifecycleKey.current = null; setJob(null); setJobId(receipt.job_id); await loadTranscript();
    } catch (caught) { setError(caught); } finally { submittingRef.current = false; setSubmitting(false); }
  };
  const stop = async () => { if (!jobId) return; try { const value = await post<Job>(`/jobs/${jobId}/cancel`); setJob(value); await loadTranscript(); } catch (caught) { setError(caught); } };
  const keyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) { event.preventDefault(); void send(); } };
  const archive = async () => { if (!sessionId) return; setMenu(false); try { const value = await post<Session>(`/sessions/${sessionId}/${readonly ? 'restore' : 'archive'}`); setSession(value); await refreshSessions(); await loadTranscript(); } catch (caught) { setError(caught); } };
  const submitRename = async (event: FormEvent) => { event.preventDefault(); if (!session) return; try { setSession(await patch<Session>(`/sessions/${session.id}`, { title: renameTitle.trim(), version: session.version })); setRename(false); await refreshSessions(); } catch (caught) { setError(caught); } };
  const lastUser = messages.filter(item => item.role === 'user').at(-1);
  const failedTail = lastUser && ['error', 'failed', 'cancelled'].includes(lastUser.state) && !messages.some(item => item.role === 'assistant' && item.sequence > lastUser.sequence && item.answer);
  return <div className="chat-workspace">
    {session && <div className="conversation-heading"><h1 title={session.title}>{session.title}</h1><div className="conversation-menu"><IconButton label="Conversation actions" aria-expanded={menu} onClick={() => setMenu(!menu)}><MoreHorizontal size={20} /></IconButton>{menu && <div className="popover"><Button onClick={() => { setRenameTitle(session.title); setRename(true); setMenu(false); }}><Pencil size={16} />Rename</Button><Button onClick={archive}><Archive size={16} />{readonly ? 'Restore conversation' : 'Archive conversation'}</Button></div>}</div></div>}
    <div ref={transcript} className="transcript" data-testid="transcript" onScroll={() => { const el = transcript.current!; nearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80; setJumpVisible(!nearBottom.current); }}>
      <div className="reading-column">
        {loading ? <Loading>Loading this conversation…</Loading> : messages.length === 0 ? <div className="chat-welcome"><div className="welcome-mark"><BookOpen size={26} strokeWidth={1.5} /></div><span className="eyebrow">Follow your curiosity</span><h1>What would you like<br className="welcome-break" /> to understand?</h1><p>Start with a question. We’ll explore it together,<br className="desktop-break" /> with explanations and sources you can inspect.</p><div className="starter-prompts"><Button onClick={() => { setDraft('What is photosynthesis?'); textarea.current?.focus(); }}><Lightbulb size={18} /><span>Explain a concept<small>What is photosynthesis?</small></span><ArrowUp size={15} /></Button><Button onClick={() => { setDraft('How are plant and animal cells different?'); textarea.current?.focus(); }}><MessageCircle size={18} /><span>Connect the ideas<small>Compare plant and animal cells</small></span><ArrowUp size={15} /></Button></div></div> : <div className="messages">{messages.map(message => message.role === 'user' ? <article key={message.id} className="message user-message" data-message-id={message.id}><span className="sr-only">You</span><div className="user-bubble">{message.content}</div>{['error', 'failed', 'cancelled'].includes(message.state) && <span className="message-state">{message.state === 'cancelled' ? 'Generation stopped' : 'Response failed'}</span>}</article> : <article className="message assistant-message" key={message.id} data-message-id={message.id} data-answer-id={message.active_answer_id || undefined}><div className="assistant-label"><BookOpen size={17} />Learning Assistant</div>{message.answer ? <AnswerView answer={message.answer} working={working} onEvidence={evidenceId => setEvidenceTarget({ answer: message.answer!, evidenceId })} onFeedback={() => setFeedbackTarget(message.answer!)} onRegenerate={() => runLifecycle(`/answers/${message.answer!.id}/regenerate`)} onSuggestion={text => { setDraft(text); void send(text); }} /> : <p>{message.content || 'This response is not available.'}</p>}</article>)}</div>}
        {working && <div className="generation-status" aria-live="polite"><Loading>{submitting && !jobId ? 'Sending your question…' : stages[job?.stage || 'queued'] || `${titleCase(job?.stage || 'queued')}…`}</Loading></div>}
        {job && ['failed', 'cancelled'].includes(job.state) && <div className="job-terminal" role="status"><p>{job.state === 'cancelled' ? 'Generation stopped. Your conversation is saved.' : 'The response could not be completed.'}</p>{job.error && <ErrorNotice error={new ApiError(job.error.code, job.error.message)} />}{job.can_retry && !working && <Button onClick={() => runLifecycle(`/answer-requests/${job.request_id}/retry`)}><RotateCcw size={16} />Retry response</Button>}</div>}
        {failedTail && !working && !job && <div className="job-terminal"><p>This question has no completed response.</p><Button onClick={() => runLifecycle(`/answer-requests/${lastUser!.request_id}/retry`)}><RotateCcw size={16} />Retry response</Button></div>}
        <ErrorNotice error={pollError} /><ErrorNotice error={error} action={loading ? <Button onClick={() => { setLoading(true); loadTranscript().then(() => setError(null)).catch(setError).finally(() => setLoading(false)); }}>Reload conversation</Button> : undefined} />
      </div>
    </div>
    {jumpVisible && <div className="jump-row"><Button onClick={() => { if (transcript.current) transcript.current.scrollTop = transcript.current.scrollHeight; nearBottom.current = true; setJumpVisible(false); }}><ArrowDown size={16} />Jump to latest</Button></div>}
    <div className="composer-region"><div className="composer-column">{readonly ? <div className="archived-notice"><Archive size={18} /><p>This conversation is archived.</p><Button onClick={archive}>Restore to continue</Button></div> : <form className="composer" onSubmit={event => { event.preventDefault(); void send(); }}><label className="sr-only" htmlFor="chat-composer">Message Learning Assistant</label><textarea ref={textarea} disabled={navigating} id="chat-composer" rows={1} placeholder="Ask a question, or explore an idea…" value={draft} onChange={event => { setDraft(event.target.value); setError(null); }} onKeyDown={keyDown} aria-describedby="composer-help" /><div className="composer-toolbar"><label className="profile-toggle"><input type="checkbox" checked={useProfile} onChange={e => setUseProfile(e.target.checked)} /><span>{useProfile ? `${titleCase(profile?.level || 'intermediate')} explanations` : 'Profile off'}</span></label><div className="send-area">{draft.length > 3600 && <span className={draft.length > 4000 ? 'error-text' : 'secondary'}>{draft.length}/4,000</span>}{jobId ? <IconButton label="Stop generation" className="primary send-button" onClick={stop}><Square size={17} fill="currentColor" /></IconButton> : <IconButton type="submit" label="Send message" className="primary send-button" disabled={!draft.trim() || submitting || navigating || draft.trim().length > 4000}><ArrowUp size={20} /></IconButton>}</div></div></form>}<p id="composer-help" className="composer-note">{capabilities?.model_mode === 'mock' ? 'Demo responses use a mock model. Check the sources and verify important details.' : 'Answers can be imperfect. Use the sources to check your understanding.'}</p></div></div>
    {evidenceTarget && <EvidenceViewer answer={evidenceTarget.answer} initialId={evidenceTarget.evidenceId} onClose={() => setEvidenceTarget(null)} />}
    {feedbackTarget && <FeedbackModal answer={feedbackTarget} onClose={() => setFeedbackTarget(null)} />}
    {rename && <Modal title="Rename conversation" onClose={() => setRename(false)}><form className="stack" onSubmit={submitRename}><label>Conversation title<input required maxLength={200} value={renameTitle} onChange={e => setRenameTitle(e.target.value)} autoFocus /></label><ErrorNotice error={error} /><Button type="submit" className="primary">Save title</Button></form></Modal>}
  </div>;
}

function AnswerView({ answer, working, onEvidence, onFeedback, onRegenerate, onSuggestion }: { answer: Answer; working: boolean; onEvidence: (id?: string) => void; onFeedback: () => void; onRegenerate: () => void; onSuggestion: (text: string) => void }) {
  const [copied, setCopied] = useState(false); const [copyError, setCopyError] = useState<unknown>(null);
  const isChat = answer.response_schema === 'chat_response_v1';
  const response = answer.response as ChatResponse;
  const legacy = answer.response as MCQResponse;
  const text = isChat ? response.answer_text : `${legacy.answer ? `${legacy.answer}. ${legacy.answer_text}\n\n` : ''}${legacy.short_explanation}`;
  const { ids: sourceIds, recorded: citationsRecorded } = responseSources(answer);
  const snapshot = answer.profile_snapshot;
  const nestedProfile = (snapshot?.profile || snapshot?.snapshot || snapshot) as Record<string, unknown> | null;
  const level = typeof nestedProfile?.level === 'string' ? titleCase(nestedProfile.level) : null;
  const copy = async () => { try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1800); } catch { setCopyError(new Error('Clipboard access is unavailable. Select the response text to copy it.')); } };
  return <><div className="answer-metadata"><span>{answer.model_mode === 'mock' ? 'Demo (mock model)' : 'Live model'}</span><span>·</span><span>{level ? `${level} profile applied` : 'Profile not applied'}</span>{isChat && response.response_type === 'refusal' && <span className="status-tag">Evidence limitation</span>}{isChat && response.response_type === 'clarification' && <span className="status-tag">A quick clarification</span>}{!isChat && <span className="status-tag">Historical MCQ result</span>}</div><SafeMarkdown text={text} evidence={answer.evidence} citationIds={sourceIds} onEvidence={onEvidence} /><div className="answer-actions">{sourceIds.length > 0 && <Button onClick={() => onEvidence()}><BookOpen size={16} />{citationsRecorded ? 'Sources' : 'Stored sources'} <span className="source-count">{sourceIds.length}</span></Button>}<Button onClick={copy}>{copied ? <Check size={16} /> : <Copy size={16} />}{copied ? 'Copied' : 'Copy'}</Button><Button onClick={onFeedback}><ThumbsUp size={16} />Feedback</Button>{answer.can_regenerate && <Button onClick={onRegenerate} disabled={working}><RotateCcw size={16} />Regenerate</Button>}</div><ErrorNotice error={copyError} />{isChat && response.follow_up_questions.length > 0 && <div className="followups" aria-label="Follow-up suggestions">{response.follow_up_questions.map(question => <Button disabled={working} key={question} onClick={() => onSuggestion(question)}>{question}<ArrowUp size={15} /></Button>)}</div>}<details className="applied-details"><summary>Applied preferences and response details</summary><DataDetails title="Profile snapshot" data={snapshot || { applied: false }} /><DataDetails title="Response record" data={{ answer_id: answer.id, request_id: answer.request_id, mode: answer.mode, response_schema: answer.response_schema, timing: answer.timing }} /></details></>;
}

function openStaxSourceUrl(sourceUrl?: string | null): string | null {
  if (!sourceUrl) return null;
  try {
    const url = new URL(sourceUrl);
    return url.protocol === 'https:' && !url.username && !url.password && (url.hostname === 'openstax.org' || url.hostname.endsWith('.openstax.org')) ? url.href : null;
  } catch { return null; }
}

export function EvidenceViewer({ answer, initialId, onClose }: { answer: Answer; initialId?: string; onClose: () => void }) {
  const { ids: sourceIds, recorded: citationsRecorded } = responseSources(answer);
  const [selected, setSelected] = useState(initialId && sourceIds.includes(initialId) ? initialId : sourceIds[0]);
  const [evidence, setEvidence] = useState<Evidence | null>(null); const [error, setError] = useState<unknown>(null); const [loading, setLoading] = useState(true);
  const originalSourceUrl = openStaxSourceUrl(evidence?.source_url);
  useEffect(() => { let cancelled = false; setLoading(true); setEvidence(null); setError(null); if (!selected) { setLoading(false); return; } api.evidence(answer.id, selected).then(value => { if (!cancelled) setEvidence(value); }).catch(caught => { if (!cancelled) setError(caught); }).finally(() => { if (!cancelled) setLoading(false); }); return () => { cancelled = true; }; }, [answer.id, selected]);
  return <Modal title="Sources" kind="evidence-modal" onClose={onClose}><p className="secondary">{citationsRecorded ? 'Sources cited in this response.' : 'Historical stored sources. Citation usage was not recorded for this response.'}</p>{sourceIds.length > 1 && <nav className="source-tabs" aria-label="Select source">{sourceIds.map((sourceId, i) => <Button className={selected === sourceId ? 'active' : ''} key={sourceId} onClick={() => setSelected(sourceId)}>Source {i + 1}</Button>)}</nav>}{loading ? <Loading>Loading the original passage…</Loading> : error ? <><h3>Source unavailable</h3><ErrorNotice error={error} /><p className="secondary">This response keeps its original citation. A different passage has not been substituted.</p></> : evidence ? <><span className="eyebrow">Original source passage</span><h3 className="source-title">{evidence.source_title}</h3><p className="source-locator">{sourceLocator(evidence)}</p>{originalSourceUrl && <div className="source-attribution"><p>OpenStax / Rice University · Access for free at openstax.org</p><a className="source-original-link" href={originalSourceUrl} target="_blank" rel="noopener noreferrer">View original source<ExternalLink size={15} aria-hidden="true" /></a></div>}<div className="source-passage">{evidence.text}</div><DataDetails data={{ request_id: answer.request_id, evidence_id: evidence.evidence_id, chunk_id: evidence.chunk_id, asset_id: evidence.asset_id, processing_id: evidence.processing_id, text_hash: evidence.text_hash, source_url: evidence.source_url, license: evidence.license, context_order: evidence.context_order, inherited_from: evidence.inherited_from }} /></> : <p>No sources were cited in this response.</p>}</Modal>;
}

function FeedbackModal({ answer, onClose }: { answer: Answer; onClose: () => void }) {
  const [feedback, setFeedback] = useState<Feedback>({ helpful: null, comment: '' }); const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false); const [saved, setSaved] = useState(false); const [error, setError] = useState<unknown>(null);
  useEffect(() => { api.feedback(answer.id).then(value => { if (value) setFeedback(value); }).catch(caught => { if (!(caught instanceof ApiError && caught.status === 404)) setError(caught); }).finally(() => setLoading(false)); }, [answer.id]);
  const save = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(null); try { const value = await put<Feedback>(`/answers/${answer.id}/feedback`, { helpful: feedback.helpful, comment: feedback.comment }); setFeedback(value); setSaved(true); } catch (caught) { setError(caught); } finally { setBusy(false); } };
  return <Modal title="Response feedback" onClose={onClose}>{loading ? <Loading>Loading saved feedback…</Loading> : <form className="stack" onSubmit={save}><p>Was this response helpful?</p><div className="feedback-options"><Button aria-pressed={feedback.helpful === true} className={feedback.helpful === true ? 'active' : ''} onClick={() => { setFeedback({ ...feedback, helpful: true }); setSaved(false); }}><ThumbsUp size={18} />Helpful</Button><Button aria-pressed={feedback.helpful === false} className={feedback.helpful === false ? 'active' : ''} onClick={() => { setFeedback({ ...feedback, helpful: false }); setSaved(false); }}><ThumbsDown size={18} />Not helpful</Button></div><label>Comment <span className="secondary">(optional)</span><textarea rows={5} maxLength={2000} value={feedback.comment} onChange={e => { setFeedback({ ...feedback, comment: e.target.value }); setSaved(false); }} placeholder="What was useful, unclear or worth checking?" /></label><ErrorNotice error={error} /><Button className="primary" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save feedback'}</Button>{saved && <p className="saved" role="status"><Check size={17} />Feedback saved for this response.</p>}</form>}</Modal>;
}
