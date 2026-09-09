# Corpus rebuild and quality review

The executable pipeline accepts administrator-owned PDF/TXT assets. The portable example in `pipelines/examples/authored_manifest.json` contains 443 bytes of original authored fixture text, SHA-256 `70fe7dd0f4229f9d74d84eb49de04312b7ce3de9277491c81f3b0f69ea3ec28a`. It is a software demonstration and is not an approved OpenStax corpus or evidence that the historical pilot pages were reviewed.

Run from the repository root in the configured backend environment, after migrations and an explicitly seeded development administrator. The worker may be continuously running; `--once` is provided for a controlled one-job rehearsal.

```text
python -m app.cli ingest --manifest pipelines/examples/authored_manifest.json
python -m app.worker --once
```

The ingest receipt prints document, original version, processing run and job IDs. Use the returned processing ID; never paste another machine's ID into a new release. `GET /api/v1/jobs/{job_id}` must show success and `GET /api/v1/processing-runs/{processing_id}/quality` must show `ready`. Both quality and comparison routes require administrator authentication. The repeatable tests use a disposable PostgreSQL database and the same routes in `tests/integration/test_corpus_runtime.py`.

The example produces two source units and two chunks with default settings. It has no blocked/excluded units. TXT page `1` means the single text-source location; sections are the real Markdown headings. pypdf preserves one-based physical PDF pages. No synthetic page numbering is presented as a printed textbook page.

Prepare a local release configuration using the returned ID:

```json
{"name":"Authored biology fixture v1","processing_run_ids":["RETURNED_PROCESSING_ID"]}
```

```text
python -m app.cli corpus-build --config YOUR_RELEASE_CONFIGURATION.json
python -m app.worker --once
python -m app.cli corpus-activate --release RETURNED_RELEASE_ID
```

Only activate a release whose saved state is `validated`. The manifest records exact processing IDs, chunk IDs, chunk/vector counts, dimension, model revision, preprocessing signature, configuration hash, content hash and float32-canonical embedding hash. PostgreSQL executes exact cosine ordering with pgvector `<=>`; it is not a Python-only search. Mock embeddings are normalized lexical fixture vectors. A learned E5 release requires separately configured pinned model weights and its actual tokenizer; selecting an unavailable model fails explicitly.

## Source and processing fields

| Record | Meaning and invariants |
| --- | --- |
| Document | Administrator title, edition, origin, use/attribution statement and current active/revoked state. A stated license is provenance metadata, not an invented permission review. |
| DocumentVersion | SHA-256 of exact original bytes, size, detected PDF/TXT media type and hash-derived storage path. Identical upload reuses this immutable original. |
| ProcessingRun | Exact original version plus immutable configuration hash. Parser `pypdf_bookmarks_v5`, cleaner `nfc_conservative_v2`, chunker `token_spans_v2` and tokenizer revision identify current processing. V5 derives sections from actual PDF bookmark destinations, preserves pre-heading continuation and records unextracted visual content. Earlier runs retain their original revision. Changed configuration produces a new run. |
| SourceUnit | Sequence, physical page, real section, exact extracted raw text, cleaned text, quality and original issue objects. Persisted SHA-256 values for raw/clean text live in the run's `counts.source_unit_hashes`. |
| Quality report | `source_quality_v1` exports actual raw/clean text and hashes, issue severities, changed-text counts, exclusions and configuration. Recorded report hash and counts must reconcile. Older records without recorded hashes are explicitly `unrecorded_legacy_or_incomplete`; their history is not rewritten. |
| Chunk | Exact cleaned text/hash, section, pages, measured body-token count and source character spans. Span offsets include source-unit and chunk-local start/end; gaps contain only whitespace. Processing ID changes never overwrite old chunks. |
| ReleaseChunk | One vector per `(release_id,chunk_id)` with exact model revision/dimension. Empty, zero, nonfinite, mixed or unnormalized vectors prevent publication. |

## Quality and exclusions

NFC normalization preserves scientific superscripts. Soft hyphens and zero-width markers are removed; hard line-end hyphens retain their spelling and produce `HYPHENATION_REVIEW`. Repeated page-edge furniture can be removed from cleaned text with a warning and retained raw text. An unreadable or empty unit is blocking. A recognized furniture-only unit is inspectable and produces no chunk.

A completed processing job may have a `quarantined` run. Inspect every blocking unit; a successful job does not mean the source is eligible for a corpus. Reprocessing uses a new configuration containing an exclusion map such as `{"2":"Unreadable fragment excluded after source inspection."}`. Invalid unit numbers or blank reasons fail. Blocking issues remain in the original run, and excluded units remain in the new quality report. Excluded units never enter chunks. Excluding every usable unit fails rather than producing an empty release.

For PDFs with bookmarks, contents lines do not create body sections. Actual section destinations and aligned heading text determine boundaries; original characters before a mid-page heading retain the previous section. Image/drawing operations carry `UNEXTRACTED_VISUAL_CONTENT`; pages with fewer than 100 non-whitespace native characters and visual content are blocking until specifically reviewed. A warning does not prove that an equation or diagram survived extraction. Source locators explicitly say PDF physical pages and warn that figures or formulas may require viewing the original PDF.

Verified publisher alternatives use `pipelines.supplements.apply_publisher_supplements`. Their exact HTML bytes, element/text hashes, PDF hash, physical page and matching review are pinned in configuration. The original insufficient PDF unit remains inspectable as `supplemented`, with unchanged raw text and blocking observation; a distinct ready unit contains the attributed publisher description. Quality reports reconcile `supplemented_units`. A supplement does not imply complete recovery of other diagrams or mathematical layout.

`GET /api/v1/processing-runs/{before_id}/diff/{after_id}` compares completed runs of the same document. It exports configuration changes, raw-version reuse, source-unit added/removed/changed records, exact unchanged chunk pairs and changed chunk groups matched by physical source overlap. Different UUIDs alone are not changes. Split/merged chunk groups retain both sides' IDs, text hashes and source spans. Changed groups require qrel review or reannotation; no relevance grade is automatically transferred.

## Recovery and rollback

Processing and release jobs check their current execution token before each short publication transaction. Parsing/tokenization/embedding calls hold no Job row lock. Stop and stale recovery mark unfinished artifacts failed with a safe next action; an old result cannot turn them ready/validated after its lease is gone. The final artifact and successful Job status commit together. A failed processing attempt can be explicitly reprocessed with the same configuration, producing a new Job while retaining the old terminal job. A failed release can be rebuilt as a new release; any partial old vectors remain outside retrieval.

Activate A, build/activate B, then run `python -m app.cli corpus-rollback --release A_ID` to restore intact A. An invalid or unavailable target leaves the current pointer unchanged. Changed processing, embeddings and inactive sources never rewrite historical answer evidence. Current deactivation blocks new retrieval; revocation makes protected historical evidence explicitly unavailable.

An older release with no recorded configuration/vector fingerprints is explicitly unverified; recomputing today's hashes does not prove they were unchanged historically. Reprocess its original source under current recorded revisions and build a new verified release. Do not backfill the historical manifest or relabel a missing baseline as a successful rollback. Old answer snapshots and original manifests remain preserved.

The original Concepts of Biology PDF was absent from the supplied source tree. The official acquisition on 2026-09-08 recovered bytes matching its historical SHA-256 `da0ffc8585e172f04eb0abb08949087baf85cc229ef2736ef06e5aa17094b1f6`; acquisition and page-review evidence are separate under `evidence/openstax`. This authored example and its quality counts do not amend historical counts. Current original-page review and any new processing decisions must be explicitly recorded.

## Verification evidence

`tests/unit/test_pipeline.py` verifies cleaning, real authored PDF byte extraction, physical locators, measured tokenizer windows and exact span reconstruction. `tests/integration/test_corpus_runtime.py` verifies actual uploads, quarantine/exclusions, quality hash exports, changed/unchanged/split processing comparisons, exact PostgreSQL vector ordering, compatible caches, corruption rejection, concurrent Stop/recovery and A→B→A rollback. `evidence/ai/verification.json` identifies the actual focused runs. Live model quality, real textbook review and scientific comparisons remain separate evidence.

## Current official four-book execution

The full current corpus is documented in [openstax-corpus-report.md](execution/openstax-corpus-report.md), with exact raw PDF identities and all current source/release/database evidence. The formal active corpus is genuine E5/pgvector, independently of the mock answer adapter. Its original/quality/processing history is separate from the authored example above.

On a configured copy with matching official originals and retained reviewed recovery materials, the operational sequence is:

```text
python -m scripts.dev.acquire_openstax
python -m scripts.dev.prepare_e5
python -m scripts.verify.e5
python -m scripts.dev.package_image_transcriptions
python -m scripts.dev.openstax_pipeline reprocess-reviewed
python -m app.worker
python -m scripts.dev.openstax_pipeline status
python -m scripts.dev.build_openstax_release
python -m scripts.verify.formal_corpus --output evidence/openstax/formal-source-validation.json
python -m scripts.verify.formal_summary --input evidence/openstax/formal-source-validation.json --output evidence/openstax/formal-source-validation-summary.json
python -m scripts.verify.openstax_retrieval
python -m scripts.dev.publish_openstax
python -m scripts.verify.corpus_report
```

The worker is a separate persistent process; wait for every named processing job and the release job to succeed before the dependent verification commands. Downloaded bytes must match the pinned acquisition/review identities. If official URLs serve new bytes, preserve them under a new hash and perform new source review; the current source-specific decisions cannot be applied to a different PDF. See [source_ocr.md](source_ocr.md) for genuine local OCR and exact retained review artifacts, and [real_embeddings.md](real_embeddings.md) for pinned model acquisition. The finite upload limit is512MiB per original.

These project-checkpoint scripts preserve successful publication records and reject an attempt to overwrite them. Use a separate project copy/evidence target for a fresh reconstruction, with a new empty database and storage. Do not reuse another database's processing/job IDs or delete current evidence to force a rerun. Full restoration of the current immutable corpus has separately passed into a distinct database; reconstruction from scratch remains a separate repeatability check.


## Recorded parser-v5 reconstruction

The current versioned rebuild is under `evidence/openstax/v5/`. The actual first seven pages of each official PDF were checked before queuing full runs. V5 carries only real bookmark headings between pages; synthetic physical-page labels remain local to their own page. Explicit v4 parsing remains available to reproduce historical semantics.

The full rebuild retained all 5,541 raw/cleaned source-unit texts and their issues, changed 20 page-label fields on physical pages 2–6, and preserved exact text/spans for 10,566 body chunks. Eighteen old frontmatter chunks became 28 correctly separated chunks, producing 10,594 current vectors. The real stored float32 vectors for every unchanged body pair are bit-identical. Compatible real vectors may be reused only after their model/input/dimension/hash guards; mock vectors never satisfy an E5 cache key. `processing-diff-summary.json` and `release-build-completion.json` record the actual results.

Use `python -m scripts.dev.reprocess_frontmatter_v5 plan`, then `queue` once, and `status` to inspect its separate registry. Its explicit configuration is `configs/corpus/e5_cuda_v5.json`. The queue command refuses a second registry; it does not alter the initial v4 evidence or activate a release. For a new repeated experiment choose a new evidence target and registered processing identities. Current versioned checks used:

```text
python -m scripts.dev.build_openstax_release --evidence-dir evidence/openstax/v5 --name "cs30_openstax_v0.2 official PDFs parser-v5 E5 real"
python -m scripts.verify.formal_corpus --registry evidence/openstax/v5/processing-registry.json --output evidence/openstax/v5/formal-source-validation.json
python -m scripts.verify.formal_summary --input evidence/openstax/v5/formal-source-validation.json --output evidence/openstax/v5/formal-source-validation-summary.json
python -m scripts.verify.openstax_retrieval --evidence-dir evidence/openstax/v5
python -m scripts.dev.publish_openstax --evidence-dir evidence/openstax/v5
python -m scripts.verify.corpus_report --evidence-dir evidence/openstax/v5
```

The source-summary file is derived from the completed full formal report and binds its SHA-256; publication checks that report and the exact processing set before switching. Existing versioned outputs are retained; do not overwrite them to rerun commands. The current report entry is updated from versioned evidence, while the original v4 publication and report remain preserved.
