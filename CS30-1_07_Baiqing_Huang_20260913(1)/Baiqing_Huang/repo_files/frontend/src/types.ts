import type { components } from './generated/api';

type Schema = components['schemas'];
export type User = Schema['UserOut'];
export type Profile = Schema['Profile'];
export type Session = Schema['SessionOut'];
export type ApiErrorData = Schema['ErrorData'];
export type ChatResponse = Schema['ChatResponseV1'];
export type MCQResponse = Schema['MCQResponseV1'];
export type Evidence = Schema['EvidenceSnapshot'];
export type Answer = Schema['AnswerOut'];
export type Message = Schema['MessageOut'];
export type MessagePage = Schema['MessagePage'];
export type Job = Schema['JobOut'];
export type JobReceipt = Schema['JobReceipt'];
export type Feedback = Pick<Schema['FeedbackOut'], 'helpful' | 'comment'> & Partial<Omit<Schema['FeedbackOut'], 'helpful' | 'comment'>>;
export type Capabilities = Schema['CapabilitiesOut'];
export type RecordData = Record<string, unknown>;
