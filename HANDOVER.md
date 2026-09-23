# CS30-1 Learning Assistant: current handover

## Current iteration — 21 September 2026

The current cumulative development is [Memory V2 and provider reliability](docs/execution/week08-memory-v2-20260921.md). It adds typed and query-conditioned learning memory, separate answer/checker compatibility tests and cause-specific checked-answer repair. The [registered protocol](docs/execution/week08-memory-v2-protocol-20260921.md) retains 552 scheduled requests with explicit human-dependent oracle items. All 552 registered generation outcomes and offline judgment receipts are terminal: 346 answers, 177 failures, five clarifications and 24 human-dependent A2 waits. The judge produced 329 valid answer judgments, 22 schema failures and 201 no-delivered-response receipts. All outcomes remain in the planned denominators. The private research archive preserves the exact 485-file study snapshot. The public-fixture successor changed five test files and added two helpers; the later release-only correction changed the packager and its existing regression test. Product and evaluator behavior remain unchanged. The [generation receipt](evidence/week08-memory-v2/20260921/formal/generation-terminal.json) and [blank reviewer-form check](evidence/week08-memory-v2/20260921/formal/review-export-verification.json) preserve their exact scopes. Final analysis and the verified private archive are linked from that entry; the earlier sections below remain historical checkpoints.

Docker recovery is complete. The original database has migrated to `e0a64c7d123b`; [preservation evidence](evidence/week08-memory-v2/20260921/migration/preservation-result.json) confirms unchanged original-column counts and hashes in all 44 pre-existing tables. The API, durable worker and frontend run locally on CPU. The original release retains 10,594 real vectors at dimension 384. New requests freeze query device, checker and memory policies; old records retain their configuration identities.

Model setup now records basic, structured and project-contract checks separately for answer and checker roles. Enabling a configuration requires the latest successful checks for the exact saved versions. Live connectivity is recorded by provider. The current development pilots use the managed DeepSeek configuration and retain failures. [Nine current English reports](docs/delivery/week08-memory-v2/README.md) passed visual inspection across 45 pages, with identical delivery/project copies. Full/eight-member archive hashes and reconstruction are recorded in adjacent release sidecars.

Ordinary textbook questions default to full direct explanations. The integrated learner workflow supports claim-specific highlighted source fragments, opt-in learning memory with source/version/edit/disable/delete controls, and explicit hint tasks that progress through further hints or a full explanation. Teaching progress is independent of textbook/general-knowledge mode. Ordinary citation views respect the current hint allowance; access to the full source is an explicit recorded action. The current provider and Memory V2 changes extend these three retained product modules.


The [final release gate](evidence/week08-memory-v2/20260921/software-gate-release-final-20260922/software_gate.json) passed 828 Python and 86 frontend tests, all eight stages, zero skips and 487 unchanged source/configuration files. [Portable parity](evidence/week08-memory-v2/20260921/portable/source-parity-release-final-20260922.json) verifies 514 public source/configuration files and all 80 preserved runtime resources; the earlier fresh CPU installation and browser checks keep their original scope. [The registry preservation receipt](evidence/week08-memory-v2/20260921/ledger-release-final-20260922/preservation-verification.json) records 180 appended observations while preserving original IDs, requirement/status fields and prior history.

The [terminal results and limitations](docs/execution/memory-v2-results-20260921.md) report B2−B1 +25.00 percentage points, T2−T1 −16.67 points and M4−M3 −2.78 points; all three registered 95% paired intervals include zero. A1 has only two valid judgments among 19 delivered answers. Measured usage across 1,919 retained attempts gives an estimated CNY 9.31490148; this is a tariff estimate, not a billing statement. Independent human ratings and oracle confirmations remain zero.


The [retained packaging failure and bounded correction](evidence/week08-memory-v2/20260921/packaging/release-fix-verification.json) record a reconstruction mismatch for the verified `resources/official-corpus/corpus.jsonl.gz` asset. The exact resource-path exception preserves its required category, size and hash checks; other archive paths remain excluded. The first nine ZIPs are retained as failed artifacts. Five focused checks and the final full gate passed after changing only the packager and its existing regression test. Scientific outputs, study code and the private research archive are unchanged. New archive hashes and reconstruction are recorded in adjacent release sidecars.

## Week 8 current checkpoint — 16 September 2026

Week 8 includes research and integrated controls for all eight improvement tracks: versioned question requirements, source-validating evidence reuse, complementary packing, bounded facet retrieval, explicit textbook/general-knowledge modes, CPU portability, teaching instructions and safe administrator traces. The 120-case catalogue is developer-authored regression material with independent labels blank. [The Week 8 record](docs/execution/week08-delivery-20260916.md) preserves v8's actual 110-question, 14-teaching and six-robustness outcomes, including failures, and the separately verified v9 changes. The final current software gate passed 427 Python/56 frontend checks with 365 source files unchanged. V9's post hoc 37-case live regression met 35 fixed automated expectations; W8-055 and W8-082 remain recorded deviations, and all 127 citation identities matched. Earlier v8 results, independent semantic review and final package reconstruction retain separate scopes. The original four-book corpus, accounts, history and all 512 September 13 benchmark outcomes retain their identities.

Reconciled on 13 September 2026. Start with [PRD](PRD.md), [SPEC](SPEC.md) and [PLANS](PLANS.md). The original 108 tasks, 60 acceptance checks and 12 responsive subchecks remain authoritative. The [upgrade record](docs/execution/answering_upgrade_20260913.md) records current execution, failed attempts and remaining acceptance. The [8 September handover](HANDOVER_20260908.md) is retained as a dated historical record.

## Existing working installation

Project: `E:/5703/learning-assistant`. Browser: `http://127.0.0.1:5173`. API: `http://127.0.0.1:8000`. PostgreSQL: `127.0.0.1:15432/learning`. One durable worker processes requests. Preserve `.env`, `.secrets/model-config.key`, the Docker data volume and source storage. The active managed revision selects real `deepseek-flash`; environment mock settings apply only when no managed revision is active. Failed real calls never fall back to simulated answers.

Administration > Models supports preset/custom protocol, endpoint/model/key, immutable save, real connection test and explicit enable. Queued requests and experiments keep their frozen configuration. Supported adapters cover OpenAI-compatible services, Azure v1, Ollama compatibility, native Anthropic and native Gemini. Only the configured DeepSeek endpoint has been externally exercised. [Model administration](docs/model-administration.md) explains tokenizer choices, encryption and safe errors.

Administration > Accounts connects creation, password reset, deactivation and restoration. Administration > Diagnostics shows actual outcomes and distinct candidate/submitted/cited counts. Learners ask questions, follow up, adjust preferences, inspect citations, manage their own sessions and submit feedback.

## Real knowledge and preservation

Active corpus: `4f11bd70-a486-4d16-b216-78cfe499530a`; four official OpenStax books, 4,638 physical pages, 10,594 real 384-dimensional E5 vectors. [The per-book report](docs/execution/openstax-corpus-report.md) gives editions, official URLs, dates, licenses, hashes, source locations, coverage, 73 reviewed exclusions, 15 recovered originals and attributable retrieval examples. Model: `intfloat/e5-small-v2@ffb93f3bd4047442299a41ebb6fa998a38507c52`.

[Migration verification](evidence/answering-upgrade/20260913/migration-preservation.json) proves the additive upgrade retained the previous corpus, identity/profile and saved answer/evidence fingerprints. Private pre-upgrade backup: `artifacts/backups/pre-answering-upgrade-20260913/manifest.json`. Later verification conversations are later records and are not claimed to be in that snapshot.

The extra post-upgrade full database/deployment-key backup and distinct restore was prepared but not executed: automatic approval review requires explicit authorization for that exact sensitive copy. [Blocked-operation record](evidence/answering-upgrade/20260913/post-upgrade-recovery-blocked.json). Preserve the original `.env`, key, database volume and source storage; the existing pre-upgrade backup remains available at its recorded scope.

The portable corpus exports the four required documents, real processing/release lineage and source recovery files. Import requires an empty corpus, verifies every source hash and active release relationship before commit, and refuses to overwrite a different existing corpus. [Isolated import and repeat-import rejection](evidence/answering-upgrade/20260913/portable-corpus-checked-import.json). Existing user histories remain in the original installation.

## Complete package startup

The full package contains English code/docs/tests, public evidence, four original PDFs, recovery artifacts, real corpus/vector data, pinned E5/reranker/DeepSeek-tokenizer assets and tiktoken caches. `PACKAGE_MANIFEST.json` lists all files and hashes. Existing users/history, provider credentials, deployment encryption keys, private evaluator references, installed dependencies and browser profiles are excluded.

Extract to a new local directory. Prerequisites: Windows x64, Python3.13, Node/npm and Docker Desktop. Local queries can use CPU; an available compatible NVIDIA device is required only when CUDA is explicitly selected. Keep the retained corpus build identity unchanged. Initial setup downloads locked Python/npm dependencies. Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/release/start_local.ps1 -Install
```

The launcher uses separate Compose project `cs30-portable-<installation-id>`, PostgreSQL port `15532`, API port `18000` and browser port `15173`. It creates fresh secrets, migrates/imports/verifies the corpus, then starts the API, worker and frontend. Existing environment files are preserved; occupied application ports cause an explicit stop. Process IDs and logs are in `artifacts/runtime`.

Administrator login: `admin@example.com` / `Passw0rd!`. Change your own password under Your account; manage other development accounts under Administration > Accounts. A fresh installation initially uses clearly labelled simulated answering with real retrieval. Configure/test/enable a provider to use real answers.

## Eight assigned workstreams

Each member ZIP contains `README.md`, `OWNED_FILES.json` and `repo_files/`, with disjoint whole-file ownership. Shared infrastructure and large resources come from the complete package. `EIGHT_MEMBER_INVENTORY.json` gives the exact union, hashes, original task IDs and integration order. Assignment records responsibility and review scope; Codex performed the shared implementation.

| Member | Assigned area |
| --- | --- |
| Xianshu Zhang | Integration, contracts, release and documentation |
| Hongle Yang | Official sources, processing, quality and corpus publication |
| Chengzhou Liu | Real embeddings, retrieval and contextual query preparation |
| Sijin Lu | Provider protocols, generation, token budgets and citations |
| Pengyuan Xia | Learner preferences and independent presentation studies |
| Zeping Liao | Accounts, model settings, durable chat, diagnostics and operations |
| Baiqing Huang | Learner/administrator UI and responsive interaction |
| Chong Zhang | Evaluation, regression verification and acceptance evidence |

## Preserved 13 September verification and remaining review

[Current browser proof](artifacts/reports/frontend/admin-settings/verification-summary.json) covers model save/test/enable/restore, accounts, a saved live answer with five submitted passages and two displayed citations, exact source inspection, keyboard focus, reload persistence and 1440/390-pixel layouts. Controlled transport tests for other adapters do not certify live vendor connectivity.

The first real 20-question suite passed 17 automated checks; the second passed 19. Both complete reports and failures remain in `evidence/answering-upgrade/20260913/`. AI review of the second found a gas-law retrieval gap, an omitted osmosis qualification and technical beginner wording. The third identical 20-case run passed all automatic checks, including 16 answers, two expected refusals, one clarification and one social response. The 13 September software checkpoint passed 312 Python and 51 frontend tests, including the later bounded E5 instance-reuse change. That change retains exact real vectors and ordered hits across eight reference and 32 cached encodes. Complete results and remaining AI-review limitations are in the [delivery review](docs/execution/upgrade-delivery-report-20260913.md); automatic status/provenance alone does not establish scientific or teaching quality.

Both frozen research protocols completed all 512 scheduled E0/E1 conditions, separately from interactive optimization. Pooled OpenQA EM was 23.44% for E0 and 14.06% for E1; MCQ accuracy was 96.88% and 67.19%. These fixed-prefix results show no basic-dense E1 improvement. All refusals and two pre-provider memory errors remain in the denominator. Lexical metrics are proxies; unreported provider cost stays null. Independent source relevance judgments, blind human ratings, full-book diagram/equation fidelity, physical devices, native IME and assistive-technology checks retain their exact remaining scope. Earlier results are dated evidence, not current blanket acceptance.

The [13 September archive review](evidence/answering-upgrade/20260913/review-member-reconstruction.json) reconstructs all 479 assigned files from eight member packages without overlap and matches all 205 tested runtime files. The final delivery folder contains `PACKAGE_VERIFICATION.json` and `EIGHT_MEMBER_RECONSTRUCTION.json` for the final archive identities and repeated verification.

## CPU installation and Week 8 delivery status

For a fresh extracted complete package, use `powershell -File scripts/release/start_local.ps1 -Install -Device cpu`. Initial installation downloads locked dependencies; `auto` installation selects the CPU lock, while explicit CUDA selects the retained CUDA lock. Existing installations can set `LOCAL_MODEL_DEVICE=cpu` for both API and worker at their normal coordinated restart. New requests freeze that policy; queued historical requests keep their recorded configuration. Unavailable explicitly requested accelerators fail visibly, and failed model loads are not retried on a different device.

The two actual CPU retrieval reports and 331/51 software gate are linked from the [Week 8 record](docs/execution/week08-delivery-20260916.md). Fresh Windows CPU package startup and explicit mock-answer flows now pass their separate verification. No original model key was copied and no live provider was configured in that installation. Final nine-archive reconstruction/hash evidence remains pending its sidecars. The eight member reports cover completed Week 8 research/design and implemented additions plus Week 9 targets. Existing September 13 archive identities, private backups and historical live results remain unchanged; no new sensitive backup/export was performed.

## Week 8 pre-expansion CPU installation evidence

[Fresh Windows CPU installation](evidence/week08-delivery/20260916/cpu-install/summary.json) passed new dependencies, migrations/import of 48 source files and 10,594 real vectors, four HTTP diagnostics plus cancellation/history, and a separate two-turn 1440/390 browser check. Answers were explicitly mock, paid calls zero, and no original key/private history was copied. [Source parity](evidence/week08-delivery/20260916/cpu-install/source-parity.json) covers 385 non-Markdown source/configuration files; all 80 public corpus/model resources were also verified. Physical new-laptop/MPS and broader performance/semantic/human acceptance remain separate. Final Week 8 ZIP sidecars/reconstruction are pending the archive phase.

## Historical v8 software checkpoint — 16 September

[The v8 software gate](evidence/week08-delivery/20260916/software-gate-v8-final/software_gate.json) completed at 2026-09-16T05:57:32Z with **383 Python tests and 53 frontend tests**, all eight stages passed and **359 source files unchanged**. It covers the frozen v8 implementation and catalogue v3 grouping checks. Earlier 331/369/377 checkpoints remain dated. This software result does not certify answer science, new live/provider outcomes, independent labels or physical-device acceptance. The v8 runtime results are retained in the Week 8 record. V9 verification and final archive reconstruction have separate identities.

## Current v9 software and live checkpoint — 16 September

[Final current gate](evidence/week08-delivery/20260916/software-gate-release-final/software_gate.json): **427 Python tests, 56 frontend tests**, eight stages passed, **365 source files unchanged**, completed 2026-09-16T06:33:30Z. [Actual v9 regression (public summary)](evidence/week08-memory-v2/20260921/privacy-relocations/public/4d11c5fec1e1-v9-targeted-live.json): all 37 fixed post hoc cases terminal, 35 automated expectations met and W8-055/W8-082 retained as deviations. [All 127 citation identities](evidence/week08-delivery/20260916/integrated/v9-source-verification/source-verification.json) matched persisted source text and locators. These structural/state/source checks do not certify claim entailment or learning quality; independent ratings remain blank. Current CPU-only continuation, explicit live general-mode continuation and 1440/390 general/fallback browsers passed their scoped checks; the exact mixed-question mock refusal and prior live/helper failures remain retained. Final package sidecars record archive hashes and isolated reconstruction separately.


Public delivery note — 21 September 2026: links labelled **public summary** open numeric summaries of retained historical records. Exact raw record hashes and restoration paths are listed in the [private relocation manifest](evidence/week08-memory-v2/20260921/privacy-relocations/legacy-relocations.json). Full questions, reference labels, model text and blank review forms are distributed only in the separate authorized research bundle. These link changes do not alter any historical execution result or provide new semantic or human validation.
