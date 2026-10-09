# Week 9 teaching plans and context coverage

The implementation follows the [registered Week 9 protocol](week09-generation-protocol-20260926.md). Ordinary textbook questions retain complete direct answers. Explicit hint tasks receive a deterministic plan derived from their frozen original problem, help level, current step, pending question and exposure history. Planning makes no provider call and records its elapsed time separately.

## Independent teaching factors

`generation/teaching_plan.py` freezes `generation_controls_v1` with the four registered arms. A uses existing content and display selection; B enables the explicit content plan; C enables progress-aware source display; D enables both. New product requests freeze D. The HTTP message contract exposes no experimental arm switch. Controlled runners can construct the registered arm, whose identity remains in the request command.

The content plan records the current step, action, allowed disclosure, evidence needs and expected learner reply. Actions are recalling a concept, splitting a step, checking understanding or locating an explicitly requested error. An attempted learner response retains the original problem and constraints. The planner assigns no mastery or correctness label. Direct questions have `enabled=false` and `complete_explanation`, with complete supported answers allowed.

Only B/D inject the new content plan into generation and checking. The display intervention runs separately for C/D on the actual cited source blocks before semantic checking. It selects complete existing blocks by claim relevance and current-step terms, preserves supplied required citation bindings, and retains a following qualification block. Source text, hashes and offsets remain unchanged. Generator evidence ordering is common across factors. Final support and cumulative-disclosure checks receive the exact proposed source display; deterministic selection cannot approve disclosure or factual support.

`progress_action_plan_v1` records an exposure-snapshot hash, previously displayed fragment IDs and prior turn/event counts. Original exposure records remain the authority. Task version, pending-question version, memory epoch, current source visibility and worker execution token are rechecked before publication.

## Context requirements and one targeted retrieval

`generation/evidence_coverage.py` produces `context_coverage_v1`. Candidate context, packed context and draft support have separate fields. Requirements name matching evidence/chunks, unmatched term groups and parts lost during packing. An inspectable DNA/RNA comparison template supplies sugar, bases, structure and function axes when the comparison requests no narrower explicit axis. Other questions use existing explicit or lexical facets. These are automatic planning estimates. Semantic context sufficiency and independent human ratings remain null until separately assessed.

For a named incomplete multi-part requirement, a v4 interactive request can execute at most one supplementary retrieval in the same frozen release, with at most ten candidate rows. The original question and conditions remain in the supplementary query. The pass uses the frozen local device, retrieval policy, reranker and relevance gate; it retains existing admitted sources and adds distinct relevant candidates. Identity conflicts fail explicitly. Callbacks check cancellation and the shared active-time budget before retrieval, before reranking and after screening. Planning and supplementary retrieval use zero remote model calls; elapsed work counts toward the existing request deadline.

V4 uses this single-pass path in place of the older two-facet fallback. Previously frozen requests retain their recorded legacy fallback and generation/checking versions. Benchmark E0/E1 does not enter these interactive controls. Packing loss calls for better selection from the existing candidates and does not trigger duplicate retrieval. A simple lexical mismatch in a single-part question also does not trigger a repeat lookup.

The generator receives coverage observations with an instruction to evaluate source meaning, answer supported parts and name actual missing parts. A missing keyword alone cannot force refusal, and a lexical match cannot certify a claim. The v4 semantic checker and independent review use their own judgments.

## Backend, memory and diagnostics

New commands freeze `evidence_reliability_v4`, `generation_controls_v1`, current managed generator/checker configurations and `query_conditioned_memory_v3`. The semantic-memory supplement defaults to disabled rule selection. Administrators can point `MEMORY_SEMANTIC_POLICY_FILE` to a calibrated policy JSON; its validated fields are frozen. An unreadable, oversized or invalid optional policy records `MEMORY_POLICY_UNAVAILABLE`. Its raw contents never enter the command. Selected source text and private selection traces remain within the existing owner-controlled memory boundary.

`AnswerRequest.command` stores immutable policies and task inputs; `trace` stores the progress plan, context coverage, supplementary-retrieval audit and measured stages. Administrator diagnostics add typed progress/action/arm fields and coverage counts, missing IDs and packing losses. Memory diagnostics add only status and selection/reread counts. They omit memory contents, source conversations, raw model payloads and private reference labels. No database migration is required for these versioned JSON additions.

## Current verification

| Scope | Observation | Evidence |
| --- | --- | --- |
| Independent factors, direct answers, step/condition preservation, exposure identity and complete-block display | 15 unit cases passed | [Combined JUnit](../../evidence/week09-generation/20260926/teaching/integration-attempt1.xml) |
| Context/draft separation, complementary requirements, packing losses, one-pass bound, cancellation and source identity | 11 unit cases passed | [Initial unit run](../../evidence/week09-generation/20260926/teaching/unit-attempt1.xml) |
| Safe administrator projection | One unit case passed | [Combined JUnit](../../evidence/week09-generation/20260926/teaching/integration-attempt1.xml) |
| PostgreSQL HTTP integration | Four cases passed: default complete answer, frozen v3 compatibility, one supplementary pass and expired-budget stop | [Combined JUnit](../../evidence/week09-generation/20260926/teaching/integration-attempt1.xml) |
| Administrator UI and types | Seven frontend cases passed; TypeScript passed | [Frontend receipt](../../evidence/week09-generation/20260926/teaching/frontend-attempt1.json) |

The combined check passed 31 Python cases. HTTP tests use a disposable migrated PostgreSQL database and explicitly authored test sources; one injects an empty initial retrieval to inspect the supplementary boundary. These cases establish software behavior. Official-corpus/provider outcomes, factorial estimates and independent human ratings use the separate registered study and retain all scheduled failures.

The wider compatibility check initially passed 27 cases and failed two historical facet-fallback assertions ([first receipt](../../evidence/week09-generation/20260926/teaching/compatibility-attempt1.xml)). Those fixtures submitted a new v4 request while asserting the older two-facet trace. They now explicitly freeze `evidence_reliability_v3` and remove the v4 generation policy. The unchanged legacy assertions and the separate v4 boundary cases passed together: 33 cases, zero failures or skips ([current receipt](../../evidence/week09-generation/20260926/teaching/compatibility-attempt2.xml)).

Two additional HTTP cases submit malformed optional memory-policy files, including a JSON array. Both retain ordinary answering and record `MEMORY_POLICY_UNAVAILABLE` with no private configuration payload in the frozen command. The six-case controls check passed ([receipt](../../evidence/week09-generation/20260926/teaching/controls-attempt2.xml)).

The first full integration run passed 129 cases and failed seven ([retained receipt](../../evidence/week09-generation/20260926/teaching/all-integration-attempt1.xml)). It found a real API omission: current probes returned `provider_probe_v3`, while the public test-result literal accepted only earlier versions. The additive literal and generated API types now include v3. The Models page also recognizes current v3 passes for activation and retains earlier receipts as history. Seven focused model/evaluation HTTP cases and 13 Models UI cases passed; TypeScript passed ([HTTP receipt](../../evidence/week09-generation/20260926/teaching/probe-http-attempt2.xml), [UI receipt](../../evidence/week09-generation/20260926/teaching/model-ui-attempt2.json)). The remaining scripted current-request fixtures require typed v4 checker/probe payloads; explicit historical paths remain separately represented.

After updating the scripted current-request fixtures to typed v4 assessments and probe schemas, the complete integration rerun passed 138 cases with zero failures and zero skips ([current complete receipt](../../evidence/week09-generation/20260926/teaching/all-integration-attempt2.xml)). This includes both new optional-policy error cases and all retained historical compatibility assertions.

## Cumulative delivery tooling

`scripts/release/week09_delivery.py` builds one complete project archive and eight disjoint overlays from the exact Week 7 baseline and the previous teaching/performance complete archive. Accountable owners remain those in the original inventory. Every assigned contribution contains the current complete file. The baseline plus the eight overlays and the two declared optional graphs reconstructs the complete archive byte for byte. All 80 verified runtime resources and three optional graph resources retain their previous bytes. Optional alignment configurations are normal versioned source files; the builder adds no new model weights to the default runtime.

The nine English reports come from `docs/delivery/week09`. Their hashes must match the supplied visual-inspection receipt. The standalone reports, member-root reports and reports inside the full project are identical. A new destination is required; older deliveries and private files are preserved. Configured secrets and decompressed DOCX contents are scanned. Week 9 fixtures, gold/reference records, raw provider payloads and private review packets are excluded, and public JSON measurements cannot include raw question, answer, source or prompt payload keys.

Seven synthetic release checks passed, including nine-archive reconstruction, exact resource preservation, compressed-DOCX secret rejection, report-hash identity, corrupted inherited graph rejection and the fixed authored-report allowlist ([receipt](../../evidence/week09-generation/20260926/teaching/package-attempt1.xml)). These use small authored archive bytes and establish builder behavior. Actual release verification follows after the final project reports and runtime checks.
## Fresh installation and application workflow observations

The separate Week 9 portable installation completed the actual Windows launcher with
`-Install -UseExistingDatabase -DatabasePort 18532 -ApiPort 18700 -FrontendPort 15773 -Device cpu`.
It uses a new Python 3.13.2 virtual environment, PyTorch 2.8.0+cpu with no CUDA runtime,
a new `cs30_week09_portable` database, and freshly installed frontend dependencies.
The official four-book release contains 10,594 active 384-dimensional vectors.
All 80 inherited runtime resource files and three optional ONNX files matched their
recorded hashes. Two mock-answer requests used real CPU retrieval, and cancellation,
history reload, source integrity and positive queue-delay checks passed. This is a
fresh environment on the current Windows host. Receipts are in
`evidence/week09-generation/20260926/portable/`.

Actual Chromium checks at 1440 and 390 pixels passed 27 checks on this installation.
They cover current `provider_probe_v3` mock role tests and activation, direct-answer
defaults, exact approved citation text, source-dialog focus, Week 9 diagnostics and
reload. Sixteen screenshots were inspected. A hint request using mock generation
retained the explicit `SEMANTIC_CHECK_UNAVAILABLE` failure. The browser receipt is
`evidence/week09-generation/20260926/browser-portable-01/verification.json`.

The first post-study real-provider HTTP journey retained six scheduled submissions.
Four published: an ordinary answer, a checked hint, its bound learner attempt and a
new problem. The multi-part DNA/RNA comparison with saved biology memory failed with
`CONTEXT_LIMIT`; explicit full explanation failed with `SEMANTIC_CHECK_FAILED` after
its bounded repair. Both actual provider role probes passed before activation.
Source fingerprints remained unchanged and the runner performed no retries.
The successful hint received 18 additional browser checks at both widths, including
the pending question, reload, exact approved preview/highlight count and focus.
Four screenshots were inspected. The full-answer browser checkpoint has no result
because that request did not publish. The receipts are
`evidence/week09-generation/20260926/http-final-01.json` and
`evidence/week09-generation/20260926/browser-main-first_hint/verification.json`.

The journey submitted 19 provider calls: six probe calls and 13 workflow calls,
including failed attempts and internal repair. Provider usage totals are 80,964
input tokens and 6,713 output tokens (87,677 combined), with 37,248 cached input
tokens and 43,716 uncached input tokens. All submitted calls have usage records;
the provider invoice amount is unavailable. See
`evidence/week09-generation/20260926/http-final-01-usage.json`.
These workflow and rendering checks are separate from the frozen experiments and
independent human scoring. The two failures remain available for diagnosis and any
separately recorded release follow-up.

## Release successor: lossless checker transport

After the frozen studies and the six-case workflow ended, a separate release fix
added `checker_payload_policy=lossless_checker_tables_v1` to newly submitted
commands. Requests without this field continue with `legacy_fragment_table_v1`.
The checker selects the smallest complete encoding from the original fragment
objects, the existing fragment table and a lossless claim/binding-bank table.
The model window, output reservation, exact source text, citation bindings,
semantic checks and retry limits retain their existing values.

Eight focused HTTP tests passed, including new-command dispatch and unchanged
historical v3/v4 commands. The first invocation encountered a missing temporary
parent directory; its setup-error receipt is retained alongside the passing
`teaching/checker-release-controls-02.xml` result. The final aggregate gate in
`software-gate-release-final-02/` passed 1,089 Python and 89 frontend tests with
unchanged source hashes during the checks.

The separately frozen successor workflow submitted four requests once: the exact
DNA/RNA comparison under the same owner and saved preference, a direct osmosis
explanation, a new osmosis hint and its full-explanation action. All four published.
For the comparison, checker input decreased from 13,151 tokens in the prior
fragment-table encoding to 12,094 tokens in the selected encoding, an 8.04%
reduction for that identical checker payload. The selected input plus the 4,096-token
output reservation fits the unchanged 16,384-token window with 194 tokens remaining.
The encoder retained the original object encoding when it was smaller for a hint.
All candidate sizes and round-trip records are in
`evidence/week09-generation/20260926/http-successor-01-usage.json`.

The four requests used 10 provider calls, including the full explanation's bounded
repair and recheck: 68,708 input tokens and 6,113 output tokens (74,821 combined),
with 28,544 cached and 40,164 uncached input tokens. The original workflow's four
publications and two failures remain separate. A four-case development replay
does not estimate general answer quality or replace the frozen experimental results.

The published full-action response passed 13 actual browser checks at 1440 and
390 pixels. Four screenshots were inspected. The pending question cleared,
direct mode persisted after reload, and source text/highlight counts matched the
approved projection. Its text explains the core osmosis definition and explicitly
identifies missing evidence for direction, concentration and pressure; publication
does not establish complete topic coverage. The receipt is
`evidence/week09-generation/20260926/browser-http-successor-01-explicit_full/verification.json`.

The fresh CPU installation was synchronized to this production version and
restarted. Two new real-retrieval/mock-answer requests, cancellation, history,
source integrity, policy freezing and queue-delay checks passed in
`evidence/week09-generation/20260926/portable/runtime-verification-release-source.json`.
Final report and document synchronization is recorded by the delivery parity
receipt. Human semantic and teaching-effect scores remain separately collected.
