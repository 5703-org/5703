# Week 8 Work Report

Zeping Liao | Backend state permissions and lifecycle | 2026-09-22

## Week 8 contribution

Persist typed memory and staged compatibility tests alongside existing accounts, chat and worker services. Historical answers and encrypted credential references remain protected while the UI receives safe, actionable current state.

Original task allocation: BE-01, BE-02, BE-03, BE-04, BE-05, BE-06, BE-07, BE-08, BE-09, BE-10, BE-11, BE-12, BE-13, BE-14, BE-15, BE-16, BE-17, CHAT-02, CHAT-03, CHAT-08.

## Completed implementation

Additive tables extend memory provenance, revisions and compatibility receipts. Existing table-column fingerprints are preserved. Workspace permissions, compare-and-swap mutations and deletion fences continue to protect concurrent requests.

Submission freezes separately resolved answer/checker versions and applicable memory context. Current corrections can affect the answer without waiting for extraction. Memory availability and provider failure are distinct safe trace fields; rejected private checker commentary is not a public error.

Compatibility suites commit starts and stage reservations before transport. Idempotency retrieves the same receipt, conflicting suites fail, and uncertain work is not silently replayed. Activation checks current schema/config hashes for both roles before pointer CAS.

## Interfaces and operation

Pengyuan supplies memory semantics, Sijin the capability/checker contract, Xianshu shared orchestration, Baiqing safe DTO consumers, and Chong real PostgreSQL concurrency and lifecycle checks.

- Inspect the authenticated workspace and separate answer/checker receipts.

- Read typed provider causes and memory availability without raw private payloads.

- Reproduce concurrency and recovery only in dedicated accounts or disposable databases.

## Verification and findings

The database migration extended memory provenance and provider compatibility while preserving original-column counts and hashes for all 44 existing tables. Memory changes use expected revisions and source ordering. Settings epochs, suppressions and tombstones fence delayed work after disable, correction or deletion.

Actual isolated HTTP checks cover owned source reads, question preview, state updates, worker cancellation and assessment provenance. Another account cannot obtain a memory source through its identifier. Imported assessment scores stay unconfirmed, while real exact-text or numeric scoring retains its rubric and source identities.

Provider test starts and reservations are durable, and activation checks separate answer and checker eligibility before changing the versioned pointer. The real DeepSeek activation preserved the answer revision and bound the successful checker receipt. A lost or uncertain attempt retains its receipt rather than silently becoming a new successful call.

The fresh portable database used distinct ports and no original learner history or deployment credentials. Its two persisted chat turns, cancellation and history reload passed with mock answering and real CPU retrieval. The final source/resource parity check left the application processes stopped and the database volume preserved.

The completed numerical report retains all planned outcomes for the assigned studies, including failures and human-dependent oracle cases. Domain accountability does not imply that the member personally executed the recorded automated work.

| Study | Recorded | Planned |
| --- | --- | --- |
| Study M Learning Memory | 180 | 180 |

## Current limits

Installation has its own recorded runtime checks. A timeout can leave provider completion uncertain; the saved receipt preserves that state. Quota, network access and model compatibility require live provider observations.

Recovery work should retain uncertain provider attempts and use dedicated accounts or disposable databases. Additional erasure and operational drills require explicit scope, and live access or quota availability remains specific to the tested provider and network.

## Week 9 goals

- Investigate recovery failures without replaying uncertain paid attempts.

- Verify derived-data erasure under explicit authorized scope.

- Extend isolated operational drills and retain historical fingerprints.

## Code and evidence

Module paths: backend/app/modules/learning_state/models.py; backend/app/modules/learning_state/memory_v2.py; backend/app/modules/model_settings/compatibility.py; backend/app/modules/model_settings/service.py; backend/app/modules/answering/diagnostics.py.

Codex performed the implementation, automated checks and recorded local browser verification through the shared project workflow. The eight reports follow the original accountable domains; member submissions and independent human reviews retain their own execution records.

Additive migration preservation. Existing-column contents and counts in 44 prior tables remained unchanged through migration e0a64c7d123b, including the preceding memory revision.

evidence/week08-memory-v2/20260921/migration/preservation-result.json

SHA256 986740e61b25c75ca3b199409b295fa1f0bc572d9c7c66e98b41c25d4cc18413

Memory implementation checkpoint. 45 focused Python checks and the dated component/build/browser checkpoint; the recorded pre-formal status belongs to this earlier checkpoint.

evidence/week08-memory-v2/20260921/memory/implementation-checkpoint.json

SHA256 879a6ed51d67605fd9fad3a11388e689dad6198f5a6390e9ae49c09b6e9f0d43

Separate role activation receipt. The existing answer revision was retained while the verified checker selection was added through the actual versioned activation route.

evidence/week08-memory-v2/20260921/providers/deepseek-paired-activation.json

SHA256 ca857c496eb48ca7f78ee71cd11b528c34de25715c91cfcd935ecc6b6aea58c9

Actual portable CPU HTTP workflow. Two persisted textbook turns, cancellation, source identities and history after sign-in on the separate database; explicit mock answering.

evidence/week08-memory-v2/20260921/portable/http-attempt1.json

SHA256 ee7c79530f7ebfcfed4f44322bffd8143b75a65219f2121f725820d69b7412f6

Final public source and resource parity. 514 selected source and configuration files match the portable public tree; all 80 resources match the preserved bundle, including 30 model and tokenizer files also compared with main paths

evidence/week08-memory-v2/20260921/portable/source-parity-release-final-20260922.json

SHA256 66cb3799d646b1b9d52dea9f442538f6ca9560b44db9d7ebcc9419c6705c0ccb

Registered automatic study results. 552 scheduled requests across 18 arms; all generation and offline judgment outcomes retained; independent human ratings zero

evidence/week08-memory-v2/20260921/formal/public-results.json

SHA256 b470c9c5df020d3dd7dae9625fdfabc82afdf60569f33a3d62c84a5ea340e7f6

Actual blank blinded review export. Two randomized 552-row reviewer slots; zero completed or imported ratings

evidence/week08-memory-v2/20260921/formal/review-export-verification.json

SHA256 9f9f675f3f00a30b7e64745be7d9ef0f2d2786295fb2cbdbc5a6a43041a75b5a

Reconciled actual attempt accounting. Development, provider diagnosis, extraction, summary, formal answers and offline judging; dated tariff estimates including failures

evidence/week08-memory-v2/20260921/accounting/final.json

SHA256 eb79da9c78412c5ce5d7196d18ffea6df5aa53d97eca336e07cacde82def7559
