# Hongle Yang - Complete project module handover

Assigned domain: **Official sources, processing, quality and corpus publication**. This is the complete owned source partition at this
cutoff, not a reporting-week increment. The recorded ownership map defines
accountability; actual new changes and verification were executed by Codex. It
does not establish that this individual independently authored or reviewed them.

## Module scope and interfaces

Primary paths: `pipelines/; backend/app/modules/knowledge/`

Produces: Source assets, processing units, chunks, visibility and corpus versions.

Consumers and dependencies: Retrieval and source-viewer consumers. Use the canonical contracts, backend
persistence and shared dependency package from this same source set. Consult
`SOURCE_INDEX.json` for every owned path, exact byte hash and file classification.
The separate `CODE_INTERFACE_INDEX.json` records real Python declarations and
route decorators; it is an index of code, not a claim that every route was exercised.

## Complete source contents

Application/build source: 29 files. Separate engineering/test source:
27 files. Shared dependencies are in COMP5703_Common_Dependencies_Final_20261027.zip.
Combine the eight disjoint partitions and shared files to recover the exact full
source manifest `9ef78492ad5ec1aefd54526d2618e04636c1cb07563d59eb236832f63e30069e`. A personal partition is not a standalone service.

## Run and integrate

1. Reconstruct the complete project using the supplied reconstruction validator.
2. Follow `docs/FORMAL_INSTALLATION.md` for local PostgreSQL, assets and private
   configuration. Runtime entry: `scripts/release/start_local.ps1`.
3. For source development, use the locked dev dependencies. Frontend source builds
   with `npm ci` then `npm run build` from frontend/. Existing installed dependencies
   were reused for this acceptance; package scripts do not imply a new network audit.
4. Run the module's verification files listed in the index from the reconstructed
   project root. Python: `python -m pytest <listed-paths>`. Frontend: `npm test`.
   Integration tests require the explicit disposable test database prerequisite.
5. Run affected cross-module tests before integration. Preserve migrations, source
   versions, request identity, budgets, owner isolation and previous evidence.

## Evidence and completion boundary

Current free engineering evidence is in ENGINEERING_EVIDENCE.zip and the project
acceptance report. Each receipt states scope, failures and invocation. Historical
experiments retain their original denominators and model outputs; they are not
reclassified as newly passing results. Original source files are copied unchanged
at the manifest hashes, and test substitutes remain outside runtime membership.

Keep processing/source hashes and active-release fences intact.

The current package remains subject to the acceptance table. Provider configuration and the bounded real-model controls are documented in the
current report. Default options remain conservative. The acceptance table records
verified scope and measured research limitations.
