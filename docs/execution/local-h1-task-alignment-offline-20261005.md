# H1 goal alignment: offline design and local repair

Recommend B: keep one observable learner decision and its reason in the existing teaching plan, then let the existing generator express it. A's conceptual applicability, direction, invariant or structural questions are permissible expressions. The implemented change is a limited process-task contract: it does not extract a domain solution graph, candidate inventory or correct answer on the server.

The previous S11/P01 native deliveries safely withheld formulas but asked only for supplied constants or quantity names. Their independent semantic verdicts remain FAIL. H1 need not solve the whole selection; it must require a local decision toward it, with a task-specific basis. For example, asking a learner whether a candidate's held-variable requirement fits this process and why requires an applicability judgment. Merely asking which variable is fixed does not. See the [previous closed pilot](local-deepseek-hint-progression-v1-20261005.md).

The design is under-constrained, rather than inherently incompatible with useful formula-free help. The saved step contains an operation, not a complete solution graph. Existing prompts already reject given readback, but the plan previously requested only a guiding question. The original hint release uses specific_help directly; complete_answer and non_repetitive_next_action are not universal hint release conditions. Changing only a diagnostic field would not repair the observed failures.

A alone is a smaller wording change but leaves the learner action implicit. B makes the required action inspectable by the generator and checker through the same frozen plan. This small B implementation adds hint_task with references to the effective operation and public conditions, a candidate applicability or local structural-fit action, and a judgment-plus-reason reply. Its existing specific_help instruction judges the visible question, not the task tag. No extra model call, schema, answer key, storage field, classifier or planning stage was added.

The derived task applies only to enabled H1 content planning and the existing finite mathematical selection recognizer. A pending question supplies the narrower operation; a nonselection pending question does not fall back to a broader saved selection. Real attempt feedback, H2/H3, direct/full help, content planning off and older policies retain their behavior. The finite recognizer and expression guard are unchanged.

Source changes: generation/teaching_plan_v10.py; new tests/unit/test_hint_task_alignment_v10.py; and an additive source-to-target record in docs/foundation/handover_migration.md. The final candidate has 950 mapped inputs. The handover retains every prior byte. The independent final static review and ROOT's AST comparison show that test formatting preserved syntax and the post-overlay production change only retained the original complete_answer meaning.

[Diagnosis](../../evidence/week09-continuation/20261005/task2-h1-task-alignment-offline-v1-01/design-diagnosis-v2.md) and [independent code review](../../evidence/week09-continuation/20261005/task2-h1-task-alignment-offline-v1-01/implementation-static-review-02.json) record exact source references. The diagnosis read 19 mapped public C source files; it did not write source files or read actual-result roots, E, private profiles, databases or protected data. Its preserved original Markdown had one ambiguous access sentence; the v2 successor corrects only that sentence.

Frozen controls preceded implementation: 10 unrelated subject/problem families, each with one useful local judgment, a given-readback negative, a generic-question negative, a notation/answer leak and a word-only answer leak. Independent AI review agreed with all 50 authored labels. This proves the finite examples' design distinction, not actual-model improvement, checker classification accuracy or learning outcomes. No authored label or negative answer example is sent to the generator.

| Frozen family | Current automatic task eligibility |
| --- | --- |
| ALGEBRA_INVERSE_STRUCTURE | Matched |
| INEQUALITY_ORDER_TEST | Design example only; finite selector does not match |
| GEOMETRY_DIMENSION_FIT | Design example only; finite selector does not match |
| PHYSICS_HELD_VARIABLE_FIT | Matched |
| PHYSICS_FORCE_SIGN_CONSISTENCY | Design example only; finite selector does not match |
| CHEMISTRY_MOLE_RATIO_FIT | Design example only; finite selector does not match |
| CHEMISTRY_CLOSED_INVENTORY | Design example only; finite selector does not match |
| ALGORITHM_SEARCH_REGION | Design example only; finite selector does not match |
| ALGORITHM_ORDER_PRESERVATION | Design example only; finite selector does not match |
| READING_CAUSAL_EVIDENCE | Design example only; finite selector does not match |

Only 2/10 original frozen goals match automatically. The chemistry unit control separately uses an explicitly mathematical selection goal; it is not a claim that the original chemistry fixture was automatically covered. The eight nonmatches remain outside this repair. Identification/extraction tasks can legitimately request a supplied datum when that is the saved operation; an applicability task must not replace them.

[Frozen examples](../../evidence/week09-continuation/20261005/task2-h1-task-alignment-offline-v1-01/synthetic-families-01.json), [independent semantic review](../../evidence/week09-continuation/20261005/task2-h1-task-alignment-offline-v1-01/fixture-semantic-review-01.json), and [offline proof](../../evidence/week09-continuation/20261005/task2-h1-task-alignment-offline-v1-01/hint-task-alignment-offline-proof-01.json) keep authored semantics, program eligibility and finite expression detection separate. Readback, generic prose and word-only disclosure remain semantic checker responsibilities; the expression guard is not a pedagogical classifier.

The native offline capture uses the current GenerationService and provider payload builder with the original public packets and full teaching schema. It verifies identical task transport to generation and the compact encoded checker; it stops before any model checker judgment. A representative authored draft provides payload-sizing input only.

| Case | Generation bytes / reference tokens | Checker bytes / reference tokens | Checker byte headroom |
| --- | --- | --- | --- |
| P01 | 27614 / 5847 | 31869 / 6731 | 899 |
| S11 | 27583 / 5832 | 31861 / 6727 | 907 |

The unchanged bounds are 32,768 UTF-8 bytes and 8,000 canonical reference tokens; schema SHA256 is 85da4dcfba700f6f652f519e074e00d887ee6edc6c57f6109c3e051cea65d8c1. Hosted input usage is not measured by this reference count. Every future actual stage retains its runtime bounds; these two representative bodies do not guarantee the size of arbitrary future outputs.

Free regression completed: focused02 passed 83 tests and 88 subtests, including the 40 new controls. The current complete mock gate passed all eight stages: 3734 Python tests plus 102 subtests, 196 frontend tests, Python quality, foundation, contracts, chat scope, frontend types and build. See [full receipt](../../evidence/week09-continuation/20261005/task2-h1-task-alignment-offline-v1-01/verification-hint-task-alignment-v1-full-01-receipt.json) and [software gate](../../evidence/week09-continuation/20261005/task2-h1-task-alignment-offline-v1-01/software_gate.json). Commands used cached dependencies, one newly owned isolated PostgreSQL container and no existing database; the focused and full owned containers were removed. Source and status hashes were unchanged during each successful run.

The first focused attempt did not start tests because the default sandbox denied C:/Users/PC/.docker/config.json and the local docker_engine named pipe. Its stopped receipt is retained. The proper permission-review path approved the same reviewed isolated runner; focused02 and the full gate then ran without an alternate configuration or existing-database fallback.

This round made zero paid API calls deliberately to avoid ineffective repetition while diagnosing H1. Existing continuous testing authorization and the 120 budget remain valid. The closed prior budget is unchanged: known 0.424482 CNY, protected 10.424482 CNY including legacy unknown 10, with no new holds. These are protected ledger figures, not a billing reconciliation; no earlier settlement was applied again.

The bounded public clone copied 47,767,802 bytes across 991 files. Its 185,858,638-byte PDF reused a same-file C hardlink with zero additional PDF data; cached frontend dependencies were reused. No installation or disk-space query occurred. Current free space remains unknown after the earlier Get-Volume denial. Earlier denied process/git/session paths were not retried or bypassed. Git status remains incomplete; source hashes, rather than a branch cleanliness claim, bind this delivery.

Acceptance remains bounded. This round establishes a more explicit process contract, finite inspectable useful examples and current software/transport regression. It does not establish actual-model semantic success, word-only leakage reliability, broad domain coverage, classroom benefit, human acceptance or complete course acceptance. The previous two native semantic failures and human-null fields are preserved. The next justified capability extension would expose a trustworthy public operation capability when the current finite selector cannot identify the task; it must preserve legitimate extraction and pending scope. No new paid trial, push, upload, deployment or course submission occurred in this round.

Local publication is confirmed only by the matching PASS publication receipt and readback in this evidence directory. Preparation and review alone do not claim E delivery.
