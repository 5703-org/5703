# Memory V2 implementation checkpoint — 21 September 2026

The current implementation adds typed, attributable learner state and a query-conditioned reader. Ordinary textbook/direct chat remains the default. The application persists explicit statements and recorded evidence; it makes no general mastery inference. Current-turn instructions take priority over relevant subject preferences, saved global profile settings, global memory preferences and evidence-gated observations, in that order.

## Domain and storage

`personalisation/memory_v2.py` defines stable field identities, category-compatible keys, versioned science-topic aliases, deterministic explicit correction/erasure recognition and bounded selection. Categories cover preferences, goals, course context, self-reported difficulty/confidence and individual assessment performance. Synonyms resolve to the same canonical field; global and subject scopes retain distinct keys. The alias dictionary is inspectable and versioned. Its topic matches are software selection rules.

`personalisation/memory_extraction.py` supplies the bounded model extractor: two calls and 90 active seconds including preparation and validation. Each accepted content value preserves an exact owned source quotation. Temporary instructions remain in the current request. Unsupported mastery claims and assessment records supplied through this extractor are rejected. The original `personalisation/memory.py` extractor remains the explicit v1 path.

The additive migration `d9e53f6b012a`, following `c8d42e5a901f`, adds field identity, verification status, source details, effective time and event sequence to memory entries; revision details; and `memory_write_events`. Existing entries retain their historical version and an explicit unverified legacy status. A free-form legacy key is used by the v1 reader; V2 asks for a typed correction before treating it as a current learner fact.

An owner-level monotonic event sequence orders source statements, manual corrections and erasures. Later changes fence earlier asynchronous results for the same canonical key. Erasing an absent field creates a tombstone; repeated erasure advances that fence. Memory settings use compare-and-swap versions and a revocation epoch. Each source is checked against active owner, workspace, session, message identity and content hash.

## Submission and asynchronous integration

The normal submit seam is:

```python
freeze_memory(db, owner_id, question, use_profile,
    policy_version="query_conditioned_memory_v2",
    current_message_id=message.id, profile=policy,
    context=context, counter=counter)
enqueue_extraction(db, owner_id, message, config, use_profile,
    policy_version="typed_memory_v2")
```

Explicit recognized corrections are applied before this request's snapshot is frozen, within its transaction. Current instructions also mask matching older fields in the selected view. Unrecognized eligible durable statements retain a separate worker purpose and finite budget. Processing events expose actual pending, applied, no-op, failed and cancelled states. They retain source/event identifiers and safe diagnostics.

The optional prepared payload has a 768-token ceiling using the supplied configured counter, with reserved space for snapshot metadata. It contains selected values, source/version references, topic-policy identity, exclusions and profile defaults. Full source rubrics and revision bodies are excluded from the prompt payload. `MemoryPreparationUnavailable.code` permits an observable preparation-unavailable result before a snapshot exists. Revoked or expired frozen snapshots remain explicit conflicts; callers cannot silently revive their values.

The explicit `typed_memory_v2` reader is M3; `query_conditioned_memory_v2` is M4. They share the same writer and evidence gates. `explicit_learning_memory_v1` remains the default of the low-level compatibility functions for frozen M2 jobs and old study code. New interactive submission chooses V2 explicitly.

## API and interface

Existing opt-in settings, entry list, edit, source inspection, delete and undo-save endpoints remain. Additions are:

| Endpoint | Behavior |
| --- | --- |
| `POST /me/memories` | Store a typed exact statement from an owned source message. |
| `POST /me/memory/assessments` | Record ordered question/response evidence with a declared scoring basis. |
| `GET /me/memory/summary` | Derive a current summary from active, unexpired items; return a revision hash. |
| `GET /me/memory/processing` | Show bounded owner-specific write-event and worker status. |
| `POST /me/memory/preview` | Select learner state for a question using current settings and profile, with zero answer-model calls. |

Assessment scoring supports actual server exact-text and finite-numeric rubrics with scorer identity/version, rubric hash, full question and response hashes, order and ownership checks. A submitted score stays `recorded_unconfirmed` and is excluded from prompt state. A named signed-in reviewer requires explicit attestation for human confirmation; an administrative role alone supplies no confirmation. A single verified result remains scoped to that assessment.

The Memory page exposes the summary, verification/source details, per-field correction, processing errors and question preview. Disabling memory clears stale preview state immediately. Overview failures preserve entry-management controls. Editing an assessment downgrades its confirmation; erasure and undo-save remove content without restoring a deleted body. Profile-off disables memory for that answer, while the management page remains available.

## Erasure and freshness

Deletion removes entry/revision payloads, source-derived details and affected frozen memory payloads. It suppresses re-extraction from erased sources and cancels stale jobs. Affected private drafts and diagnostic traces are redacted. Original chat messages follow their separate retention lifecycle. Expiry removes a value from new state and invalidates its frozen derivatives while leaving an expired record inspectable. Global disable blocks updates and use; re-enable retains eligible saved entries without replaying suppressed jobs. Summary text is derived afresh from current active items.

## Verification recorded so far

`evidence/week08-memory-v2/20260921/memory/focused-final-attempt2.xml` records 45 passing checks across typed selection, immediate correction, delayed older writes, repeated erasure, assessment provenance, actual HTTP management/preview, worker cancellation, current product integration and the preserved M2 path. These include the executable 12-pair observation-gate fixture test in disposable PostgreSQL, uncertain-call resume and authentication-stop guards, frozen label hashes, and retained missing/error denominators. The ungated arm is an evaluator-only projection with zero writes. Frontend Memory component checks passed 11/11 in `ui-attempt2.json`, and TypeScript/Vite build passed. These checks used authored fixtures and mock transports, with zero paid calls. Earlier fixture/temp-directory failures and prior compatibility-test assumptions are retained in the same evidence directory.

`memory/browser-final/verification.json` records actual Edge interaction with a separately migrated disposable database. At 1440 and 390 pixels, the browser verified biology-to-ATP selection, current-instruction precedence, profile-off suppression, source inspection and Escape, a typed correction, disable, deletion and retention of the original owned message. Five screenshots were visually inspected. The temporary API had no provider key or answer worker, and both owned services were stopped afterward. The exact API source checkpoint is `memory/browser-runtime2.json`; the visual and process record is `memory/browser-final/visual-and-runtime-review.json`. Two earlier harness locator/async-wait failures remain available. Physical keyboard, IME, assistive-technology and scientific answering quality are outside this browser check.

## Study preparation

`evaluation/memory_v2/memory_catalogue.py` loads 12 new authored histories, three question probes each, 24 extraction inputs with field/operation/scope expectations, and 12 observation-gating pairs from the separate private research bundle. Common frozen question and retrieval records bind the five memory arms; private expected values stay outside generation inputs. Corrections are checked by exact value as well as field identity. Public packages omit `evaluation/memory_v2/private/memory-catalogue.json`; optional study execution asks for the approved research inputs when absent. Public tests use independent authored fixtures.

`evaluation/memory_v2/memory_study.py` separates typed extraction, state preparation and 180 checked final answers. One actual typed writer state is read by M3 and M4 and checked for equality; M2 uses its original extractor/worker/reader. M1 uses the existing bounded rolling-summary updater. Its explicit delete/expiry control clears that small summary; this comparator policy is recorded. Per-probe snapshots represent their historical point in the authored sequence, allowing faithful replay after later deletion. They are private research artifacts, separate from current product memory.

The harness requires a frozen study manifest, matched private trajectory/task hashes, independent extraction-case and observation-gate hashes, exact retrieval hashes and current executable source identity. Gate execution consumes the frozen input arrays. Extraction agreement uses the full 24-input denominator with error and missing cases retained; M2's free-form attributes receive no invented typed-field scores. Preparation targets a distinct empty migrated `cs30_memory_study_*` database. Credentials are resolved read-only from the frozen managed configuration and held in process; no credential rows or original learner history are copied. Write-once reservations prevent automatic replay of uncertain calls. Saved outcomes reconstruct provider stopping rules before further calls. The frozen memory-answer execution is terminal: 180 planned requests retain 108 answers and 72 failures, as recorded in [the complete generation receipt](../../evidence/week08-memory-v2/20260921/formal/generation-terminal.json). The [terminal numerical results](memory-v2-results-20260921.md) retain all 180 outcomes: M4 has 20/36 conservative successes versus M3 21/36, a −2.78-point difference with 95% interval [−13.89, +8.33]. Extraction yields 24/24 valid outputs and 16/24 exact authored operation sets; all 12 observation gates match their authored expectations. Required-label recall is 22/26 for M3 and 21/26 for M4, while explicitly excluded selections fall from seven to two. These selected-field counts do not establish semantic selection precision. Independent human ratings remain blank.
