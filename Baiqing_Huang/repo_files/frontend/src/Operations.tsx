import { Button, DataDetails, ErrorNotice, Loading, titleCase } from './components';
import { useLearningResource } from './learning-ui';

type ModelSummary = { configuration_id: string; name: string; provider_preset: string; model: string | null; revision: number };
type QueueSummary = { queued: number; running: number; retry_wait: number; failed: number; oldest_queued_seconds: number | null };
type WorkerLockSummary = {
  observation: 'postgres_advisory_lock' | 'unavailable';
  layout: 'all' | 'split' | 'partial' | 'none' | 'unexpected' | 'unavailable';
  interactive: { lock_observed: boolean | null };
  background: { lock_observed: boolean | null };
};
export interface OperationsOverview {
  observed_at: string; database: string;
  corpus: { active_release_id: string | null; release_state: string | null; document_count: number; chunk_vector_count: number };
  model: { answer: ModelSummary | null; checker: ModelSummary | null };
  queues: { interactive: QueueSummary; background: QueueSummary };
  worker_locks: WorkerLockSummary;
  recent_failures: { job_id: string; request_id: string | null; kind: string; error_code: string | null; updated_at: string }[];
  experiment_states: Record<string, number>;
  recent_usage: { sampled_requests: number; requests_with_usage: number; input_tokens: number; output_tokens: number; scope: string; cost_estimate: null };
}

export function OperationsPage({ go }: { go: (path: string) => void }) {
  const result = useLearningResource<OperationsOverview>('/admin/operations/overview');
  const data = result.data;
  return <div className="content-page stack"><div><span className="eyebrow">Administration</span><h1>Operations overview</h1><p className="page-intro">Inspect the saved configuration, current queues and recent workspace usage.</p></div><Button disabled={result.loading} onClick={result.reload}>Refresh operations</Button><ErrorNotice error={result.error} />{result.loading && <Loading>Loading operational records…</Loading>}{data && <><p className="secondary">Observed {new Date(data.observed_at).toLocaleString()}</p><div className="learning-cards"><section className="record stack"><h2>Database and sources</h2><p>Database: {titleCase(data.database)}</p><p>{data.corpus.document_count} documents · {data.corpus.chunk_vector_count.toLocaleString()} chunk vectors</p><p>Release: {data.corpus.active_release_id || 'No active release'}</p><p>State: {data.corpus.release_state ? titleCase(data.corpus.release_state) : 'Unavailable'}</p><Button onClick={() => go('/admin/corpus')}>Inspect corpus and quarantine</Button></section><section className="record stack"><h2>Answer and checker models</h2>{(['answer', 'checker'] as const).map(role => <div key={role}><h3>{titleCase(role)}</h3>{data.model[role] ? <p>{data.model[role].name} · {data.model[role].model || 'Model not recorded'} · Revision {data.model[role].revision}</p> : <p className="secondary">No managed configuration recorded. Inspect the effective configuration on Models.</p>}</div>)}<Button onClick={() => go('/admin/models')}>Manage models and tests</Button></section></div>
    <section className="stack"><h2>Processing queues</h2><p className="secondary">Counts describe saved jobs in this workspace. Advisory locks show whether a worker claimed a lane at observation time; they do not prove the worker is responsive.</p><p role="status">Worker lock observation: {data.worker_locks.observation === 'unavailable' ? 'Unavailable' : titleCase(data.worker_locks.layout)}</p><div className="learning-cards">{(['interactive', 'background'] as const).map(queue => <article className="record" key={queue}><h3>{queue === 'interactive' ? 'Interactive answers' : 'Background work'}</h3><p>Worker lock observed: {data.worker_locks[queue].lock_observed === null ? 'Unknown' : data.worker_locks[queue].lock_observed ? 'Yes' : 'No'}</p><dl className="metadata">{Object.entries(data.queues[queue]).map(([key, value]) => <div key={key}><dt>{titleCase(key)}</dt><dd>{value === null ? 'No queued job' : value}{key === 'oldest_queued_seconds' && value !== null ? ' seconds' : ''}</dd></div>)}</dl></article>)}</div></section>
    <section className="record stack"><h2>Recent recorded usage</h2><p>{data.recent_usage.requests_with_usage} of {data.recent_usage.sampled_requests} sampled requests have provider counters.</p><dl className="metadata"><div><dt>Known input tokens</dt><dd>{data.recent_usage.input_tokens.toLocaleString()}</dd></div><div><dt>Known output tokens</dt><dd>{data.recent_usage.output_tokens.toLocaleString()}</dd></div><div><dt>Estimated cost</dt><dd>Unavailable · tariff evidence is required</dd></div></dl><p className="secondary">{data.recent_usage.scope}</p></section>
    <section className="stack"><h2>Recent failed jobs</h2>{data.recent_failures.length ? data.recent_failures.map(job => <article className="record" key={job.job_id}><p>{titleCase(job.kind)} · {job.error_code || 'Error code not recorded'}</p><p className="secondary">{new Date(job.updated_at).toLocaleString()} · Job {job.job_id}</p>{job.request_id ? <Button onClick={() => go(`/admin/failures/${encodeURIComponent(job.request_id!)}`)}>Inspect request</Button> : <Button onClick={() => go('/admin/corpus')}>Inspect background processing</Button>}</article>) : <p>No failed jobs were returned.</p>}<Button onClick={() => go('/admin/failures')}>All response diagnostics</Button></section><DataDetails title="Experiment states" data={data.experiment_states} /><div className="form-actions"><Button onClick={() => go('/admin/experiments')}>Experiments</Button><Button onClick={() => go('/admin/practice')}>Practice quality and publication</Button><Button onClick={() => go('/admin/accounts')}>Accounts and access</Button></div></>}</div>;
}
