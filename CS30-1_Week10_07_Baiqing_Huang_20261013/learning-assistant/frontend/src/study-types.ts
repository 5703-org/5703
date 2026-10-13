import type { components } from './generated/api';

type Schema = components['schemas'];
export type SourceLocator = Schema['SourceLocator'];
export type Book = Schema['BookOut'];
export type Section = Schema['SectionOut'];
export type ReadingUnit = Schema['ReadingUnitOut'];
export type ReadingPage = Schema['ReadingPageOut'];
export type ReadingPosition = Schema['ReadingPositionOut'];
export type GoalUnit = Schema['GoalUnitOut'];
export type Goal = Schema['GoalOut'];
export type PracticeKind = Schema['PracticeOut']['kind'];
export type PracticeItem = Schema['PracticeOut'];
// The server materializes these contract defaults on every saved attempt.
export type PracticeResponse = Required<Schema['PracticeResponse']>;
export type PracticeFeedback = Required<Schema['PracticeFeedback']>;
export type PracticeAssessment = Omit<NonNullable<Schema['AttemptOut']['assessment']>, 'feedback'> & { feedback: PracticeFeedback };
export type PracticeAttempt = Omit<Schema['AttemptOut'], 'response' | 'feedback' | 'assessment'> & { response: PracticeResponse; feedback: PracticeFeedback; assessment?: PracticeAssessment | null };
export function effectivePracticeFeedback(attempt: PracticeAttempt): PracticeFeedback {
  return attempt.assessment?.status === 'applied' ? attempt.assessment.feedback : attempt.feedback;
}
export function isHistoricalLexicalFeedback(attempt: PracticeAttempt): boolean {
  const feedback = effectivePracticeFeedback(attempt);
  return (feedback.grading_method === 'deterministic_rules_v1' || feedback.grading_method === 'deterministic_rules_v2')
    && attempt.response.value === null && !attempt.response.selection.length && Boolean(attempt.response.text.trim());
}
export type PracticeProgress = Omit<Schema['PracticeProgressOut'], 'attempts'> & { attempts: PracticeAttempt[] };
export type PracticeTutor = Schema['PracticeTutorOut'];
export type ReviewItem = Schema['ReviewOut'];
export type StudyNote = Omit<Schema['NoteOut'], 'concepts'> & { concepts: string[] };
export type LearningRecord = Schema['LearningRecordOut'];
