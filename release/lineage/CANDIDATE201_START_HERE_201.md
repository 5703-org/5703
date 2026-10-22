# Experimental Complete Candidate201

This independent public candidate includes the Main199 baseline, phase200 lossless CHECK transport and phase201 corrections for ordinary-question false clarification and programmatic zero-RPC behavior. The final package manifest identifies its source. Keep existing installations and earlier ZIPs separate.

The bundle contains the four original OpenStax PDFs (Biology 2e, Chemistry 2e, Anatomy and Physiology 2e, and Concepts of Biology), their manifest-bound corpus/source objects/vectors, visual candidate catalogs, fixed public E5/MiniLM models, tokenizers and licenses. Preserve these original bytes and relative paths. Provider credentials, private encryption keys, learner histories and database files are excluded.

## Verify public files

Use Windows PowerShell, Python **3.13.x**, and supported Node: **22.x from 22.12**, **24.x**, or **26.x and later**. The normal managed-database path requires Docker Desktop with **Linux containers** and Docker Compose.

From this directory:

```powershell
.\start_candidate.ps1 -VerifyOnly
```

This reads the declared public files and checks their hashes. It does not install, hydrate runtime caches, start services, read an actual `.env`, access a database or send model requests. This file check is separate from startup and scientific acceptance.

## Install and start

This is a complete source/public-resource bundle, not an offline dependency installer. Locked Python/npm dependencies and any missing Docker image require their configured registries. Create environments locally; do not copy another installation's `.venv` or `node_modules`.

Choose free ports and run, for example:

```powershell
.\start_candidate.ps1 -Install -Device cpu -DatabasePort 15592 -ApiPort 18092 -FrontendPort 15192
```

The wrapper verifies and locally hydrates the fixed model assets, then invokes the native installer/launcher for dependencies, frontend build, a separately owned database, schema/corpus/visual import, API, interactive/background workers and frontend. Existing `.env` files are retained and must match the selected installation. Never point this command at a preserved development database. Generated runtime state is not part of the ZIP.

After successful readiness, open `http://127.0.0.1:15192`. Use `admin@example.com` and the locally generated password identified by startup, normally `.secrets/initial-admin-password.txt`; change it through Your account. Preserve this installation's model-encryption key after it is created.

A fresh installation uses visibly labelled mock answers. For a real provider, enter its key privately through **Administration > Models**, save, test and explicitly activate the revision. Provider tests and real answers can incur charges. No saved real-provider profile or API key is shipped.

## Defaults and observed limits

New ordinary chats start with **Check answer off**. Turning it on requests the additional semantic check; protected teaching/evaluation paths keep their mandatory checks. Fresh configuration uses `json_source_citations_v3` and `lossless_assertion_checker_tables_v3`, with ordinary retrieval caching enabled. Their supported-route fallbacks remain available. Existing `.env` files, model revisions, keys and checkbox choices are not rewritten.

This is an **experimental candidate with known scientific and delivery failures**, not an all-quality-passed release. The fixed development observations were:

| Scope | Observed result |
| --- | --- |
| Offline software regressions | 441 PASS; software scope only |
| Native preparation | 5 PASS; pre-provider scope only |
| Earlier phase200 paid attempt | STOPPED_SETUP, 0 GEN/0 CHECK; retained |
| Candidate201 OFF | 4/5 delivered; all four completed answers below 10 seconds; two answers (N1/N3) had scientific precision/source-oversimplification issues |
| Candidate201 ON | 2/5 delivered (N1/N5), neither within 10 seconds; three failed native gates |
| Scientifically clean and complete within 10 seconds | OFF 2/5; ON 0/5 |
| Both fixed cohorts | 14 reported calls: 10 GEN + 4 CHECK; conservative usage-based estimate CNY 0.602962, not a provider invoice; no new UNKNOWN requests |
| Clean-PC dependency installation and full fresh launcher/corpus startup | NOT RUN |

The isolated development runtime reused existing dependencies and the public assets hydrated from this bundle. It does not establish a clean-PC installation, a general ten-second guarantee, complete scientific correctness or human learning benefit. The strict local fence also blocked an urllib3 IPv6 capability probe to `::1:0`; therefore a clean network-fence audit is not claimed. The official execution-tool approvals succeeded; this local fence event was not a tool-approval rejection.

Read the final public [validation report](release/validation/FINAL-VALIDATION201.md) for per-case results, quality findings, failures and exact scope. No additional paid run is planned as part of package assembly.

## Recovery and preservation

Inspect this installation's `artifacts/runtime/processes.json` and role logs after startup problems. Identify the recorded owned processes before stopping/restarting them; a failed launch can leave owned processes alive. Preserve user databases, model keys, histories, source backups, earlier ZIPs and their failed-run evidence. Repeating startup without `-Install` reuses the installation's dependencies; use `-UseExistingDatabase` only after deliberately checking that installation's separate local configuration. Source replacement, process restart and database operations are distinct actions.

The optional [exact-base upgrade patch](release/patches/README.md) is for its documented Main199 base; do not apply it to this already-complete tree. Historical README/ledger links can refer to older retained workspace evidence that is not shipped. The current Candidate201 guide, canonical result report and validation pointer resolve within this package.
