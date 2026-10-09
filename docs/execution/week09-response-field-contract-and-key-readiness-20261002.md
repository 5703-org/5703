# Response field contract and first-use model key readiness

Two repairs were integrated after the frozen V20 four-book development runs and the complete mock learning journey. Their exact before bytes are retained in private source-cutover records. Current complete-gate and installed acceptance results are tracked separately from those earlier source identities.

## Response transport

Fresh G010 generation and format-repair outputs conflicted with the existing answer/refusal field invariants. New ordinary chat requests now freeze `CHAT_PROVIDER_OUTPUT_POLICY=json_field_contract_v2` in the server-owned immutable command. The worker uses that recorded value on execution and retry. Existing commands missing the field use `strict_v1`; the `GenerationRequest` default remains `strict_v1`.

The new policy supplies complete legal field examples to initial generation and the one existing format repair. Answers, clarifications and social replies require a null refusal reason. Genuine refusals require an allowed reason, empty citations and follow-up questions, and null short answer and confidence. Supported partial answers can describe their specific evidence limitation as an answer; factual support and completeness still pass the existing checks. The parser continues to reject contradictory fields and invalid citation markers. No output is altered to force validation.

Claim-patch repair retains its own schema. Empty provider output under the new policy remains a terminal strict failure. The historical `json_example_once_v1` recovery and strict policy paths retain their behavior. Ordinary chat continues to default to full textbook answers with checker V5, four calls, 180 active seconds and a 3,000-token evidence ceiling. E0/E1 producers and definitions remain unchanged.

The private candidate passed twenty-three authored transport tests with actual generator/parser/checker code and network connections denied. The first seventeen-pass/five-failure fixture run remains retained; its test-helper construction was corrected. Four disposable PostgreSQL/API cases were authored to check frozen commands, retries, historical defaults and invalid-policy failure before a model call. Their actual execution belongs to the new unified gate. Candidate tests establish software behavior; independent answer-quality labels and human scores are zero.

Affected code: [server settings](../../backend/app/core/config.py), [chat producer and worker consumer](../../backend/app/modules/answering/service.py), [checked generation](../../generation/checked.py), [legacy chat generation](../../generation/service.py), [field instructions](../../generation/response_field_contract_v2.py), and [environment example](../../.env.example).

## First-use encryption readiness

An installation with an absent key file could disable the administrator's API-key input before any save action could create the deployment key. Development readiness now uses the existing atomic restricted key-creation path. Production still requires a configured key. Existing keys and ciphertext remain unchanged; an invalid environment key or invalid file fails explicitly without replacement.

Five focused tests use real Fernet and temporary files, with the Windows ACL command mocked. A separate native Windows candidate check created a usable 44-byte key with inheritance disabled and only the current owner's FullControl permission, then verified repeat readiness and decryption of existing local test ciphertext. That check performed no database, API, browser or provider operation. Current installed first-administrator GET and browser acceptance have their own receipts; the candidate Windows check is not their substitute.

Affected code: [credential storage](../../backend/app/modules/model_settings/secrets.py) and [focused tests](../../tests/unit/test_model_settings_key_readiness.py). Neither repair changes official sources, vectors, existing answers, environment secrets or historical model records.

## Current validation boundary

The complete mock gate passed all eight stages on 848 identical source inputs, with 2,832 Python tests and 182 frontend tests and no failures, errors or skips. Its [actual checkpoint](../../evidence/week09-continuation/20261001/current-field-contract-key-software-checkpoint-20261002.json) ended at 2026-10-02T07:38:00.809934+00:00. The first complete gate retained two historical-request fixture failures and two import-lock fixture errors. Historical fixtures now omit the newer provider-policy field and verify its strict legacy fallback; the second disposable import database verifies the exact configured loopback server and retains its random test-only name. Nine focused cases passed after correction. The first focused assertion mistakes and their logs remain preserved. Product legacy V4 execution was unchanged. Current CPU installation, first administrator's Models page, the real memory-effect run and the G010 transport repeat remain pending separate current-source evidence. The chemistry anchor gap and G005 D checker contradiction remain in the [four-book development record](week09-four-book-grouped-development-20261002.md).
