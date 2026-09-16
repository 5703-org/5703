import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Check, Plus, RefreshCw } from 'lucide-react';
import { ApiError, post, request } from './api';
import { Button, DataDetails, ErrorNotice, Loading, titleCase } from './components';
import type { components } from './generated/api';

type Schema = components['schemas'];
export type ModelValues = Schema['ModelValues'];
export type ModelTest = Schema['ConnectionTestOut'];
export type ModelConfiguration = Schema['ModelConfigurationOut'];
export type ModelState = Schema['ModelSettingsState'];
export type ModelPreset = Schema['ProviderPreset'];
const root = '/admin/model-configurations';
const defaults: ModelValues = { provider: 'openai_compatible', model: '', base_url: '', window_tokens: 16384, max_tokens: 1024, timeout_seconds: 60, temperature: 0, token_limit_parameter: 'max_tokens', structured_output_mode: 'json_schema', tokenizer_provider: 'estimate', token_count_fallback: 'estimate' };
const protocols: { value: ModelValues['provider']; label: string }[] = [
  { value: 'openai', label: 'OpenAI' }, { value: 'openai_compatible', label: 'OpenAI-compatible' }, { value: 'anthropic', label: 'Anthropic' }, { value: 'gemini', label: 'Google Gemini' }, { value: 'azure_openai', label: 'Azure OpenAI' }, { value: 'ollama', label: 'Ollama' }, { value: 'local', label: 'Local OpenAI-compatible server' }, { value: 'mock', label: 'Demo (mock)' },
];

export function modelDiagnostic(code: string) {
  if (code === 'CONNECTION_ERROR') return 'The application server could not be reached. The provider test result is not known; refresh before retrying.';
  if (/AUTH|KEY|CREDENTIAL|401|403|PERMISSION|FORBIDDEN/.test(code)) return 'Check the API key and its permission to use this model.';
  if (/QUOTA|RATE|LIMIT|429|BUDGET/.test(code)) return 'Check provider quota, rate limits and the configured token budget before retrying.';
  if (/MODEL|DEPLOYMENT/.test(code)) return 'Check the exact model or deployment name and your access to it.';
  if (/URL|ADDRESS|ENDPOINT|404/.test(code)) return 'Check the protocol and base URL. Use the service base, without credentials or query parameters.';
  if (/NETWORK|CONNECT|TIMEOUT|DNS|TLS/.test(code)) return 'Check whether the API server can reach the provider, including TLS and timeout settings.';
  if (/SCHEMA|STRUCTURED|PARSE|OUTPUT/.test(code)) return 'The provider responded, but its output did not meet the required response format. Review compatibility settings.';
  return 'Review the recorded diagnostic and the provider configuration before retrying.';
}

export function ModelsPage({ onActivated }: { onActivated: () => void }) {
  const [state, setState] = useState<ModelState | null>(null); const [presets, setPresets] = useState<ModelPreset[]>([]);
  const [selected, setSelected] = useState<string | null>(null); const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null); const [notice, setNotice] = useState('');
  const refresh = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [next, options] = await Promise.all([request<ModelState>(root), request<ModelPreset[]>(`${root}/presets`)]);
      setState(next); setPresets(options);
      setSelected(current => current && next.items.some(item => item.id === current) ? current : next.active_configuration_id || next.items[0]?.id || null);
    } catch (caught) { setError(caught); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const saved = (configuration: ModelConfiguration) => {
    setState(current => current && { ...current, items: [...current.items.filter(item => item.id !== configuration.id), configuration] });
    setSelected(configuration.id); setNotice(`Saved version ${configuration.revision}. Test this saved version before enabling it.`);
  };
  const tested = (value: ModelTest) => {
    setState(current => current && { ...current, items: current.items.map(item => item.id === value.configuration_id ? { ...item, latest_test: value } : item) });
    setNotice('');
  };
  const activated = (value: ModelState) => { setState(value); setNotice('Model configuration enabled. New requests will use this selection. Existing requests retain their saved configuration.'); onActivated(); };
  const active = state?.items.find(item => item.id === state.active_configuration_id);
  const current = state?.items.find(item => item.id === selected) || null;
  const latest = state?.items.filter(item => !state.items.some(other => other.group_id === item.group_id && other.revision > item.revision)) || [];
  const older = state?.items.filter(item => !latest.includes(item)) || [];
  const select = (item: ModelConfiguration) => { setSelected(item.id); setNotice(''); };
  return <div className="content-page settings-page">
    <span className="eyebrow">Administration</span><h1>Models</h1>
    <p className="page-intro">Choose an answering service, save its settings, run a connection test, then enable the tested version.</p>
    <div className="admin-toolbar"><Button onClick={() => { setSelected(null); setNotice(''); }} disabled={loading || !state}><Plus size={17} />New configuration</Button><Button onClick={refresh} disabled={loading}><RefreshCw size={17} />Refresh</Button></div>
    <ErrorNotice error={error} />{loading ? <Loading>Loading model settings…</Loading> : state && <>
      <div className="readiness"><strong>{active ? `${active.name} · version ${active.revision}` : state.source === 'environment' ? 'Using server environment settings' : 'No active model configuration'}</strong><p>{active ? `${active.config.provider === 'mock' ? 'Demo (mock model)' : active.config.provider} · ${active.config.model}` : 'No saved configuration is currently selected.'} · Active selection version {state.active_version}</p></div>
      {!state.encryption_ready && <div className="notice"><p>Encrypted key storage is unavailable. Ask the server administrator to configure it before saving a new API key. Keyless local configurations can still be prepared.</p></div>}
      {latest.length > 0 && <nav className="configuration-list" aria-label="Saved model configurations">{latest.map(item => <Button key={item.id} aria-pressed={selected === item.id} onClick={() => select(item)}><span>{item.name}<small>Version {item.revision} · {item.active ? 'Enabled' : item.latest_test?.status === 'passed' ? 'Test passed' : item.latest_test?.status === 'failed' ? 'Test failed' : 'Not tested'}</small></span></Button>)}</nav>}
      {older.length > 0 && <details className="data-details"><summary>Earlier saved versions</summary><div className="configuration-list">{older.map(item => <Button key={item.id} aria-pressed={selected === item.id} onClick={() => select(item)}>{item.name} · version {item.revision}{item.active ? ' · Enabled' : ''}</Button>)}</div></details>}
      {notice && <p className="saved" role="status"><Check size={17} />{notice}</p>}
      <ModelEditor key={current?.id || 'new'} initial={current} presets={presets} state={state} onSaved={saved} onTested={tested} onActivated={activated} />
    </>}
  </div>;
}

function endpointIdentity(config: ModelValues) {
  try { return `${config.provider}:${new URL(config.base_url || '').origin}`; } catch { return `${config.provider}:${config.base_url || ''}`; }
}

function ModelEditor({ initial, presets, state, onSaved, onTested, onActivated }: { initial: ModelConfiguration | null; presets: ModelPreset[]; state: ModelState; onSaved: (value: ModelConfiguration) => void; onTested: (value: ModelTest) => void; onActivated: (value: ModelState) => void }) {
  const [name, setName] = useState(initial?.name || ''); const [preset, setPreset] = useState(initial?.preset || 'custom');
  const [config, setConfig] = useState<ModelValues>(initial?.config || defaults); const [key, setKey] = useState(''); const [clearKey, setClearKey] = useState(false);
  const [busy, setBusy] = useState<'save' | 'test' | 'activate' | null>(null); const pending = useRef(false); const [error, setError] = useState<unknown>(null);
  const dirty = !initial || name !== initial.name || preset !== initial.preset || JSON.stringify(config) !== JSON.stringify(initial.config) || !!key || clearKey;
  const currentTest = initial?.latest_test;
  const changedDestination = initial?.has_api_key && endpointIdentity(initial.config) !== endpointIdentity(config);
  const canActivate = !!initial && !dirty && !error && !initial.active && currentTest?.status === 'passed' && currentTest.configuration_id === initial.id;
  const change = <K extends keyof ModelValues>(field: K, value: ModelValues[K]) => { setConfig(previous => ({ ...previous, [field]: value })); setError(null); };
  const choosePreset = (value: string) => {
    setPreset(value); setError(null);
    const option = presets.find(item => item.id === value);
    if (option) { setConfig({ ...defaults, ...option.config }); if (!name) setName(option.name); }
  };
  const action = async (kind: 'save' | 'test' | 'activate') => {
    if (pending.current) return;
    setError(null);
    if (kind === 'save') {
      if (changedDestination && !key && !clearKey) { setError(new Error('The service destination changed. Enter a key for this service or explicitly remove the saved key.')); return; }
      if (key && !state.encryption_ready) { setError(new Error('Encrypted key storage must be available before saving an API key.')); return; }
      if (config.provider !== 'mock') {
        try { const url = new URL(config.base_url || ''); if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error(); }
        catch { setError(new Error('Use an HTTP(S) base URL without credentials, query parameters or fragments.')); return; }
      }
    }
    if (kind !== 'save' && (!initial || dirty)) return;
    if (kind === 'activate' && !canActivate) return;
    pending.current = true; setBusy(kind);
    try {
      if (kind === 'save') onSaved(await post<ModelConfiguration>(initial ? `${root}/${initial.id}/versions` : root, { name: name.trim(), preset, config: { ...config, model: config.model.trim(), base_url: config.base_url?.trim() || null, api_version: config.api_version?.trim() || null }, ...(key ? { api_key: key } : {}), ...(clearKey ? { clear_api_key: true } : {}) }));
      else if (kind === 'test') onTested(await post<ModelTest>(`${root}/${initial!.id}/test`));
      else onActivated(await post<ModelState>(`${root}/${initial!.id}/activate`, { test_id: currentTest!.id, expected_active_version: state.active_version }));
    } catch (caught) { setError(caught); }
    finally { if (kind === 'save') setKey(''); pending.current = false; setBusy(null); }
  };
  const submit = (event: FormEvent) => { event.preventDefault(); void action('save'); };
  return <section className="model-editor"><h2>{initial ? `${initial.name} · version ${initial.revision}` : 'New configuration'}</h2>
    <form className="stack" onSubmit={submit}><fieldset disabled={!!busy} className="stack">
      <div className="form-grid"><label>Name<input required maxLength={120} value={name} onChange={event => setName(event.target.value)} placeholder="Team answering model" /></label><label>Provider preset<select value={preset} onChange={event => choosePreset(event.target.value)}><option value="custom">Custom service</option>{presets.filter(item => item.id !== 'custom').map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label></div>
      {presets.find(item => item.id === preset)?.description && <p className="secondary">{presets.find(item => item.id === preset)!.description}</p>}
      <div className="form-grid"><label>API protocol<select value={config.provider} onChange={event => { change('provider', event.target.value as ModelValues['provider']); setPreset('custom'); }}>{protocols.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label><label>{config.provider === 'azure_openai' ? 'Deployment name' : 'Model name'}<input required maxLength={200} value={config.model} onChange={event => change('model', event.target.value)} placeholder="Exact model identifier" /></label></div>
      {config.provider !== 'mock' && <label>Base URL<input type="url" required maxLength={2048} value={config.base_url || ''} onChange={event => change('base_url', event.target.value)} placeholder="https://your-provider.example/v1" autoComplete="off" /><small>The API server connects to this address. A local address refers to the server’s machine.</small></label>}
      {config.provider === 'azure_openai' && <label>Azure API version<input maxLength={50} value={config.api_version || ''} onChange={event => change('api_version', event.target.value)} /><small>Optional for Azure v1. For dated deployment endpoints, enter the API version required by your service.</small></label>}
      {config.provider !== 'mock' && <><label>{initial?.has_api_key ? 'Replace API key' : 'API key'}<input type="password" maxLength={8192} value={key} disabled={clearKey || !state.encryption_ready} onChange={event => setKey(event.target.value)} autoComplete="new-password" spellCheck={false} placeholder={initial?.has_api_key ? 'Leave empty to keep the saved key' : 'Enter only if this service needs a key'} /><small>{initial?.has_api_key ? 'Saved key: ********. The saved value is never returned to this page.' : 'Keys are sent only when you save and are never stored in browser storage.'}</small></label></>}{initial?.has_api_key && <label className="inline-check"><input type="checkbox" checked={clearKey} onChange={event => { setClearKey(event.target.checked); setKey(''); }} />Remove the saved API key in the new version</label>}
      {changedDestination && <p className="secondary">This destination differs from the saved version. Enter the appropriate key or remove the old one before saving.</p>}
      <details className="model-advanced"><summary>Advanced settings</summary><div className="stack">
        <div className="form-grid"><label>Context window (tokens)<input type="number" required min={2048} max={2000000} value={config.window_tokens} onChange={event => change('window_tokens', Number(event.target.value))} /></label><label>Maximum output tokens<input type="number" required min={1} max={1024} value={config.max_tokens} onChange={event => change('max_tokens', Number(event.target.value))} /></label><label>Timeout (seconds)<input type="number" required min={1} max={60} value={config.timeout_seconds} onChange={event => change('timeout_seconds', Number(event.target.value))} /></label><label>Temperature<input type="number" min={0} max={2} step="0.1" value={config.temperature ?? ''} onChange={event => change('temperature', event.target.value === '' ? null : Number(event.target.value))} /><small>Leave blank when the model does not accept temperature.</small></label></div>
        <div className="form-grid"><label>Output limit parameter<select value={config.token_limit_parameter || 'max_tokens'} onChange={event => change('token_limit_parameter', event.target.value as ModelValues['token_limit_parameter'])}><option value="max_tokens">max_tokens</option><option value="max_completion_tokens">max_completion_tokens</option></select></label><label>Response format<select value={config.structured_output_mode || 'json_schema'} onChange={event => change('structured_output_mode', event.target.value as ModelValues['structured_output_mode'])}><option value="json_schema">JSON schema</option><option value="json_object">JSON object</option><option value="prompt">Prompt instructions</option></select></label></div>
        <p className="secondary">These limits are bounded by the server. All responses must still pass the application’s response validation.</p>
        <label>Thinking mode<select value={config.thinking_enabled === true ? 'enabled' : config.thinking_enabled === false ? 'disabled' : 'default'} onChange={event => change('thinking_enabled', event.target.value === 'default' ? null : event.target.value === 'enabled')}><option value="default">Provider default</option><option value="disabled">Disabled</option><option value="enabled">Enabled</option></select><small>Use only when the provider supports this setting. The DeepSeek preset disables thinking for the bounded output budget.</small></label>
      </div></details>
    </fieldset>
    <ErrorNotice error={error} />{error instanceof ApiError && <p className="secondary">{modelDiagnostic(error.code)}{error.status === 409 ? ' Refresh to load the current active version before retrying.' : ''}</p>}
    <div className="form-actions"><Button type="submit" className="primary" disabled={!!busy || !dirty}>{busy === 'save' ? 'Saving…' : initial ? 'Save new version' : 'Save configuration'}</Button><Button disabled={!!busy || !initial || dirty} onClick={() => action('test')}>{busy === 'test' ? 'Testing connection…' : 'Test connection'}</Button><Button disabled={!!busy || !canActivate} onClick={() => action('activate')}>{busy === 'activate' ? 'Enabling…' : initial?.active ? 'Enabled' : 'Enable tested version'}</Button></div>
    {dirty && initial && <p className="secondary">Save your changes as a new version, then test that version before enabling it.</p>}
    <p className="secondary">{config.provider === 'mock' ? 'Mock checks run locally. They do not test a live provider or establish answer quality.' : 'Connection tests make an actual request to the selected provider and may use its quota. A passed test checks connection and response format, not answer quality.'}</p>
    {currentTest && <section className={`model-test-result ${currentTest.status}`} aria-label="Latest connection test" role="status"><h3>{currentTest.model_mode === 'mock' ? 'Mock check' : 'Connection test'} {currentTest.status}</h3><p>{currentTest.message}</p><p className="secondary">{currentTest.diagnostic_code} · {currentTest.latency_ms} ms · {currentTest.created_at}</p>{currentTest.status === 'failed' && <p>{modelDiagnostic(currentTest.diagnostic_code)}</p>}{dirty && <p>This result belongs to the saved version; your unsaved edits have not been tested.</p>}<DataDetails title="Test usage" data={currentTest.usage} /></section>}
    {initial && <DataDetails title="Saved configuration identity" data={{ id: initial.id, group_id: initial.group_id, revision: initial.revision, config_hash: initial.config_hash, created_at: initial.created_at, active: initial.active }} />}
  </form></section>;
}
