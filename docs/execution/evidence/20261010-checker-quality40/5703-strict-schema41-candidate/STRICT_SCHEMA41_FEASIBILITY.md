# Full V2 native schema transport feasibility

The current `gemini35_google_vertex_v1` route can prepare the full existing V2 response schema as `response_format.type=json_schema` with `strict=true`. The pure proof passed without model calls, credentials, database access, or Main writes. It does not establish live endpoint compliance or scientific correctness.

The original full compact schema remains **7,125 bytes**, SHA-256 `864212a5e636d2cadbc34328f431712a954c30130848a31e64e66e4bdedbc926`. For this actual schema, `provider_schema(..., "openai_compatible")` returns an equal schema. The V1 Gemini route has no schema projection or compact hydration policy. Required claim citations, unit assessments and `attempt_evaluation_ok` remain required. The canonical strict parser and source assessment gates must remain unchanged.

| Actual keyword | Count | Compatibility implication |
| --- | ---: | --- |
| `$defs` / `$ref` | 1 / 12 | Local definitions remain exact; Gemini JSON Schema refs are documented, while gateway translation must be observed. |
| `anyOf` | 3 | Existing portable discriminated branches remain. |
| `required` / `additionalProperties` | 12 / 12 | Mandatory fields and forbidden extra fields remain. |
| `const` | 4 | Kept unchanged; not individually established by the public supported-fields list for this endpoint. |
| `minLength` / `maxLength` / `pattern` | 16 / 19 / 1 | Kept unchanged; remote enforcement is unconfirmed, original local enforcement remains mandatory. |
| `minItems` / `maxItems` | 2 / 11 | Kept unchanged. |
| `enum` | 13 | Kept unchanged. |

The schema has no `oneOf`, `discriminator`, `uniqueItems`, or `default` keywords. The pure proof records 109 unexpanded schema nodes and maximum unexpanded depth 3. Expansion and provider translation are not measured by these counts.

Google's current Generate Content documentation explicitly lists Gemini 3.5 Flash-Lite as supporting structured outputs. It describes a subset of JSON Schema, warns that unsupported properties can be ignored and complex schemas can be rejected, and requires application validation of semantic values. [Google structured outputs](https://ai.google.dev/gemini-api/docs/generate-content/structured-output)

OpenRouter documents `response_format.type=json_schema`, recommends `require_parameters=true`, and explains that support and strict enforcement depend on the provider endpoint. Some endpoints translate schemas or treat them as strong hints. [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)

The public provider page did not expose an endpoint capability table to the web reader; the public model endpoint catalogue URL was unavailable through that reader. This is an unresolved observation, not a local compiler failure or proof that the fixed Vertex endpoint lacks support. No credential-bearing API discovery was performed.

The W-only helper `strict_schema41_transport_contract.py` prepares the minimal candidate: identical authored candidate40 system rules, source data and hints; change only the saved mode to `json_schema`. The automatic textual schema hint produced by JSON-object mode moves into `response_format` as the identical full schema. It asserts all other request controls remain equal, preserves the fixed Vertex route and low reasoning, and performs no calls or credential access.

Root's finite launcher must separately freeze the actual complete planned wire, verify the fixed original 10 claims / 19 units / 71 source blocks, prove wire size at most 98,304 bytes, and seal the prior closed group of 20 POSTs / USD 0.17182790 plus a fresh one-request maximum USD 0.045. A provider 400, embedded gateway error, invalid schema response, partial source support or UNKNOWN cost is a retained failure. Do not retry, remove schema constraints, flatten branches, auto-fill citations, alter returned raw output, enable fallback, or publish without the full original quality gates.

Only local request preparation is established. Native UI time to complete answer, repair avoidance and source support are not measured by this proof.
