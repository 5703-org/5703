import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ModelsPage, type ModelConfiguration, type ModelPreset, type ModelState, type ModelTest } from './Models';
import { ApiError, post, request } from './api';

vi.mock('./api', async importOriginal => ({ ...await importOriginal<typeof import('./api')>(), request: vi.fn(), post: vi.fn() }));
const config: ModelConfiguration = { id: 'config-1', group_id: 'group-1', revision: 1, name: 'Team model', preset: 'custom', config: { provider: 'openai_compatible', model: 'verified-model', base_url: 'https://provider.example/v1', window_tokens: 16384, max_tokens: 1024, timeout_seconds: 60, temperature: 0, token_limit_parameter: 'max_tokens', structured_output_mode: 'json_schema', tokenizer_provider: 'estimate', token_count_fallback: 'estimate' }, config_hash: 'hash-1', has_api_key: true, api_key_masked: '********', created_at: '2026-09-13T01:00:00Z', latest_test: null, active: false };
const state: ModelState = { items: [config], active_configuration_id: null, active_version: 4, source: 'environment', encryption_ready: true };
const test: ModelTest = { id: 'test-1', configuration_id: 'config-1', status: 'passed', model_mode: 'live', diagnostic_code: 'CONNECTION_OK', message: 'The configured endpoint returned a valid response.', latency_ms: 98, usage: { output_tokens: 12 }, created_at: '2026-09-13T01:01:00Z', test_version: 'provider_probe_v4', role: 'answer', tier: 'all', network_label: 'local_unverified', project_passed: true, activation_eligible: true };
const presets: ModelPreset[] = [{ id: 'openai', name: 'OpenAI', description: 'Select an available model.', requires_api_key: true, config: { provider: 'openai', base_url: 'https://api.openai.com/v1', model: '' } }, { id: 'mock', name: 'Demo (mock)', description: 'Application checks only.', requires_api_key: false, config: { provider: 'mock', model: 'mock-v1', base_url: null } }];
function setResponses(value: ModelState) { vi.mocked(request).mockImplementation(async path => path.endsWith('/presets') ? presets : value); }
beforeEach(() => { vi.clearAllMocks(); sessionStorage.clear(); localStorage.clear(); setResponses(state); });
afterEach(cleanup);

describe('saved model configuration lifecycle', () => {
  it.each([
    ['openai_luna_v2', 'openai/gpt-6-luna', null, 2048, 'json_schema', 16384, 60],
    ['qwen38_alibaba_v2', 'qwen/qwen3.8-flash', 0, 2048, 'json_schema', 16384, 60],
    ['glm53_deepinfra_fp4_v1', 'z-ai/glm-5.3-flash', 0, 4096, 'json_schema', 16384, 60],
    ['gemini35_google_vertex_v1', 'google/gemini-3.5-flash-lite', null, 2048, 'json_object', 131072, 45],
  ] as const)('saves %s while retaining its existing key and requiring fresh tests', async (profile, model, temperature, maxTokens, structuredOutputMode, windowTokens, timeoutSeconds) => {
    const previous = { ...config, config: { ...config.config, base_url: 'https://openrouter.ai/api/v1', model: 'qwen/qwen3.8-flash', openrouter_route_profile: 'qwen38_alibaba_v1' } };
    setResponses({ ...state, items: [previous] });
    const next = { ...previous, id: 'config-2', revision: 2, config: { ...previous.config, model, openrouter_route_profile: profile, temperature, max_tokens: maxTokens } };
    vi.mocked(post).mockResolvedValue(next);
    const activated = vi.fn(); render(<ModelsPage onActivated={activated} />);
    fireEvent.change(await screen.findByLabelText(/^OpenRouter model/), { target: { value: profile } });
    expect((screen.getByLabelText('Model name') as HTMLInputElement).value).toBe(model);
    expect((screen.getByLabelText('Model name') as HTMLInputElement).readOnly).toBe(true);
    expect((screen.getByLabelText(/Replace API key/) as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText(/^Thinking mode/) as HTMLSelectElement).disabled).toBe(true);
    expect((screen.getByLabelText(/^Reasoning effort/) as HTMLInputElement).disabled).toBe(true);
    expect(post).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Save new version' }));
    await screen.findByText('Saved version 2. Test this saved version before enabling it.');
    const [path, body] = vi.mocked(post).mock.calls[0];
    expect(path).toBe('/admin/model-configurations/config-1/versions');
    expect(body).toEqual(expect.objectContaining({ config: expect.objectContaining({ provider: 'openai_compatible', base_url: 'https://openrouter.ai/api/v1', model, openrouter_route_profile: profile, temperature, max_tokens: maxTokens, structured_output_mode: structuredOutputMode, window_tokens: windowTokens, timeout_seconds: timeoutSeconds, thinking_enabled: null, reasoning_effort: null, seed: null, auth_header: null, api_version: null }) }));
    expect(body).not.toHaveProperty('api_key'); expect(body).not.toHaveProperty('clear_api_key');
    expect(post).toHaveBeenCalledTimes(1); expect(activated).not.toHaveBeenCalled();
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
  });


  it('requires fresh answer and checker project receipts for an explicitly selected experimental Google version', async () => {
    const previous: ModelConfiguration = { ...config, config: { ...config.config, base_url: 'https://openrouter.ai/api/v1', model: 'qwen/qwen3.8-flash', openrouter_route_profile: 'qwen38_alibaba_v1' }, latest_test: test, latest_answer_test: test, latest_checker_test: { ...test, id: 'previous-checker', role: 'checker' } };
    setResponses({ ...state, items: [previous] });
    let saved: ModelConfiguration = previous;
    let finish: (value: ModelTest) => void = () => {};
    const answer: ModelTest = { ...test, id: 'google-answer-2', configuration_id: 'config-2', tier: 'project' };
    const checker: ModelTest = { ...answer, id: 'google-checker-2', role: 'checker' };
    vi.mocked(post).mockImplementation((path, body) => {
      if (path.endsWith('/versions')) {
        saved = { ...previous, id: 'config-2', revision: 2, config_hash: 'hash-2', config: (body as { config: ModelConfiguration['config'] }).config, latest_test: null, latest_answer_test: null, latest_checker_test: null };
        return Promise.resolve(saved);
      }
      if (path.endsWith('/test')) return new Promise(resolve => { finish = resolve as (value: ModelTest) => void; });
      return Promise.resolve({ ...state, active_configuration_id: saved.id, active_checker_configuration_id: saved.id, active_version: 5, source: 'database', items: [{ ...saved, active: true, latest_test: checker, latest_answer_test: answer, latest_checker_test: checker }] });
    });
    const activated = vi.fn(); render(<ModelsPage onActivated={activated} />);
    const select = await screen.findByLabelText(/^OpenRouter model/) as HTMLSelectElement;
    expect(select.value).toBe('qwen38_alibaba_v1');
    expect(screen.getByRole('option', { name: 'Gemini 3.5 Flash Lite (experimental)' })).toBeTruthy();
    expect(post).not.toHaveBeenCalled();
    fireEvent.change(select, { target: { value: 'gemini35_google_vertex_v1' } });
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Save new version' }));
    await screen.findByText('Saved version 2. Test this saved version before enabling it.');
    expect(post).toHaveBeenCalledTimes(1); expect(activated).not.toHaveBeenCalled();
    expect(saved.config).toEqual(expect.objectContaining({ model: 'google/gemini-3.5-flash-lite', openrouter_route_profile: 'gemini35_google_vertex_v1', structured_output_mode: 'json_object', window_tokens: 131072, max_tokens: 2048, timeout_seconds: 45, temperature: null, thinking_enabled: null, reasoning_effort: null }));
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByText('Connection test passed')).toBeNull();
    fireEvent.change(screen.getByLabelText('Test stage'), { target: { value: 'project' } });
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(vi.mocked(post).mock.calls[1]).toEqual(['/admin/model-configurations/config-2/test', { role: 'answer', tier: 'project', network_label: 'local_unverified' }, expect.any(String)]);
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
    finish(answer);
    await screen.findByText('Connection test passed');
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText('Test role'), { target: { value: 'checker' } });
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(3));
    expect(vi.mocked(post).mock.calls[2]).toEqual(['/admin/model-configurations/config-2/test', { role: 'checker', tier: 'project', network_label: 'local_unverified' }, expect.any(String)]);
    expect(activated).not.toHaveBeenCalled();
    finish(checker);
    await waitFor(() => expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(false));
    expect(post).toHaveBeenCalledTimes(3); expect(activated).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Enable tested version' }));
    await screen.findByText(/Model configuration enabled\./);
    expect(post).toHaveBeenLastCalledWith('/admin/model-configurations/config-2/activate', { test_id: answer.id, checker_configuration_id: saved.id, checker_test_id: checker.id, expected_active_version: 4 });
    expect(activated).toHaveBeenCalledTimes(1);
  });

  it('retains an earlier saved route without replacing it when editing its name', async () => {
    const previous = { ...config, config: { ...config.config, base_url: 'https://openrouter.ai/api/v1', model: 'qwen/qwen3.8-flash', openrouter_route_profile: 'qwen38_alibaba_v1' } };
    setResponses({ ...state, items: [previous] });
    vi.mocked(post).mockResolvedValue({ ...previous, id: 'config-2', revision: 2 });
    render(<ModelsPage onActivated={() => {}} />);
    const select = await screen.findByLabelText(/^OpenRouter model/) as HTMLSelectElement;
    expect(select.value).toBe('qwen38_alibaba_v1');
    expect(screen.getByRole('option', { name: 'Earlier saved route' })).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Earlier model name edit' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save new version' }));
    await screen.findByText('Saved version 2. Test this saved version before enabling it.');
    expect(vi.mocked(post).mock.calls[0][1]).toEqual(expect.objectContaining({ config: expect.objectContaining({ openrouter_route_profile: 'qwen38_alibaba_v1', max_tokens: previous.config.max_tokens }) }));
    expect(vi.mocked(post).mock.calls[0][1]).not.toHaveProperty('api_key');
  });

  it('keeps earlier gateway settings readable and requires an explicit route before saving', async () => {
    const previous = { ...config, config: { ...config.config, base_url: 'https://openrouter.ai/api/v1' } };
    setResponses({ ...state, items: [previous] });
    render(<ModelsPage onActivated={() => {}} />);
    const select = await screen.findByLabelText(/^OpenRouter model/) as HTMLSelectElement;
    expect(select.value).toBe('');
    expect((screen.getByLabelText('Model name') as HTMLInputElement).value).toBe('verified-model');
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Reviewed gateway version' } });
    fireEvent.submit(select.form!);
    await screen.findByText('Choose an OpenRouter model before saving.');
    expect(post).not.toHaveBeenCalled();
  });

  it.each(['legacy_connection_v1', 'provider_probe_v2', 'provider_probe_v3'] as const)('retains %s history and requires the current project contract before activation', async (version) => {
    // A complete role pair with an inconsistent true flag still cannot admit an obsolete protocol.
    const legacy: ModelTest = { ...test, test_version: version, tier: version === 'legacy_connection_v1' ? 'legacy' : 'all', project_passed: version !== 'legacy_connection_v1' };
    setResponses({ ...state, items: [{ ...config, latest_test: legacy, latest_answer_test: legacy, latest_checker_test: { ...legacy, id: 'legacy-checker', role: 'checker' } }] });
    render(<ModelsPage onActivated={() => {}} />);
    await screen.findByText('Legacy connection test passed');
    expect(screen.getByText('Run the current project and checker tests before enabling this configuration.')).toBeTruthy();
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('enables a server-qualified v4 role pair without repeating paid tests or equating different hash domains', async () => {
    const answer: ModelTest = { ...test, stages: [{ metadata: { configuration_hash: 'probe-model-config-digest' } }] };
    const checker: ModelTest = { ...answer, id: 'checker-1', role: 'checker' };
    const qualified = { ...config, latest_test: checker, latest_answer_test: answer, latest_checker_test: checker };
    expect(answer.stages?.[0].metadata).not.toEqual({ configuration_hash: qualified.config_hash });
    setResponses({ ...state, items: [qualified] });
    vi.mocked(post).mockResolvedValue({ ...state, active_configuration_id: config.id, active_checker_configuration_id: config.id, active_version: 5, source: 'database', items: [{ ...qualified, active: true }] });
    const activated = vi.fn(); render(<ModelsPage onActivated={activated} />);
    const enable = await screen.findByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement;
    expect(enable.disabled).toBe(false); expect(post).not.toHaveBeenCalled();
    fireEvent.click(enable);
    await screen.findByText(/Model configuration enabled\./);
    expect(post).toHaveBeenCalledExactlyOnceWith('/admin/model-configurations/config-1/activate', { test_id: answer.id, checker_configuration_id: config.id, checker_test_id: checker.id, expected_active_version: 4 });
    expect(activated).toHaveBeenCalledTimes(1);
  });

  it.each((['answer', 'checker'] as const).flatMap(role => [
    { role, failure: 'server eligibility is false', change: { activation_eligible: false } },
    { role, failure: 'server eligibility is absent', change: { activation_eligible: undefined } },
    { role, failure: 'receipt has the other role', change: { role: role === 'answer' ? 'checker' as const : 'answer' as const } },
    { role, failure: 'receipt belongs to another configuration', change: { configuration_id: 'other-configuration' } },
  ]))('blocks a complete v4 pair when $role $failure', async ({ role, change }) => {
    const answer: ModelTest = { ...test };
    const checker: ModelTest = { ...test, id: 'checker-1', role: 'checker' };
    // Deliberately inject malformed API data, including an absent required field.
    Object.assign(role === 'answer' ? answer : checker, change);
    setResponses({ ...state, items: [{ ...config, latest_test: answer, latest_answer_test: answer, latest_checker_test: checker }] });
    const activated = vi.fn(); render(<ModelsPage onActivated={activated} />);
    const enable = await screen.findByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement;
    expect(enable.disabled).toBe(true);
    fireEvent.click(enable);
    expect(post).not.toHaveBeenCalled(); expect(activated).not.toHaveBeenCalled();
  });

  it('preserves the exact request key after a lost test receipt and shows the selected tier', async () => {
    vi.mocked(post).mockRejectedValueOnce(new ApiError('CONNECTION_ERROR', 'Receipt not received.')).mockResolvedValueOnce({ ...test, tier: 'basic', project_passed: false, activation_eligible: false, stages: [{ tier: 'basic', status: 'passed', diagnostic: { http_status: 200, provider_request_id: 'fixture-request' } }] });
    render(<ModelsPage onActivated={() => {}} />);
    await screen.findByLabelText('Test stage');
    fireEvent.change(screen.getByLabelText('Test stage'), { target: { value: 'basic' } });
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }));
    await screen.findByText('Receipt not received.');
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }));
    await screen.findByText('Stage 1: basic · passed');
    expect(vi.mocked(post).mock.calls[0][2]).toBe(vi.mocked(post).mock.calls[1][2]);
    expect(vi.mocked(post).mock.calls[0][1]).toEqual({ role: 'answer', tier: 'basic', network_label: 'local_unverified' });
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('uses a separate checker receipt and displays sanitized per-stage diagnostics', async () => {
    const checker: ModelConfiguration = { ...config, id: 'other-checker', name: 'Separate checker', latest_checker_test: { ...test, id: 'checker-proof', configuration_id: 'other-checker', role: 'checker' } };
    setResponses({ ...state, items: [{ ...config, latest_test: test, latest_answer_test: test }, checker] });
    vi.mocked(post).mockResolvedValue({ ...state, active_configuration_id: config.id, active_checker_configuration_id: checker.id, active_version: 5 });
    render(<ModelsPage onActivated={() => {}} />);
    await screen.findByLabelText('Checker configuration');
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText('Checker configuration'), { target: { value: checker.id } });
    fireEvent.click(screen.getByRole('button', { name: 'Enable tested version' }));
    await screen.findByText(/Model configuration enabled\./);
    expect(post).toHaveBeenLastCalledWith('/admin/model-configurations/config-1/activate', { test_id: 'test-1', checker_configuration_id: 'other-checker', checker_test_id: 'checker-proof', expected_active_version: 4 });
  });

  it.each([
    { name: 'Azure v1 with a blank API version', base_url: 'https://resource.openai.azure.com/openai/v1', api_version: '', expected: null },
    { name: 'a dated Azure deployment with its explicit API version', base_url: 'https://resource.openai.azure.com/openai/deployments/team-model', api_version: '2024-10-21', expected: '2024-10-21' },
  ])('saves $name without testing or enabling it', async ({ base_url, api_version, expected }) => {
    const azure: ModelPreset = { id: 'azure', name: 'Azure OpenAI', description: 'Use an available deployment.', requires_api_key: true, config: { provider: 'azure_openai', model: '', base_url, api_version: null } };
    vi.mocked(request).mockImplementation(async path => path.endsWith('/presets') ? [...presets, azure] : { ...state, items: [] });
    vi.mocked(post).mockResolvedValue({ ...config, name: 'Azure OpenAI', preset: 'azure', config: { ...config.config, provider: 'azure_openai', model: 'team-model', base_url, api_version: expected } });
    const activated = vi.fn(); render(<ModelsPage onActivated={activated} />);
    fireEvent.change(await screen.findByLabelText('Provider preset'), { target: { value: 'azure' } });
    fireEvent.change(screen.getByLabelText('Deployment name'), { target: { value: 'team-model' } });
    const version = screen.getByLabelText(/Azure API version/) as HTMLInputElement;
    fireEvent.change(version, { target: { value: api_version } });
    fireEvent.change(screen.getByLabelText(/API key/), { target: { value: 'unit-only-azure-secret' } });
    expect(version.checkValidity()).toBe(true);
    expect(version.form?.checkValidity()).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Save configuration' }));
    await screen.findByText('Saved version 1. Test this saved version before enabling it.');
    expect(post).toHaveBeenCalledExactlyOnceWith('/admin/model-configurations', expect.objectContaining({ config: expect.objectContaining({ provider: 'azure_openai', base_url, model: 'team-model', api_version: expected }) }));
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
    expect(activated).not.toHaveBeenCalled();
  });
  it('preserves the provider preset thinking setting and sends an explicit advanced override', async () => {
    const options: ModelPreset[] = [...presets, { id: 'deepseek', name: 'DeepSeek', description: 'Verified alias; bounded output.', requires_api_key: true, config: { provider: 'openai_compatible', base_url: 'https://api.deepseek.com', model: 'deepseek-flash', thinking_enabled: false, structured_output_mode: 'json_object' } }];
    vi.mocked(request).mockImplementation(async path => path.endsWith('/presets') ? options : { ...state, items: [] });
    vi.mocked(post).mockResolvedValue({ ...config, preset: 'deepseek', name: 'DeepSeek', config: { ...config.config, ...options[2].config, thinking_enabled: true } });
    render(<ModelsPage onActivated={() => {}} />);
    fireEvent.change(await screen.findByLabelText('Provider preset'), { target: { value: 'deepseek' } });
    expect((screen.getByLabelText('Model name') as HTMLInputElement).value).toBe('deepseek-flash');
    expect((screen.getByLabelText(/Thinking mode/) as HTMLSelectElement).value).toBe('disabled');
    fireEvent.change(screen.getByLabelText(/Thinking mode/), { target: { value: 'enabled' } });
    fireEvent.change(screen.getByLabelText(/API key/), { target: { value: 'unit-only-secret' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save configuration' }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect(vi.mocked(post).mock.calls[0][1]).toEqual(expect.objectContaining({ config: expect.objectContaining({ thinking_enabled: true, structured_output_mode: 'json_object', model: 'deepseek-flash' }) }));
  });
  it('waits for an actual test result before enabling and uses its exact version/receipt', async () => {
    let finish: (value: ModelTest) => void = () => {};
    vi.mocked(post).mockImplementation(path => path.endsWith('/test') ? new Promise(resolve => { finish = resolve as (value: ModelTest) => void; }) : Promise.resolve({ ...state, active_version: 5, active_configuration_id: config.id, source: 'database', items: [{ ...config, latest_test: test, active: true }] }));
    const changed = vi.fn(); render(<ModelsPage onActivated={changed} />);
    await screen.findByRole('button', { name: 'Test connection' });
    const enable = screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement;
    expect(enable.disabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }));
    expect(screen.getByRole('button', { name: 'Testing connection…' })).toBeTruthy();
    expect(enable.disabled).toBe(true); expect(changed).not.toHaveBeenCalled();
    finish(test);
    await screen.findByText('Connection test passed');
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText('Test role'), { target: { value: 'checker' } });
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }));
    finish({ ...test, id: 'checker-1', role: 'checker' });
    await waitFor(() => expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole('button', { name: 'Enable tested version' }));
    await screen.findByText(/Model configuration enabled\./);
    expect(post).toHaveBeenLastCalledWith('/admin/model-configurations/config-1/activate', { test_id: 'test-1', checker_configuration_id: 'config-1', checker_test_id: 'checker-1', expected_active_version: 4 });
    expect(changed).toHaveBeenCalledTimes(1);
  });

  it('saves a new immutable version, clears entered secrets, and invalidates earlier test eligibility', async () => {
    setResponses({ ...state, items: [{ ...config, latest_test: test, latest_answer_test: test, latest_checker_test: { ...test, id: 'checker-1', role: 'checker' } }] });
    const saved = { ...config, id: 'config-2', revision: 2, config_hash: 'hash-2', config: { ...config.config, model: 'new-model' } };
    vi.mocked(post).mockResolvedValue(saved);
    render(<ModelsPage onActivated={() => {}} />);
    await screen.findByRole('button', { name: 'Enable tested version' });
    fireEvent.change(screen.getByLabelText('Model name'), { target: { value: 'new-model' } });
    const key = screen.getByLabelText(/Replace API key/) as HTMLInputElement;
    fireEvent.change(key, { target: { value: 'test-secret-never-persist' } });
    expect(key.type).toBe('password');
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Save new version' }));
    await screen.findByText('Saved version 2. Test this saved version before enabling it.');
    expect(post).toHaveBeenCalledWith('/admin/model-configurations/config-1/versions', expect.objectContaining({ api_key: 'test-secret-never-persist', config: expect.objectContaining({ model: 'new-model' }) }));
    expect((screen.getByLabelText(/Replace API key/) as HTMLInputElement).value).toBe('');
    expect(JSON.stringify(sessionStorage)).not.toContain('test-secret'); expect(JSON.stringify(localStorage)).not.toContain('test-secret');
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByText('Connection test passed')).toBeNull();
  });

  it('records a failed permission test without activating or claiming success', async () => {
    vi.mocked(post).mockResolvedValue({ ...test, status: 'failed', activation_eligible: false, diagnostic_code: 'PROVIDER_AUTH_ERROR', message: 'Permission denied.' });
    render(<ModelsPage onActivated={() => {}} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Test connection' }));
    await screen.findByText('Connection test failed');
    expect(screen.getByText('Check the API key and its permission to use this model.')).toBeTruthy();
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
    expect(post).toHaveBeenCalledTimes(1);
  });

  it('does not reuse a secret automatically for a changed service destination', async () => {
    render(<ModelsPage onActivated={() => {}} />);
    await screen.findByLabelText(/Base URL/);
    fireEvent.change(screen.getByLabelText(/Base URL/), { target: { value: 'https://different.example/v1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save new version' }));
    await screen.findByText('The service destination changed. Enter a key for this service or explicitly remove the saved key.');
    expect(post).not.toHaveBeenCalled();
    vi.mocked(post).mockResolvedValue({ ...config, id: 'config-2', revision: 2, has_api_key: false, api_key_masked: null, config: { ...config.config, base_url: 'https://different.example/v1' } });
    fireEvent.click(screen.getByRole('checkbox', { name: 'Remove the saved API key in the new version' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save new version' }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect(vi.mocked(post).mock.calls[0][1]).toEqual(expect.objectContaining({ clear_api_key: true }));
    expect(vi.mocked(post).mock.calls[0][1]).not.toHaveProperty('api_key');
  });

  it('keeps the active version unchanged on an activation conflict and blocks an uncertain retest', async () => {
    setResponses({ ...state, items: [{ ...config, latest_test: test, latest_answer_test: test, latest_checker_test: { ...test, id: 'checker-1', role: 'checker' } }] });
    const changed = vi.fn();
    vi.mocked(post).mockRejectedValue(new ApiError('CONFLICT', 'The active selection changed.', 409));
    render(<ModelsPage onActivated={changed} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Enable tested version' }));
    await screen.findByText('The active selection changed.');
    expect(changed).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'Enabled' })).toBeNull();
    vi.mocked(post).mockRejectedValue(new ApiError('CONNECTION_ERROR', 'The test response was lost.'));
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }));
    await screen.findByText('The test response was lost.');
    expect((screen.getByRole('button', { name: 'Enable tested version' }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('labels mock testing separately and makes encryption unavailability explicit', async () => {
    const mock = { ...config, has_api_key: false, api_key_masked: null, preset: 'mock', config: { ...config.config, provider: 'mock' as const, model: 'mock-v1', base_url: null }, latest_test: { ...test, model_mode: 'mock' as const } };
    setResponses({ ...state, encryption_ready: false, items: [mock] });
    render(<ModelsPage onActivated={() => {}} />);
    await screen.findByText('Mock check passed');
    expect(screen.getByText(/Encrypted key storage is unavailable/)).toBeTruthy();
    expect(screen.queryByText('Connection test passed')).toBeNull();
  });
});
