# Answering model administration

Sign in as an administrator, open **Administration > Models**, choose a provider preset, and enter the endpoint, available model name and API key. Use **Save configuration**, **Test connection**, then **Enable**. Saving creates a revision; it does not change the active model. A successful test belongs to that exact revision. A later failed test prevents its activation until a new test passes. A mock test is labelled explicitly and makes no external request.

## Supported protocol settings

| Provider / deployment | Protocol and base URL | Model and useful settings |
| --- | --- | --- |
| DeepSeek | OpenAI compatible; `https://api.deepseek.com/v1` | The account used on 13 September 2026 exposes `deepseek-flash`. Use JSON object output and disabled thinking for the verified 1,024-token answering configuration. Model availability is checked on the actual account. |
| OpenAI | OpenAI; `https://api.openai.com/v1` | Enter an available model. Advanced settings expose its supported output-token parameter and JSON mode. Optional `reasoning_effort` is available through the configuration API. |
| Azure OpenAI v1 | Azure OpenAI; `https://RESOURCE.openai.azure.com/openai/v1` | Model is the deployment name; authentication uses `api-key`. Leave API version empty for the v1 endpoint. A dated deployment endpoint may include `/openai/deployments/DEPLOYMENT` in its base and a separate API version field. |
| Anthropic | Anthropic; `https://api.anthropic.com/v1` | Native Messages protocol with `x-api-key` and a separate Anthropic version. The preset uses prompt-based JSON; local validation always applies. |
| Google Gemini | Gemini; `https://generativelanguage.googleapis.com/v1beta` | Native generateContent protocol and `x-goog-api-key`. Native token counting is available when the tokenizer setting selects provider/auto. |
| Gemini compatible endpoint | Custom compatible; `https://generativelanguage.googleapis.com/v1beta/openai` | Select OpenAI-compatible wire format and the provider's available model. |
| Ollama | Ollama; `http://127.0.0.1:11434/v1` | Use an installed local model. The local default needs no key. A container's loopback refers to that container. |
| Other compatible services | Custom compatible; the service's documented API base | Enter the model, credential and supported JSON mode. The configuration API supports optional `auth_header` overrides; the browser uses the selected protocol's standard header. The connection test reports protocol failures explicitly. |

The application supports Chat Completions, native Anthropic Messages and native Gemini generateContent. Provider-specific APIs with different contracts require an adapter. Vendor models can differ in structured-output, temperature and token-limit support; these remain editable instead of being guessed from the provider name. HTTPS is required for remote calls; local HTTP is restricted to loopback. Redirects are not followed with credentials. Put API versions in their field and credentials in the key field, never in URL query parameters.

## Keys, revisions and running work

Keys are write-only. Responses show `********` and a key-present flag. The database stores encrypted credentials separately from immutable public configuration revisions. `MODEL_CONFIG_KEY_FILE` defaults to `.secrets/model-config.key`; alternatively supply `MODEL_CONFIG_ENCRYPTION_KEY`. Development creates a restricted key file when needed. Production requires provisioned key material. API, worker and evaluator must read the same persistent key. The Compose deployment shares the dedicated key volume, with read-only worker/evaluator access.

Blank key input on a successor revision retains its existing credential. Changing the provider or destination origin requires an explicit replacement or clear action. A cleared managed key never inherits `LLM_API_KEY`. Changing the active configuration affects newly submitted requests. Queued/running requests resolve the credential associated with their frozen revision; previous answers and experiments retain their configuration identity. Environment configuration remains available through an explicit administrator action. Missing credentials/configuration produce an error; a live failure never selects the mock adapter.

Back up deployment credentials and their encryption key through a private operator procedure. The previous corpus/history backup script does not copy the deployment key file. Complete portable handovers exclude `.env`, `.secrets`, existing model-setting records and learner histories. Configure a new deployment's own key and provider after installation.

## Token limits and diagnostics

The current limits remain 3,000 evidence tokens, 2,000 history tokens, 512 summary tokens, 1,024 chat output tokens and 768 MCQ output tokens, subject to the complete model context window. Known OpenAI tokenizers use verified local tiktoken resources; a fixed local Hugging Face tokenizer can be configured. Native Anthropic/Gemini count calls share the request's four-call and 180-second cumulative budget. An unavailable tokenizer either fails explicitly or uses the configured, labelled estimate. Local text tokenization is exact for its configured tokenizer; whole-request framing includes a conservative reserve and is labelled estimated unless a provider supplies a count.

The local DeepSeek tokenizer is `deepseek-ai/DeepSeek-V4-Flash-0731` at `7872f01b1d1fe23eabc4c98b48bffcef5a386062`. Source manifest and file hashes accompany the assets. The service exposes a mutable model alias and does not disclose an immutable checkpoint identity, so tokenizer-family equivalence is not asserted as a provider guarantee. Recorded provider usage is the authority for actual consumed tokens.

Open **Diagnostics** to inspect the question, frozen model, processing stages, safe error, call budget and separate candidate/submitted/cited counts. **Sources** in a learner answer lists the passages actually cited by that answer. Correct citation IDs and hashes establish traceability; semantic support still requires reviewing the cited text. **Accounts** creates users, changes status and resets passwords. Password changes revoke existing login tokens. These administrator operations are scoped to the current workspace.

## Protocol references

Reviewed on 13 September 2026: [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/), [DeepSeek JSON output](https://api-docs.deepseek.com/guides/json_mode/), [Azure OpenAI REST](https://learn.microsoft.com/en-us/azure/foundry/openai/latest), [Anthropic API](https://platform.claude.com/docs/en/api/overview), [Gemini compatibility](https://ai.google.dev/gemini-api/docs/openai), [Ollama compatibility](https://docs.ollama.com/api/openai-compatibility), and [LiteLLM administration](https://docs.litellm.ai/docs/proxy/ui). These references support protocol and workflow choices; they do not certify every provider/model combination in this project.
