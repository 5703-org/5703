# Compact127 same-input provider diagnostic

Four independent checker slots were authorized: S01 and S02 positive controls on existing DeepSeek and OpenAI configurations, with separate CNY0.25 and USD0.05 upper budgets. Actual outcomes below retain failed and unrun units. No generation, repair, retry or increased output limit was permitted.

| Provider / case | Status | Native valid | Complete citation groups | Accepted / FR | Input / output tokens | API ms | Currency upper / UNKNOWN |
| --- | --- | --- | --- | --- | --- | --- | --- |
| deepseek / S01 | VALID_SEMANTIC_RESULT | True | True | True / False | 7831 / 410 | 2397.5 | CNY 0.018942 / 0 |
| deepseek / S02 | TECHNICAL_STOP | False | True | None / None | 7807 / 369 | 2193.3 | CNY 0.018566 / 0 |
| openai / S01 | VALID_SEMANTIC_RESULT | True | True | False / True | 7743 / 375 | 4765.8 | USD 0.00234825 / 0 |
| openai / S02 | TECHNICAL_STOP | False | True | None / None | 7691 / 360 | 4126.6 | USD 0.00231875 / 0 |

## Request identity and methodology

Configured model IDs are deepseek-flash at https://api.deepseek.com/v1/chat/completions and gpt-6-luna at https://api.openai.com/v1/chat/completions. Exact configured aliases were checked against fresh public documentation; account availability was not assumed. S01/S02 contain the same frozen questions, saved answers, full64/54 textbook source passages, strict compact schema and positive labels across providers. Original citation groups are pre-enumerated7/4, with every group required exactly once. Temperature0 and output limit4096 are fixed. DeepSeek uses max_tokens and disabled thinking; OpenAI uses max_completion_tokens and reasoning_effort=none. No endpoint substitution or saved-profile change occurred.

The actual serializer compilation from126 is frozen; the DeepSeek serializer was recompiled before127. OpenAI local o200k request estimates8002/7982 plus2048 framing reserve and4096 output fit the existing16384 configured window. These are local admission estimates, not provider-exact token counts. JSON-object output and the embedded strict schema are common to both; native validation enforces schema, provenance, ownership, quote uniqueness and semantic gates.

Execution order was DeepSeek S01, DeepSeek S02, OpenAI S01, OpenAI S02. Cache state was not equalized: DeepSeek reported0/768 cached input tokens, while OpenAI reported0 cached hits and7740/7688 cache-write tokens. Pricing protection covers those writes. The sequence and cache differences are further reasons not to infer a causal latency advantage from these four observations.

Actual POSTs use the exact frozen endpoint/body with an audit boundary, no redirects or retries, live source/caller pins and a30-minute public-price receipt age. Returned bytes are retained unchanged after privacy validation. Each returned response is then replayed through the unchanged full native application runner using the common frozen generation context. This offline scoring replay issues no model request; its simulated ledger is not actual provider billing. Real request lineage, usage and currency protection are recorded separately.

Complete citation assessment counts the exact pre-enumerated group keys with explicit S/I/C decisions under duplicate-key/nonfinite rejection; it is separate from native task validity. Null means coverage could not be established. Acceptance and false rejection are only scored for native-valid results. Missing/unassessed/truncated/invalid results remain unscored. Positive labels are controlled fixture labels, not formal human quality ratings.

## Currency protection and outcomes

The [DeepSeek price documentation](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/) supplies conservative peak rates2/8 CNY per million input/output tokens. The [OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna) lists standard0.10/0.50 USD, cache-write0.125 and fast-rate multipliers. Protective OpenAI rates0.25/1.1 USD per million cover those documented modifiers for these small requests. Input reservations use wire bytes+2048 and full4096 output; total pre-reservations are CNY0.183806 and USD0.02379595. These protective upper estimates are not invoices or converted currencies.

Actual checker requests: 4; dispatch intents: 4. Totals: `{"deepseek": {"currency": "CNY", "known_upper": "0.037508", "unknown_hold": "0"}, "openai": {"currency": "USD", "known_upper": "0.00466700", "unknown_hold": "0"}}`.

Unknown or abnormal usage retains at least the full hold, or the larger observed protective cost, and stops the affected provider. The other currency remains independently eligible. Five free metering counterexamples, two strict-JSON controls and seven financial-observation/audit/prewire boundary controls passed before dispatch. Original125/older raw responses, scores and holds remain unchanged.

### deepseek-S01-positive-B

```json
{
  "status": "VALID_SEMANTIC_RESULT",
  "reason": null,
  "pipeline_error": null,
  "response_model": "deepseek-flash",
  "finish_reason": "stop",
  "validation_state": "validated",
  "checker_inconsistencies": [],
  "structural_issues": [],
  "failed_rules": null
}
```

### deepseek-S02-positive-B

```json
{
  "status": "TECHNICAL_STOP",
  "reason": null,
  "pipeline_error": {
    "code": "QUALIFICATION_CONTRACT_INVALID",
    "message": "The opt-in checker returned invalid metadata; no correction call or answer publication",
    "retryable": false,
    "details": {
      "issue_codes": [
        "SOURCE_REFERENCE_OUTSIDE_ACTUAL_CITATIONS"
      ]
    }
  },
  "response_model": "deepseek-flash",
  "finish_reason": "stop",
  "validation_state": "checker_inconsistent",
  "checker_inconsistencies": [
    {
      "code": "SOURCE_REFERENCE_OUTSIDE_ACTUAL_CITATIONS"
    }
  ],
  "structural_issues": null,
  "failed_rules": null
}
```

### openai-S01-positive-B

```json
{
  "status": "VALID_SEMANTIC_RESULT",
  "reason": null,
  "pipeline_error": {
    "code": "SEMANTIC_CHECK_FAILED",
    "message": "The proposed answer did not pass its required support or teaching checks",
    "retryable": false,
    "details": {
      "revision": 0,
      "publication_block": {
        "version": "semantic_publication_block_v1",
        "stop_reason": "insufficient_calls_for_repair_and_recheck",
        "remaining_provider_calls": 0,
        "required_calls_for_repair_and_recheck": 2,
        "checker_contract_repair_calls": 0,
        "checker_reported_body_ok": true,
        "checker_reported_non_supported_factual_claims": 0,
        "failed_checker_gate_names": [],
        "checker_reported_coverage": "full",
        "requirement_issue_codes": [],
        "structural_issue_codes": [
          "ACTUAL_CITATION_IRRELEVANT",
          "SOURCE_CONDITION_CHANGED",
          "SOURCE_RELATION_CHANGED"
        ]
      }
    }
  },
  "response_model": "gpt-6-luna",
  "finish_reason": "stop",
  "validation_state": "validated",
  "checker_inconsistencies": [],
  "structural_issues": [
    {
      "code": "SOURCE_RELATION_CHANGED",
      "claim_id": "claim_19b9e595808de6beb9f1697d_1",
      "unit_id": "U01"
    },
    {
      "code": "SOURCE_CONDITION_CHANGED",
      "claim_id": "claim_19b9e595808de6beb9f1697d_1",
      "unit_id": "U01"
    },
    {
      "code": "SOURCE_RELATION_CHANGED",
      "claim_id": "claim_19b9e595808de6beb9f1697d_1",
      "unit_id": "U02"
    },
    {
      "code": "SOURCE_CONDITION_CHANGED",
      "claim_id": "claim_19b9e595808de6beb9f1697d_1",
      "unit_id": "U02"
    },
    {
      "code": "SOURCE_RELATION_CHANGED",
      "claim_id": "claim_eee180277f923411b6918542_1",
      "unit_id": "U01"
    },
    {
      "code": "SOURCE_CONDITION_CHANGED",
      "claim_id": "claim_eee180277f923411b6918542_1",
      "unit_id": "U01"
    },
    {
      "code": "SOURCE_RELATION_CHANGED",
      "claim_id": "claim_72a93f1dcaf440f8e5709bfc_1",
      "unit_id": "U01"
    },
    {
      "code": "SOURCE_CONDITION_CHANGED",
      "claim_id": "claim_72a93f1dcaf440f8e5709bfc_1",
      "unit_id": "U01"
    },
    {
      "code": "SOURCE_RELATION_CHANGED",
      "claim_id": "claim_72a93f1dcaf440f8e5709bfc_1",
      "unit_id": "U02"
    },
    {
      "code": "SOURCE_CONDITION_CHANGED",
      "claim_id": "claim_72a93f1dcaf440f8e5709bfc_1",
      "unit_id": "U02"
    },
    {
      "code": "SOURCE_RELATION_CHANGED",
      "claim_id": "claim_72a93f1dcaf440f8e5709bfc_1",
      "unit_id": "U03"
    },
    {
      "code": "SOURCE_CONDITION_CHANGED",
      "claim_id": "claim_72a93f1dcaf440f8e5709bfc_1",
      "unit_id": "U03"
    },
    {
      "code": "SOURCE_RELATION_CHANGED",
      "claim_id": "claim_72a93f1dcaf440f8e5709bfc_1",
      "unit_id": "U04"
    },
    {
      "code": "SOURCE_CONDITION_CHANGED",
      "claim_id": "claim_72a93f1dcaf440f8e5709bfc_1",
      "unit_id": "U04"
    },
    {
      "code": "ACTUAL_CITATION_IRRELEVANT",
      "claim_id": "claim_72a93f1dcaf440f8e5709bfc_1"
    }
  ],
  "failed_rules": null
}
```

### openai-S02-positive-B

```json
{
  "status": "TECHNICAL_STOP",
  "reason": null,
  "pipeline_error": {
    "code": "QUALIFICATION_CONTRACT_INVALID",
    "message": "The opt-in checker returned invalid metadata; no correction call or answer publication",
    "retryable": false,
    "details": {
      "issue_codes": [
        "SOURCE_REFERENCE_OUTSIDE_ACTUAL_CITATIONS"
      ]
    }
  },
  "response_model": "gpt-6-luna",
  "finish_reason": "stop",
  "validation_state": "checker_inconsistent",
  "checker_inconsistencies": [
    {
      "code": "SOURCE_REFERENCE_OUTSIDE_ACTUAL_CITATIONS"
    }
  ],
  "structural_issues": null,
  "failed_rules": null
}
```

## Interpretation and evidence

Both S02 failures are supporting-quote scope violations, not missing citation groups or truncation. DeepSeek uses quote pointers17/18/15 that resolve to source14/15/12 outside the corresponding claim's selected group-S sources; OpenAI uses pointer23 resolving to source17 while selecting source18. The source-number and quote-pointer namespaces differ. DeepSeek's repeated use of source numbers as quote pointers suggests namespace confusion; this is an inference from the unchanged wire, not proof of the model's reasoning. No pointer was remapped or borrowed evidence added.

OpenAI S01 explicitly marks G5 irrelevant and every unit's relation/condition preservation as neither. Native gates report ACTUAL_CITATION_IRRELEVANT, SOURCE_CONDITION_CHANGED and SOURCE_RELATION_CHANGED. This is a complete, technically valid negative judgment and counts as false rejection against the frozen positive fixture label. It differs from the historical125 omitted-assessment case, which stays unscored under current classification. DeepSeek S01 accepts with all groups assessed and preservation flags explicit.

DeepSeek compact is the practical candidate for the next controlled development step because it produced one complete native acceptance and short outputs on both cases. It is not ready for default activation: S02 must pass without quote-scope errors. The next offline change should make source and quote identities structurally distinct and expose role-scoped quote choices, rather than silently translate model pointers or weaken native scope checks. OpenAI remains a separate comparison candidate; its explicit semantic/preservation rejection requires diagnosis. No additional requests or code changes are included in127.
This small positive-only diagnostic helps identify an executable checker path. Two cases cannot establish a provider winner, false-accept performance, general scientific reliability or causal speedup. Inspect individual native judgments before choosing a next experiment. No production default was activated. Unified-condition RAG quality and native page send-to-complete-answer timing remain open.

Evidence directory: C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-compact127-real. Final prepared manifest SHA256 `52f2876e78d606beb6d4212607c9b867298c2d90a771d9937c1701c746cf008d`; actual result SHA256 `ef4abd1a70d60754969a938f87cec498757f30be445b7e3aa403d12381b9da48`. Per-unit SEND_INTENT, raw response, currency settlement/unknown protection, result and native replay receipts retain failed/unrun units. Read-only independent review receipts are retained alongside these artifacts.

Only this report and append-only progress/handover checkpoints are added to Main. No project code/default/profile/credential/database/experiment-input changes, installs, archives, remote publication, deployment or course submission occurred.
