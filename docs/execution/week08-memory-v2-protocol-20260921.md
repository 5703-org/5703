# Week 8 Memory V2 and answer reliability: protocol v1

Registration date: 21 September 2026. This design is recorded before any new formal model calls. Implementation and development pilots may refine the executable study checkpoint; changes require a dated amendment before formal execution. A write-once manifest must freeze this document, exact case inventory, source/configuration/prompt hashes, evidence identities and randomisation before any formal result is generated. The 20 September studies remain unchanged.

## Objectives and data partitions

The primary memory comparison is **M4 versus M3**: query-conditioned learner state versus typed/versioned memory with the same writer and evidence rules. The primary reliability comparison is **B2 versus B1**: repaired pipeline versus the current complete checking pipeline. T2 versus T1 retains the separate teaching question about jointly controlling hint content and source exposure. All other contrasts are diagnostic or exploratory.

Existing formal failures, including citation atomic-content failures, F28/F40/F56 local-reference errors and M02/M03/M04 memory failures, are development/regression inputs. They are excluded from independent final claims. New final items are grouped by scientific concept/problem family, so a paraphrase cannot cross the development/final boundary. Each final case stores its original question, context, source edition/section/page/fragment anchors, required concepts, applicable units/conditions and forbidden inferences in an evaluator-only file. Generators receive only the allowlisted public question and the condition's permitted evidence/state.

The planned final inventory has **24 independent question families** (six associated with each of the four real books), **12 independent teaching tasks** with three turns, and **12 synthetic learner trajectories** with three answer probes. Topic overlap between books must be checked manually in the authored family map; counts by textbook are coverage strata, not independent subjects. The 12 teaching tasks may use 12 of the 24 new families; their correlated outputs are grouped by family. Memory histories are clearly authored test records and never become textbook corpus data.

## Study conditions

| Study | Conditions and planned requests | Matched factors and interpretation |
| --- | --- | --- |
| A: supplied-information diagnosis | A0 no retrieval; A1 frozen current retrieval; A2 human-confirmed sufficient evidence. 24 requests per arm, 72 planned. | Same basic answer prompt, model and output budget. Model background knowledge is permitted in all arms; evidence is optional additional information. A2 is an oracle diagnostic. Its execution requires a real reviewer's sufficient-evidence confirmation for each case. Pending confirmations remain scheduled missing results and do not stop other arms. |
| B: strict textbook reliability | B0 schema-valid basic generation; B1 frozen current complete checking; B2 repaired pipeline. 24 per arm, 72 planned. | Same textbook-grounding instructions, query, frozen candidate pool, generator/checker identity and memory off. B2 may improve evidence packing and checking; the headline difference is explicitly a combined pipeline effect. B0 retains schema, ownership and source-ID checks but no semantic-check/repair call. It is an evaluation-only diagnostic, never an automatic production fallback. |
| C: targeted reliability ablations | C1 B2 with legacy packing; C2 B2 with legacy claim/marker repair. 24 per arm, 48 additional requests. | Reuse B2 results as the full condition. Freeze all other policies and record supplied-context hashes. C1 isolates packing relative to B2; C2 isolates the mapping/repair change. Changes in available evidence are stated explicitly. |
| T: teaching control | T0–T4, 12 tasks × 3 turns × 5 conditions = 180 requests. | Preserve the existing factorial definitions: T0 no body/display/cumulative check; T1 body only; T2 body+display+cumulative; T3 body+display; T4 body+cumulative. All arms share the new reliability implementation and exact evidence pool. Default direct chat is outside the hint-only protocol. |
| M: memory utilisation | M0 no long-term memory; M1 frozen rolling summary; M2 frozen current structured reader/writer; M3 typed/versioned writer with unconditioned reader; M4 same writer with query-conditioned state. 12 trajectories × 3 probes × 5 conditions = 180 requests. | Match question, textbook evidence, generator, teaching mode, current-turn text and saved profile. M3/M4 use identical operation candidates, gates and state transitions. Evaluate selection and final answer separately. Memory enablement, expiry/deletion/current correction/scope states are preregistered per probe. |

The maximum planned main generation requests are **552**, including the 24 human-dependent A2 requests. This is an engineering study with limited statistical power, not a population-wide learning-effect estimate. No sample increase or early termination based on favourable scores is permitted.

## Memory engine, extraction and observation tests

Before formal final-answer calls, run deterministic engine cases for explicit ADD/UPDATE/DELETE/NO_OP; synonyms and stable keys; scoped exceptions; later correction versus delayed older work; temporary instructions; source ownership; CAS; disable/re-enable; expiry; derivative erasure; cross-user isolation; current instruction precedence; and query selection including ATP/Biology. These tests report actual operation outcomes and expected state equality without involving a generator.

Freeze **24 model-extraction cases**, two for each of the 12 memory trajectories, before extraction calls. Retain model parse/availability failures and the exact validated operations. Reuse M3/M4 extracted candidates to isolate reader effects. Report field precision/recall, operation accuracy, source support, stale value reuse and invalid evidence rejection separately from final answers.

Freeze **12 observation-gating pairs** spanning question-only, self-report, supported scored response, absent scoring basis, wrong owner and exaggerated mastery. Compare the production gate with an isolated evaluation-only gate-disabled projection using identical authored candidates. The ungated projection never writes product memory. Count unsupported learner conclusions and valid-observation retention. A single correct response supports only that assessment. Human confirmation is never inferred from an automatic evaluator.

M1 summarisation calls and all memory extraction/planning calls are independently recorded. The deterministic reader needs no external planning calls; any introduced model planner requires a pre-run amendment and a finite shared budget.

## Runtime limits and stopping rules

Provider diagnosis uses public authored probes and the saved encrypted credential path. Basic generation, structured output and full project-contract results are recorded separately, including checker role. There is no hidden live retry or model substitution. Unavailable credentials or inaccessible networks are recorded by provider and scope.

Product answer requests retain a finite shared ceiling of **four external calls and 180 active seconds**, with model/protocol-specific output/context/time settings frozen in the manifest. A normal checked request uses generation then checking. One remaining repair/recheck pair addresses a diagnosed cause. An inconsistent checker is repaired against the same draft; unsupported content or mapping issues repair the answer. Local retrieval and re-ranking consume active time. A protocol's native token-counting call consumes a call slot when used. No final publication bypasses required production checks.

Run at concurrency one by default with rotated condition order derived from seed **20260921**. Technical recovery resumes only items without terminal results and preserves every attempt. Stop new calls on authentication/billing denial, three consecutive transport failures for the same provider, a source/configuration fingerprint change, invalid freeze or a privacy/integrity failure. Record the remaining scheduled items as unexecuted with cause. Corrected reruns use a new explicit attempt/run version; original outcomes remain visible. Development tuning stops before the final freeze.

## Metrics and analysis

Every table includes planned, attempted, delivered, refused/clarified, failed, unexecuted and judged counts. Delivery rate uses all planned eligible requests. Factual correctness among delivered answers uses delivered answers with actual judgments and separately reports judgment coverage. Conservative end-to-end correct delivery uses all planned eligible requests, counting failed/missing outcomes as unsuccessful. Human-dependent arms report both planned and confirmed eligibility without concealing missing confirmations.

Evaluate factual support, complete required-point coverage, applicable conditions/units, claim-to-inline-marker mapping, citation support and unnecessary refusal separately. Hint validity requires supported useful help and allowed cumulative body/source disclosure. Memory metrics include update/extraction accuracy, stale reuse, selected-item precision/recall, scope violations, current-instruction override, appropriate personalisation and unsupported learner inference. Structural exact-span checks do not establish semantic support.

Use paired differences grouped by task/family or learner trajectory, with 10,000 bootstrap resamples and seed 20260921; keep all turns within their group. Report confidence intervals and raw paired counts. Only the three stated primary contrasts are confirmatory within this small engineering study; other contrasts are labelled exploratory. Automatic judgments retain model identity, prompt/schema hashes, reasons and failures. A judge from the same provider/model family has correlated bias; report it explicitly. No automatic rating is a human rating.

## Human review and cost

Prepare blinded randomised packages for two actual independent reviewers, with answer/source views, scoring guidance, original blank rating columns, schema-validating import, per-reviewer immutable revisions, disagreement lists and separate adjudication. Human ratings start at zero. Oracle evidence confirmations require a named actual reviewer, source hashes, coverage and confirmation time. Gold/reference and condition keys remain in evaluator-private review materials, outside the runnable public package and member GitHub packages.

Record every generation, checker, repair, extractor, summariser, diagnostic and judge attempt, including truncation, timeout and failure. Reconcile returned input/output/cache usage with the applicable dated provider price. Missing usage or unknown cache splits remain unknown-cost rows, not zero. Report provider currency and estimates separately from invoices. Research bundles for the team's authorised private review are separated from public deliverables.

## Freeze and amendments

The source baseline archive is recorded in [the implementation entry](week08-memory-v2-20260921.md). The executable formal freeze and exact case inventories are pending implementation. No new formal experiment has run at this registration point. Amendments must explain which factor changed, whether outputs had been inspected and which earlier results remain valid; a frozen file is never overwritten.
