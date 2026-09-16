# CS30-1 Learning Assistant: current handover

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

Extract to a new local directory. Prerequisites: Windows x64, Python 3.13, Node/npm, Docker Desktop and an NVIDIA CUDA-capable device for the retained corpus configuration. Initial setup downloads locked Python/npm dependencies. Run:

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

## Verification and remaining review

[Current browser proof](artifacts/reports/frontend/admin-settings/verification-summary.json) covers model save/test/enable/restore, accounts, a saved live answer with five submitted passages and two displayed citations, exact source inspection, keyboard focus, reload persistence and 1440/390-pixel layouts. Controlled transport tests for other adapters do not certify live vendor connectivity.

The first real 20-question suite passed 17 automated checks; the second passed 19. Both complete reports and failures remain in `evidence/answering-upgrade/20260913/`. AI review of the second found a gas-law retrieval gap, an omitted osmosis qualification and technical beginner wording. The third identical 20-case run passed all automatic checks, including 16 answers, two expected refusals, one clarification and one social response. Current software verification passed 312 Python and 51 frontend tests, including the later bounded E5 instance-reuse change. That change retains exact real vectors and ordered hits across eight reference and 32 cached encodes. Complete results and remaining AI-review limitations are in the [delivery review](docs/execution/upgrade-delivery-report-20260913.md); automatic status/provenance alone does not establish scientific or teaching quality.

Both frozen research protocols completed all 512 scheduled E0/E1 conditions, separately from interactive optimization. Pooled OpenQA EM was 23.44% for E0 and 14.06% for E1; MCQ accuracy was 96.88% and 67.19%. These fixed-prefix results show no basic-dense E1 improvement. All refusals and two pre-provider memory errors remain in the denominator. Lexical metrics are proxies; unreported provider cost stays null. Independent source relevance judgments, blind human ratings, full-book diagram/equation fidelity, physical devices, native IME and assistive-technology checks retain their exact remaining scope. Earlier results are dated evidence, not current blanket acceptance.

The [current archive review](evidence/answering-upgrade/20260913/review-member-reconstruction.json) reconstructs all 479 assigned files from eight member packages without overlap and matches all 205 tested runtime files. The final delivery folder contains `PACKAGE_VERIFICATION.json` and `EIGHT_MEMBER_RECONSTRUCTION.json` for the final archive identities and repeated verification.
