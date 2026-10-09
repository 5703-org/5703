# Week 9 continuation delivery workflow

## Current release boundary on 30 September 2026

The [V11 complete release](week09-v11-release-status-20260930.md) has nine independently verified ZIPs, nine English DOCX reports and a scoped same-host isolated CPU/runtime acceptance. Its complete-project archive remains immutable. The post-release source passed its [successor eight-stage gate](../../evidence/week09-continuation/20260930/software-gate-successor-v12-2/software_gate.json) with 1,375 Python and 142 frontend tests, but its refreshed reports, archive reconstruction and selected installed runtime each require separate receipts before a successor ZIP is treated as released. The [interrupted first gate attempt](../../evidence/week09-continuation/20260930/software-gate-successor-v12-1-aborted.json) remains recorded. The original Week 7 baseline, 26 September release, V10 and V11 ZIPs, official sources, database and historical answers remain preserved. The workflow below uses a new destination and the current report-visual receipt for each successor build.

This workflow prepares a new 30 September delivery. The 26 September full archive, original Week 7 archive, project, official source files and databases are preserved. The V4 fresh CPU installation has a retained interruption/recovery receipt. The V9 candidate software gate passed 1,293 Python and 132 frontend tests; the earlier V8 study remains frozen. Final installed runtime parity is verified; continuation archive checks remain separate.

## Inputs and accountable ownership

`scripts/release/week09_continuation_delivery.py` is a separate successor to the preserved `week09_delivery.py`. It requires these exact immutable inputs:

| Input | Location | SHA-256 |

| --- | --- | --- |

| Original Week 7 full archive | `E:/5703/deliverables/answering_upgrade_20260913/final/CS30-1_Complete_Runnable_Project_20260913.zip` | `a880978703f850bfdc514bd232c97f5dc999709634459173abfb6218679b8927` |

| Original eight-member ownership | `E:/5703/deliverables/answering_upgrade_20260913/final/EIGHT_MEMBER_INVENTORY.json` | `a1b4973e869772d85b6f5fe0c6e3fe342f627c6304abcf234f4d95c46dd3fe08` |

| Latest retained full archive | `E:/5703/deliverables/CS30-1_Week09_Final_20260926/CS30-1_Week09_Complete_Project_20260926.zip` | `a3be2aae9a982d3850c5a87e8f7ab3851879b0ff6ff60e6a38cddef6c51ac4c1` |

Original owners take precedence over path-based assignments. Files added in later releases retain their recorded owners. The eight member ZIPs contain disjoint **complete current files**, cumulatively compared with the Week 7 baseline; they are not patch fragments. The complete archive retains all 80 verified runtime resources and three separately labelled optional ONNX resources from the 26 September release. Optional graph bytes remain outside member source packs and are explicitly supplied from the full archive during virtual reconstruction.

The new report directory is `docs/delivery/week09-continuation`. It must contain `Week09_Overall_Report.docx` and `Week09_<First_Last>_Report.docx` for all eight original members. Creation requires a receipt with `status: passed`, `every_page_inspected: true` and the exact nine `report_hashes`. The builder checks full-archive, assigned member and standalone report bytes. The earlier reports remain unchanged.

## Plan and creation commands

Run from the project root in the existing development environment. These commands use a new destination; existing nonempty destinations are rejected.

```powershell

python -m scripts.release.week09_continuation_delivery `

  --baseline E:/5703/deliverables/answering_upgrade_20260913/final/CS30-1_Complete_Runnable_Project_20260913.zip `

  --previous E:/5703/deliverables/CS30-1_Week09_Final_20260926/CS30-1_Week09_Complete_Project_20260926.zip `

  --ownership E:/5703/deliverables/answering_upgrade_20260913/final/EIGHT_MEMBER_INVENTORY.json `

  --destination E:/5703/deliverables/CS30-1_Week09_Continuation_20260930 `

  --plan-only `

  --plan-output E:/5703/week09_learning_20260930/packaging/plan-new.json

```

Plan-only hashes the declared inputs, resolves current source/resource membership, applies privacy exclusions and scans the selected current bytes for known configured secrets. It creates no destination or ZIP. Missing reports or their review receipt are explicit blockers. Once source, test and report freeze is complete, run the same command without `--plan-only`, add `--report-verification` pointing to the actual nine-report receipt, and use a fresh `--plan-output` path. Creation does not activate a model, migrate a database, start services or remove any baseline file.

The resulting full ZIP is `CS30-1_Week09_Continuation_Complete_Project_20260930.zip`. Eight named member ZIPs, nine standalone reports, `PACKAGE_MANIFEST.json`, `PACKAGE_VERIFICATION.json`, `CUMULATIVE_CHANGES.json`, `CHECKSUMS.sha256`, `PACKAGE_PLAN.json` and a runnable handover README bind their bytes and boundaries. Baseline removals are virtual reconstruction metadata for an isolated exact copy only.

## Independent archive check and startup

The two-stage workflow first materializes the authoritative package plan into a new isolated runtime with exact file hashes. Installation runs before final reports, so those reports can cite actual outcomes. After report completion, the single final ZIP is created and every runtime/configuration/resource member is compared with the tested staging. Documentation, completed evidence and report changes are enumerated separately. The [V4 checkpoint](../../evidence/week09-continuation/20260930/staging-installation-v4-summary.json) passed with explicit worker interruption/recovery; the next candidate still requires its final runtime identity and archive proof. No prior archive or installation is overwritten.

After creation, the separate verifier reads the actual ZIP entries, not just the builder's success flag:

```powershell

python -m scripts.release.verify_week09_continuation `

  --baseline E:/5703/deliverables/answering_upgrade_20260913/final/CS30-1_Complete_Runnable_Project_20260913.zip `

  --previous E:/5703/deliverables/CS30-1_Week09_Final_20260926/CS30-1_Week09_Complete_Project_20260926.zip `

  --ownership E:/5703/deliverables/answering_upgrade_20260913/final/EIGHT_MEMBER_INVENTORY.json `

  --destination E:/5703/deliverables/CS30-1_Week09_Continuation_20260930

```

It verifies nine unique archives, exact file membership/hash/size, historical ownership, zero member overlap, all resources, nine report identities and Week 7 baseline plus cumulative overlays plus declared optional graphs equalling the complete archive. It writes a new `INDEPENDENT_VERIFICATION.json` only after success and never restores or deletes files.

For a fresh runtime, extract the complete ZIP to a new directory and use `powershell -ExecutionPolicy Bypass -File scripts/release/start_local.ps1 -Install -Device cpu` from its `learning-assistant` directory. Supply distinct ports if existing services occupy the defaults. Docker Desktop, supported Python/Node and the documented local installation requirements apply; see [runbook](../runbook.md). Configure provider credentials locally. The archive contains no deployment key, authenticated browser state, account history or database. Mock answering and a configured real semantic checker have distinct capabilities; archive reconstruction does not prove a fresh live run.

For an empty corpus, the Windows PowerShell 5.1-compatible launcher generates 24 cryptographically random bytes as a 48-hex-character initial password. It atomically creates `.secrets/initial-admin-password.txt` after protecting directory inheritance for the current Windows user, then applies a current-user-only file ACL. Concurrent or repeated launches reuse the winning valid file. The password is supplied only to corpus import; the transient environment value is cleared in `finally`. Existing passwords, roles, account status and token versions are preserved. Startup displays the administrator email and a private password-file path only after verifying that the saved credential matches an active local administrator. It never prints the password. Read the file privately and change the password in **Your account** after first login. An invalid private file is preserved and fails explicitly. If a valid file no longer matches the active administrator, its path hint is withheld and the existing account is unchanged. The launcher does not guess or reset the password. The explicit `seed-demo --confirm-dev` development fixture retains its separate known test credential. Private files and local databases are excluded from public archives.

After installing the official corpus, startup verifies and idempotently imports all 5,543 visual candidates before launching services. It resolves each original PDF from installed or bundled storage by exact SHA-256; a missing or mismatched source, catalog or import stops startup. The four exact derived catalog paths/hashes retain OpenStax CC BY-NC-SA provenance and needs-review states. Import does not add them to released answer evidence or establish scientific correctness. [Nine focused credential checks](../../evidence/week09-learning/20260930/answer-core/portable-credentials-receipt.json) and [catalog integrity verification](../../evidence/week09-learning/20260930/packaging/visual-catalog-runtime-verification.json) retain their scoped evidence; the V4 installation passed with the worker interruption and recovery recorded above. Final installed source parity is verified; archive verification remains separate.

## Privacy and verification scope

On a current-user-owned directory where the direct ACL call is denied, the launcher uses Windows `icacls` to grant that owner, remove inherited rules and re-read the actual ACL. It requires the current owner, protected inheritance and exactly one full-control owner rule; failure stops before credential creation/startup. The [focused fallback check](../../evidence/week09-continuation/20260930/portable-acl-fallback-validation.json) passed. The [actual V4 installation](../../evidence/week09-continuation/20260930/staging-installation-v4-summary.json) then completed its first one-command launcher run without manual ACL changes, within an observed upper bound of 237.688 seconds. Its first cold chat worker exited with no captured exception: after 211.659 seconds of polling, explicit recovery recorded `WORKER_INTERRUPTED`; a separate CPU/mock retry succeeded in 12.259 seconds with one citation after 12 verified superseded staging services were stopped. The cause remains unknown and recurrence is not ruled out. Main/clone services and database volumes were preserved.

The full package also contains the four exact official-source visual catalogs under `evidence/week09-continuation/20260930/visual-full-attempt2/`, together with their manifest and the preserved original PDFs. Each `.jsonl.gz` path and SHA-256 is explicitly pinned; the manifest must match an original PDF among the 80 verified runtime resources. Their derived contents retain OpenStax CC BY-NC-SA provenance and `needs_review` status. Importing them does not constitute scientific review or publish them as answer evidence. Other evidence archives remain excluded, and these four catalogs are secret-scanned after decompression. The [17 focused packaging checks](../../evidence/week09-learning/20260930/packaging/visual-catalog-tests.xml) include actual miniature ZIP inclusion, source/hash refusal and decompressed-secret rejection.

Existing private research exclusions remain in force. The continuation additionally excludes private pilot/label data, provider responses, local test credentials and authenticated browser state; executable evaluator code stays public. Nested raw answer/reference/key fields in public Week 9 JSON are rejected. Known secrets from the local environment are scanned in memory, including DOCX XML, without printing their values. This mechanical scan cannot classify arbitrary unknown credentials, sensitive prose or screenshots; curated public-input review remains required.

The [packaging preparation receipt](../../evidence/week09-learning/20260930/packaging/preparation.json) records the authored miniature-archive tests and actual plan-only observation. Earlier setup failures are retained. The V7 plan-only check selected 4,649 files and reported the expected final-report/QA blockers. The V7 plan exposed a filename-filter omission of the authored portable-credential test. The [V8 correction](../../evidence/week09-learning/20260930/packaging/v8-release-verification.json) passed 19 focused tests and the complete gate. Its exact-path exception retains all actual credential/private exclusions and content scanning. Final archive and V8 runtime parity require actual verification receipts.

## Public reviewer materials

The [reserved retrieval audit](../../evidence/week09-continuation/20260930/reserved-retrieval-integrity.md) retains all 52 paired concept groups: 48 met source-anchor eligibility and four missed at least one required anchor. Conditional preparation then verified all 48 eligible groups. Formal V8 QA, teaching and offline AI judgment are terminal within that conditional population. No paired comparison against the 26 September release or SciQ E0/E1 has been executed on these new source-anchored cases. The [separate V7 reviewer deliverable](../../evidence/week09-learning/20260930/packaging/external-reviewer-v7.json) provides 21 blinded packets, two blank 21-row sheets and a scoring guide; [exact-copy verification](../../evidence/week09-learning/20260930/packaging/public-reviewer-copy-v7.json) preserves the approved bytes. Human ratings remain zero; coordinator mappings and hidden labels remain private. The approved materials are distributed in the sibling `CS30-1_Week09_Reviewer_Materials_20260930/pilot_v7/` directory, outside the runnable and member ZIPs.

Approved reviewer-only copies are delivered separately under `CS30-1_Week09_Reviewer_Materials_20260930/pilot_v7/`. The two CSV payloads retain their exact bytes as `ratings-1.csv` and `ratings-2.csv`. Both duplicate project directories were moved to an outside-project preservation folder after hash verification, so the frozen package privacy rules and metadata remain consistent. Private coordinator mappings and provider attempts stay outside both the public runtime and reviewer deliverable. The public relocation receipt records all source/destination hashes; no executable source changed.
The [V8 plan-only verification](../../evidence/week09-learning/20260930/packaging/v8-plan-verification.json) selected 4,679 files at that checkpoint. All 639 public paths from the 655-file software snapshot matched exactly; the other 16 are intentionally private evaluator catalogues and fixtures. The plan retained 80 official runtime resources and four exact visual catalogs. Its only listed blockers were the nine final English reports and their matching visual-QA receipt. Later report/evidence additions require a refreshed plan before materialization. No V8 installation or archive is claimed by this planning result.

## Formal teaching execution checkpoint

The [formal V8 automatic receipt](../../evidence/week09-continuation/20260930/formal-v8-automatic-sanitized.json) records all **240 scheduled requests terminal** on the 48 source-eligible concept groups. Textbook QA produced **32 answers, two clarifications and 14 failures from 48 requests**. Teaching produced **179 hints and 13 failures from 192 requests**: A delivered 47/48, and B, C and D each delivered 44/48. Every failure remains in its scheduled denominator. The separately blinded offline judge rated 211 delivered answers or hints and recorded 29 no-output outcomes. It used the same DeepSeek model family and assigned maximum correctness to every scored output, so these saturated ratings provide limited discrimination. Human ratings remain zero.

The paired teaching D-minus-A scheduled-endpoint estimate is **−0.0625**, with a 95% concept-group bootstrap interval of approximately **[−0.146, +0.021]** across 48 groups; this result provides no demonstrated D advantage. The study remains conditional on accepted source anchors: the unconditional retrieval audit retains **48/52 eligible groups and four misses**. No same-case paired comparison with E0, E1 or the 26 September release was executed, and learner gains were not measured. The 601 product calls and 211 offline-judge calls have zero unknown-call outcomes; their combined off-peak estimate is **USD 0.771599619**, with provider invoice reconciliation absent.

The integrated V9 checker candidate passed its [complete eight-stage software gate](../../evidence/week09-continuation/20260930/software-gate-v9-release-1/software_gate.json) with **1,293 Python tests and 132 frontend tests**, zero Python failures/skips and **657 captured source files unchanged**. Its canonical source-map SHA256 is `738168152a99f62c18c6d6492af934cc41d9b6d6491325a57b38aa253f759dd5`. The ordinary default remains `single_contract_correction_v1`. The explicit candidate `schema_contract_corrections_v2` permits a second checker correction only after eligible structural defects, while retaining strict validation and the shared four-call/180-active-second budget. The completed paired development probe retains the legacy default; final installation has passed its runtime checks; report and archive verification remain separate. Frozen V8 scientific results retain their original code, prompts and outcomes; the V9 software pass supplies no new efficacy measurement.

The [paired V9 development probe](../../evidence/week09-continuation/20260930/v9-checker-development/results.json) replayed four previously exposed V7 drafts and identical source evidence under both current checker policies. Each policy accepted **three of four fixed drafts**. Legacy used five real checker calls; the successor used six. Across all eight runs there were **11 checker calls, zero generation-model calls and 98,568 tokens**. The successor's delivered-run median was **5.000 seconds**, compared with **3.905 seconds** for legacy, with three delivered runs per policy. The tariff estimate is **USD 0.010857264**; invoice reconciliation is absent. One schema correction changed a partial-support opinion to supported on the unchanged draft, and that change awaits human review. The release keeps `single_contract_correction_v1` as the ordinary default; `schema_contract_corrections_v2` remains opt-in. The probe made zero database publications, used no reserved cases, and supplies no end-to-end delivery or independent quality advantage. Human ratings remain zero. Final CPU installation has passed its runtime checks; report and archive verification remain separate.

The [final V9 CPU installation](../../evidence/week09-continuation/20260930/staging-installation-v9-summary.json) passed its runtime checks in a new virtual environment and isolated database on the existing Windows host. All **1,051 installed runtime inputs** matched their preinstall hashes; the public package plan includes 641 gate source paths and excludes 16 private evaluation inputs. The installation retains four original PDF hashes, **10,594 real 384-dimensional vectors**, and **5,543 unreviewed visual candidates**. PyTorch is `2.8.0+cpu`, CUDA is absent, 78 installed distributions pass `pip check`, and the schema head is `f4a18bc67d20`. A cold CPU retrieval/mock-answer request succeeded in **22.424 seconds** with one exact Biology 2e citation at physical PDF page 235. A separate read-only CPU query retrieved and reranked 20 candidates in **8.7203 seconds**, preserving the full vector and release fingerprints. These are installation smoke timings. The launcher success marker and live services were verified; its child exited, but the output-capture wrapper did not expose an exit code. The original main database and existing services were untouched. Live-answer quality, another physical machine and Mac remain outside this check. Final ZIP/runtime parity and report/archive verification are recorded separately.

The separate reviewer deliverable also contains all 240 formal outcome packets with two blank 240-row sheets and 23 supplementary formal draft packets with two blank 23-row sheets. The separate one-draft packet retains its own blank sheet. The 41-file reviewer manifest verifies their hashes and sizes. Human ratings remain zero. These materials stay outside the complete runnable and eight member ZIPs.
