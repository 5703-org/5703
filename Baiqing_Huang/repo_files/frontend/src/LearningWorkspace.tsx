import { StudyLibrary } from './StudyLibrary';
import { StudyGoals, StudyNotes, StudyRecords } from './StudyPlans';
import { PracticeList, PracticeWorkspace, ReviewQueue } from './StudyPractice';
import type { ReadingContext } from './reading-context';
import './styles/learning.css';

export function LearningWorkspace({ path, userId, go, onAsk }: { path: string; userId: string; go: (path: string) => void; onAsk: (question: string, context: ReadingContext) => Promise<void> }) {
  const parts = path.split('/').filter(Boolean).map(decodeURIComponent); const area = parts[1] || 'library';
  const tabs = [['library', 'Textbooks'], ['goals', 'Goals'], ['practice', 'Practice'], ['review', 'Review'], ['notes', 'Notes'], ['records', 'Records']];
  return <div className="learning-page"><nav className="learning-navigation" aria-label="Learning workspace">{tabs.map(([id, label]) => <a className="button" key={id} href={`/learn/${id}`} aria-current={area === id ? 'page' : undefined} onClick={event => { event.preventDefault(); go(`/learn/${id}`); }}>{label}</a>)}</nav><div className="learning-content">{area === 'library' ? <StudyLibrary bookId={parts[2]} sectionId={parts[3] === 'section' ? parts[4] : undefined} unitId={parts[3] === 'unit' ? parts[4] : undefined} go={go} onAsk={onAsk} /> : area === 'goals' ? <StudyGoals go={go} onAsk={onAsk} /> : area === 'practice' ? parts[2] && parts[2] !== 'goal' ? <PracticeWorkspace key={parts[2]} userId={userId} itemId={parts[2]} goalId={parts[3] === 'goal' ? parts[4] : undefined} go={go} /> : <PracticeList goalId={parts[2] === 'goal' ? parts[3] : undefined} unitId={parts[4] === 'unit' ? parts[5] : undefined} go={go} /> : area === 'review' ? <ReviewQueue go={go} /> : area === 'notes' ? <StudyNotes go={go} /> : area === 'records' ? <StudyRecords /> : <h1>Learning page not found</h1>}</div></div>;
}
