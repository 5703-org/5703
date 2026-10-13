import { useEffect, useRef, useState, type FormEvent } from 'react';
import { OriginalPageModal } from './OriginalPage';
import { post, put } from './api';
import { Button, ErrorNotice, Loading } from './components';
import { passageSelection, sourceUrl, useLearningResource, type PassageSelection } from './learning-ui';
import type { ReadingContext } from './reading-context';
import type { Book, ReadingPage, ReadingPosition, ReadingUnit, Section } from './study-types';

export function StudyLibrary({ bookId, sectionId, unitId, go, onAsk }: { bookId?: string; sectionId?: string; unitId?: string; go: (path: string) => void; onAsk: (question: string, context: ReadingContext) => Promise<void> }) {
  const books = useLearningResource<Book[]>('/learning/library');
  const positions = useLearningResource<ReadingPosition[]>('/learning/reading-position');
  const book = books.data?.find(item => item.id === bookId);
  if (bookId) return <section className="stack"><Button onClick={() => go('/learn/library')}>All textbooks</Button><ErrorNotice error={books.error || positions.error} action={<Button onClick={() => { books.reload(); positions.reload(); }}>Reload textbooks</Button>} />{books.loading && <Loading>Opening textbook…</Loading>}{book && <BookReader key={`${book.id}:${sectionId || ''}:${unitId || ''}`} book={book} sectionId={sectionId} unitId={unitId} go={go} onAsk={onAsk} positions={positions.data || []} positionsReady={positions.data !== null && !positions.loading} refreshPositions={positions.reload} />}{books.data && !book && <p>This textbook is not available in the current published library.</p>}</section>;
  return <section className="stack"><div><span className="eyebrow">Read, question, understand</span><h1>Your textbook library</h1><p className="page-intro">Explore the published textbooks. Reading and practice keep separate records of your progress.</p></div><ErrorNotice error={books.error || positions.error} action={<Button onClick={() => { books.reload(); positions.reload(); }}>Reload library</Button>} />{books.loading && <Loading>Loading textbooks…</Loading>}{books.data?.length === 0 && <p>No textbooks are published yet.</p>}<div className="learning-cards">{books.data?.map(item => {
    const position = positions.data?.find(saved => saved.source.document_id === item.id && saved.source.release_id === item.release_id);
    return <article className="record book-card stack" key={item.id}><span className="book-monogram" aria-hidden="true">{item.title.slice(0, 1)}</span><div><h2>{item.title}</h2><p className="secondary">{item.edition} · {item.section_count} sections</p></div><p className="secondary">{item.license}</p><div className="form-actions"><Button className="primary" onClick={() => go(`/learn/library/${encodeURIComponent(item.id)}`)}>Open textbook</Button>{position && <Button onClick={() => go(`/learn/library/${encodeURIComponent(item.id)}/unit/${encodeURIComponent(position.source.source_unit_id)}`)}>Resume reading</Button>}</div>{position && <small>Reading place saved {new Date(position.updated_at).toLocaleDateString()}</small>}</article>;
  })}</div></section>;
}

function BookReader({ book, sectionId, unitId, go, onAsk, positions, positionsReady, refreshPositions }: { book: Book; sectionId?: string; unitId?: string; go: (path: string) => void; onAsk: (question: string, context: ReadingContext) => Promise<void>; positions: ReadingPosition[]; positionsReady: boolean; refreshPositions: () => void }) {
  const sections = useLearningResource<Section[]>(`/learning/library/${encodeURIComponent(book.id)}/sections`);
  const [filter, setFilter] = useState(''); const [offset, setOffset] = useState(0);
  const [seekUnit, setSeekUnit] = useState(unitId);
  const [view, setView] = useState<'contents' | 'reading' | 'question'>(unitId || sectionId ? 'reading' : 'contents');
  const params = new URLSearchParams({ offset: String(offset), limit: '20' }); if (sectionId) params.set('section_id', sectionId); if (seekUnit) params.set('source_unit_id', seekUnit);
  const page = useLearningResource<ReadingPage>(`/learning/library/${encodeURIComponent(book.id)}/units?${params}`);
  const [chosen, setChosen] = useState<{ unit: ReadingUnit; selection: PassageSelection } | null>(null);
  const [question, setQuestion] = useState(''); const [scope, setScope] = useState<ReadingContext['scope']>('chapter');
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null); const [notice, setNotice] = useState(''); const [originalPage, setOriginalPage] = useState<number | null>(null);
  const currentPosition = positions.find(item => item.source.document_id === book.id);
  const positionVersion = useRef(currentPosition?.version || 0);
  const positionKnown = useRef(false);
  const readingRestored = useRef(false);
  const resumePosition = currentPosition?.source.release_id === book.release_id && currentPosition.source.source_unit_id === unitId ? currentPosition : undefined;
  useEffect(() => {
    if (positionsReady) { positionVersion.current = Math.max(positionVersion.current, currentPosition?.version || 0); positionKnown.current = true; }
  }, [currentPosition, positionsReady]);
  useEffect(() => {
    if (!unitId || !page.data || !positionsReady || readingRestored.current) return;
    const passage = document.getElementById(`reading-${unitId}`);
    if (passage) { (passage.querySelector<HTMLElement>('[data-reading-offset]') || passage).scrollIntoView({ block: 'start' }); readingRestored.current = true; }
  }, [unitId, page.data, positionsReady, resumePosition]);
  const savePosition = async (unit: ReadingUnit, charOffset = 0) => {
    if (busy || (!positionsReady && !positionKnown.current)) return; setBusy(true); setError(null); setNotice('');
    try { const saved = await put<ReadingPosition>('/learning/reading-position', { source: unit.locator, char_offset: charOffset, expected_version: positionVersion.current }); positionVersion.current = saved.version; setNotice('Reading place saved.'); refreshPositions(); }
    catch (caught) { setError(caught); } finally { setBusy(false); }
  };
  const ask = async (event: FormEvent) => {
    event.preventDefault(); if (!chosen || !question.trim() || busy) return; setBusy(true); setError(null);
    try { await onAsk(question.trim(), { scope, document_id: book.id, source_unit_id: chosen.unit.id, selection: chosen.selection }); }
    catch (caught) { setError(caught); } finally { setBusy(false); }
  };
  const bookmark = async () => {
    if (!chosen || busy) return; setBusy(true); setError(null); setNotice('');
    try { await post('/learning/notes', { title: `${book.title} · PDF page ${chosen.unit.page}`, content: chosen.selection.text, kind: 'bookmark', source: { ...chosen.unit.locator, start: chosen.selection.start, end: chosen.selection.end }, concepts: [] }); setNotice('Passage saved in your notes and bookmarks.'); }
    catch (caught) { setError(caught); } finally { setBusy(false); }
  };
  const activeSection = sections.data?.find(item => item.id === sectionId || item.id === page.data?.items[0]?.section_id);
  return <><header className="stack"><div><span className="eyebrow">{book.edition}</span><h1>{book.title}</h1></div><p className="secondary">{book.license}</p></header>
    <div className="reader-mobile-tabs" role="group" aria-label="Reading workspace view">{(['contents', 'reading', 'question'] as const).map(tab => <Button key={tab} aria-pressed={view === tab} onClick={() => setView(tab)}>{tab === 'contents' ? 'Contents' : tab === 'reading' ? 'Read' : 'Ask'}</Button>)}</div>
    <ErrorNotice error={sections.error || page.error || error} action={<Button disabled={busy} onClick={() => { sections.reload(); page.reload(); refreshPositions(); }}>Reload saved reading</Button>} />{notice && <p className="saved" role="status">{notice}</p>}
    {originalPage !== null && <OriginalPageModal documentId={book.id} versionId={book.document_version_id} sourceHash={book.source_sha256} page={originalPage} title={book.title} onClose={() => setOriginalPage(null)} />}
    <div className={`reader-layout reader-view-${view}`}>
      <nav className="reader-contents stack" aria-label="Textbook chapters"><label>Search chapters<input value={filter} onChange={event => setFilter(event.target.value)} /></label>{sections.loading && <Loading>Loading contents…</Loading>}{sections.data?.filter(item => item.title.toLowerCase().includes(filter.toLowerCase())).map(section => <Button key={section.id} aria-current={activeSection?.id === section.id ? 'page' : undefined} onClick={() => go(`/learn/library/${encodeURIComponent(book.id)}/section/${encodeURIComponent(section.id)}`)}>{section.title}<small>PDF {section.first_page}–{section.last_page}</small></Button>)}</nav>
      <section className="reader-body stack" aria-label="Textbook reading"><h2>{activeSection?.title || 'Textbook passages'}</h2>{activeSection && <details><summary>Learning objectives and connected chapters</summary><div className="stack"><ul>{activeSection.learning_objectives.map((text, index) => <li key={index}>{text}</li>)}</ul><p>Key concepts: {activeSection.concepts.join(', ') || 'No published concept metadata'}</p>{activeSection.related_section_ids.map(id => <Button key={id} onClick={() => go(`/learn/library/${encodeURIComponent(book.id)}/section/${encodeURIComponent(id)}`)}>{sections.data?.find(section => section.id === id)?.title || 'Related section'}</Button>)}</div></details>}
        {page.loading && <Loading>Loading original source text…</Loading>}{page.data?.items.map(unit => <ReaderPassage key={unit.id} unit={unit} resumeOffset={resumePosition?.source.source_unit_id === unit.id ? resumePosition.char_offset : undefined} selected={chosen?.unit.id === unit.id ? chosen.selection : null} onSelect={selection => { setChosen({ unit, selection }); }} onAsk={() => { setChosen({ unit, selection: { text: unit.text, start: 0, end: Array.from(unit.text).length } }); setView('question'); }} onSave={() => savePosition(unit, chosen?.unit.id === unit.id ? chosen.selection.start : 0)} onOriginal={() => setOriginalPage(unit.page)} busy={busy || (!positionsReady && !positionKnown.current)} />)}
        {page.data && <div className="form-actions"><Button disabled={!page.data.offset || busy} onClick={() => { setSeekUnit(undefined); setOffset(Math.max(0, page.data!.offset - 20)); setChosen(null); }}>Previous passages</Button><span className="secondary">{page.data.offset + (page.data.items.length ? 1 : 0)}–{page.data.offset + page.data.items.length} of {page.data.total}</span><Button disabled={page.data.next_offset === null || busy} onClick={() => { setSeekUnit(undefined); setOffset(page.data!.next_offset!); setChosen(null); }}>Next passages</Button></div>}
      </section>
      <aside className="reader-question stack" aria-label="Ask about your reading"><h2>Explore this passage</h2><p className="secondary">Select text while reading, or choose “Ask about this passage”.</p>{chosen && <blockquote className="selected-passage">{chosen.selection.text}</blockquote>}<form className="stack" onSubmit={ask}><label>Search within<select value={scope} onChange={event => setScope(event.target.value as ReadingContext['scope'])}><option value="chapter">Current chapter</option><option value="textbook">Current textbook</option><option value="all">All textbooks</option></select></label><label>Your question<textarea rows={4} maxLength={4000} required value={question} onChange={event => setQuestion(event.target.value)} /></label><Button className="primary" type="submit" disabled={!chosen || busy || !question.trim()}>{busy ? 'Opening…' : 'Continue in chat'}</Button><small>Your question opens as an editable draft with a direct explanation selected.</small></form><Button disabled={!chosen || busy} onClick={bookmark}>Bookmark selected passage</Button><Button onClick={() => go('/learn/notes')}>Open notes and bookmarks</Button></aside>
    </div></>;
}

function ReaderPassage({ unit, resumeOffset, selected, onSelect, onAsk, onSave, onOriginal, busy }: { unit: ReadingUnit; resumeOffset?: number; selected: PassageSelection | null; onSelect: (selection: PassageSelection) => void; onAsk: () => void; onSave: () => void; onOriginal: () => void; busy: boolean }) {
  const ref = useRef<HTMLParagraphElement>(null);
  const select = () => { if (ref.current) { const range = passageSelection(ref.current, window.getSelection()); if (range) onSelect(range); } };
  const url = sourceUrl(unit.source_url);
  const characters = Array.from(unit.text);
  const savedOffset = resumeOffset === undefined ? undefined : Math.max(0, Math.min(resumeOffset, characters.length));
  return <article className={`reader-passage ${selected ? 'has-selection' : ''}`} id={`reading-${unit.id}`}><header><span>PDF physical page {unit.page}</span><span className="secondary">{unit.section}</span></header><p ref={ref} className="source-passage" tabIndex={0} onMouseUp={select} onKeyUp={select} onTouchEnd={select}>{selected ? <>{characters.slice(0, selected.start).join('')}<mark>{characters.slice(selected.start, selected.end).join('')}</mark>{characters.slice(selected.end).join('')}</> : savedOffset !== undefined ? <>{characters.slice(0, savedOffset).join('')}<span data-reading-offset={savedOffset} aria-label="Saved reading place">{characters[savedOffset] || ''}</span>{characters.slice(savedOffset + 1).join('')}</> : unit.text}</p><div className="form-actions"><Button onClick={onAsk}>Ask about this passage</Button><Button disabled={busy} onClick={onSave}>Save reading place</Button><Button onClick={onOriginal}>View PDF page</Button>{url && <a className="button" href={url} target="_blank" rel="noopener noreferrer">View original source</a>}</div></article>;
}
