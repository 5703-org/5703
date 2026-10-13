# Configured DeepSeek/OpenAI checker capability comparison

Both configured models produced readable, legally mapped short outputs for all six tasks. Neither passed scientific admission: DeepSeek had four false support certifications; OpenAI had three false support certifications and one false insufficiency. Each was correct on six of ten selected-proof judgments. The original inhibitor-conformation false refusal and cross-fragment continuation controls were handled correctly; generic-scope false certification remained in both models. No default or application integration was changed.

## Concrete models and six task classes

The existing local public configurations were freshly inspected, then bound to the actual returned model IDs. No guessed model, new credential, alternate endpoint or fallback was introduced.

| Setting | DeepSeek | OpenAI |
|---|---|---|
| Configured and returned model | `deepseek-flash` | `gpt-6-luna` |
| Actual endpoint | `https://api.deepseek.com/v1/chat/completions` | `https://api.openai.com/v1/chat/completions` |
| Structured output | JSON object | Strict JSON Schema |
| Reasoning | `thinking.type=disabled` | `reasoning_effort=none`; returned reasoning tokens 0 |
| Output ceiling | `max_tokens=1024` | `max_completion_tokens=1024` |
| Temperature | 0 | 0 |

OpenAI's documented token parameter, explicit none effort, default service tier and `store=false` were experiment-only adaptations of the saved profile. DeepSeek did not return a reasoning-token detail; its absence is not a measured zero. The models and structured capabilities were checked against [DeepSeek's official documentation](https://api-docs.deepseek.com/quick_start/pricing/) and [OpenAI's model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna). [OpenAI's GPT-6 guide](https://developers.openai.com/api/docs/guides/latest-model) supports temperature with none effort. A fetch of DeepSeek's dedicated JSON guide failed; its pricing/capability declaration and the actual counted warmups supplied the support evidence.

All six task messages were frozen before execution and identical between providers. Program code fixes target IDs and legal reference domains. Each model returns only ID, status and selected reference IDs. No teacher draft, reference answer, expected label or reviewer rationale was sent. The first sufficient and insufficient tasks ran once per provider; both providers then qualified structurally for the remaining four pairs. Semantic agreement was measured, not used to hide a failed warmup. The six tasks contain ten judgments over five original units, including a deliberate repeated activity negative; they are not ten independent questions.

| Task/class | DeepSeek | OpenAI | Direct finding |
|---|---|---|---|
| 01: sufficient inhibitor conformation/affinity, C004.U02 | Correct support with F004+F005 | Correct support with F004+F005 | Original unit-level false refusal resolved locally |
| 02: activity without a rate bridge, C009.U07 | False support with F009/F014 | Correct insufficiency | Missing-bridge rejection available in OpenAI; unresolved in DeepSeek |
| 03: generic allosteric-site location, insufficient/sufficient pair | Negative falsely supported; positive correct | Negative falsely supported; positive selects only F009 and remains uncertified | Scope error unresolved in both; a matching positive status is not sufficient proof |
| 04: generic conformation, sufficient/insufficient pair | Positive correct; negative falsely supported | Positive correct; negative falsely supported | Generic conclusion from activator-only evidence unresolved in both |
| 05: activity, missing/complete bridge pair | Negative falsely supported; complete bridge correct | Negative correct; complete bridge falsely refused | DeepSeek is too permissive; OpenAI is too restrictive on the paired positive |
| 06: complete/truncated allosteric-activator continuation, C007.U01 | Both correct | Both correct | Joint proof and genuine missing-continuation controls resolved locally |

The activity positive is a bounded qualitative textbook relation under its stated conditions, not an unconditional kinetic theorem. Task03's added F040 and task05's added F045–F047 are explicitly controlled source rebinding outside their historical parent domain; they do not repair or requalify old answers. All source text and provenance were retained. The other sufficient controls use their original parent domains.

## Structure, selected proof and attribution

Twelve physical requests completed with provider `stop`; all twelve strict JSON/coverage/reference checks passed, yielding twenty legal judgments and no unassessed rows. Scientific selected-proof review found:

- DeepSeek: 6 correct, 4 false support certifications, 0 false insufficiencies.
- OpenAI: 6 correct, 3 false support certifications, 1 false insufficiency. Its status-only agreement is 7/10, but task03's sufficient row omitted F040 and selected the same inadequate F009 as its negative, reducing selected-proof agreement to 6/10.

These observations separate transport reliability from entailment reliability. The short task is demonstrably solvable for the inhibitor and joint-continuation cases. The activity tradeoff differs by model. Generic-scope false certification survives across both configured models, so it cannot be blamed solely on the previous Gemini transport or cured by a cheap replacement. The experiment does not causally distinguish model training from semantic task framing: versus Phase91 it narrows the evidence domains, removes the full teacher context and uses smaller batches; provider structured modes and effort also differ. The remaining generic scope/selected-evidence obligations need implementation and evaluation work before publication. No same-direction prompt loop or further request was started.

Ten finite in-memory runner guard groups and the recorded two-file Ruff check passed before execution. The [small reproduction archive](20261012-checker92-reproduction.zip) contains frozen messages, public configuration/price records, raw observations, independent review, code and entry hashes. Extract it and run `python -B reproduce92.py` to replay all twelve short decodes, same-message bindings, wire claims and numerical usage bounds without a credential, database, model request or write. This replay is not a semantic oracle or a full application test. Local delivery is verified in the [readback receipt](20261012-checker92-readback.json).

## Budget and project boundary

The independent allocation was twelve requests maximum, DeepSeek CNY1 and OpenAI USD0.30. All twelve physical slots were used: six per provider, with twelve numerical usage observations. Conservative token-tariff bounds are **CNY0.011802** and **USD0.00093060**, respectively; current-batch UNKNOWN is zero for each provider. They are not invoice debits. DeepSeek uses peak uncached input/output protection from its [official CNY price table](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/); OpenAI uses a protection rate above its [standard price table](https://developers.openai.com/api/docs/models/gpt-6-luna). Currencies were neither added nor converted. Old UNKNOWN records remain separate and unchanged. No retry, price-based model promotion or request beyond the twelve-slot allocation occurred.

The first metadata proposal was automatically rejected because it added unnecessary credential presence/character checks. Those fields were removed before the approved public-only inspection. Actual execution used the existing two credentials solely in necessary in-memory authentication headers; no secret value/hash/copy was exported and the private profile was not modified. There is no remaining authorization blocker in this batch.

The fixed-ID Main module remains default-off with SHA256 `cfa5948069edcbddcc504a59fac7cf178c58bb743ac13d2b691974e9397e991f`; existing production B16 source and previous results remain intact. This phase adds a locally archived Week10 diagnostic implementation and result, with append-only progress/handover entries. It does not write the other window's Week9 report, change defaults, touch a database, install dependencies, rerun the full unit suite or perform remote publication/submission.

Neither candidate qualifies for default adoption or a full-answer trial on these results. Local negative controls and the complete question-to-answer path must both pass before adoption. No complete question/answer, application publication, DOM, heldout RAG/Human Gold, TTFT or p95 result was obtained here. Project/course completion and quality-qualified complete-answer latency remain open.
