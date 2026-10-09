# CS30-1 Source04 delivery: Chong Zhang's attributed source partition

Source version: **CS30-1_Main_20261008_b94f69f894ce**. Public-source index SHA256: `88451d11075975db45e2102ffadf5e26f2190d4d03060ca6c3721993448ab890`.
This is an actual packaging successor with 1489 public source files and one
shared set of 85 public startup/model/textbook resources. Nine final English
DOCX reports are PENDING in this phase. `final_release_frozen=false` and
`project_complete=false`. Owner assignment describes domain responsibility,
not evidence of who personally executed or reviewed the work.

Use the COMPLETE_PROJECT_SOURCE04 archive for installation. The eight OWNER
archives contain disjoint assigned source files and reference the same shared
runtime; they are module handoffs within one product. They contain no copies
of the large resources. All earlier archives and experimental results are
preserved. Source04 changes only the two cumulative ledgers and the new dated
measurement report; the tested Source03 application code is unchanged.

## Fresh local CPU startup

Extract the complete archive into a new short directory. Read `README.md` and
`docs/runbook.md`. Host prerequisites are Python 3.13, Node >=22.12, PowerShell,
and Docker Desktop with Linux Compose. Python/frontend dependencies and the
PostgreSQL/pgvector image use their public registries. Check free disk space
before installation. No installed virtual environment or node_modules is
bundled. From `learning-assistant`, choose unused loopback ports and run:

```powershell
.\start_candidate.ps1 -Install -Device cpu -DatabasePort 15540 -ApiPort 18010 -FrontendPort 15180
```

Use the launcher's directory-specific Compose project and fresh disposable
database volume. Keep any initial credential file private. For acceptance,
use isolated synthetic data; do not connect to an existing learner database.
Real answering providers require a separately saved, authorized configuration;
the public package supplies no key or credential store. Existing pinned local
retrieval assets are included. This packaging run did not install dependencies,
run the full installer, start services, access a database, or call a provider.

## Current acceptance scope

The dated report
`docs/execution/20261008-default-rag-browser-and-matched-quality-evidence.md`
records the actual software, browser, retrieval, model, timing and cost evidence
with its source identities. The historical full Mock gate predates the narrow
PDF-page query repair; current targeted tests and separate native observations
retain their own scope. The successful actual browser follow-up is one complete
answer with citations and refresh persistence, not a full-answer p95 sample.
Five matched DeepSeek requests returned invalid protocol content, so a valid
semantic comparison remains unavailable. Packaging supplies no additional
live-model, PostgreSQL, clean-installation or physical-device qualification.

Independent human learning measures, complete gold IR labels, semantic quality
non-inferiority and the preregistered warm end-to-end p95 improvement remain
open or null as recorded. A SHA/CRC/source-coverage pass does not close those
requirements. Private databases, actual dotenv files, secrets, experimental
Gold, learner/session data and runtime caches are excluded.
