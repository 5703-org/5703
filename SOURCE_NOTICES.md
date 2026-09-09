# Source identities and retained notices

This local project preserves the user's original documents and earlier implementation
materials at their recorded workspace paths. The current source package is separate
from those unchanged originals. Their inventory, hashes and adaptation decisions are
in `docs/foundation/source_inventory.md`, `docs/execution/source_files.json` and
`docs/foundation/handover_migration.md`. No new license grant for the project's own
code is assigned by this notice; upstream files retain their applicable notices.

## OpenStax textbook material

The current four-book corpus uses Anatomy and Physiology 2e, Biology 2e, Chemistry 2e
and Concepts of Biology from official OpenStax PDF URLs. The actual acquired PDFs'
physical page4 states ©2026 Rice University and Creative Commons
Attribution-NonCommercial-ShareAlike4.0. Access for free at openstax.org.

The original downloaded PDFs remain unchanged. Processing normalizes native text,
records removed running furniture and reviewed cover/blank exclusions, and links
14 reviewed local OCR transcriptions plus one exact publisher image description.
These are processing adaptations, not replacement official editions. Source excerpts,
rendered review images and processed text retain book/title/page/hash attribution.
Exact origins, editions, digital ISBNs, acquisition dates, license links and processing
limits are in `docs/execution/openstax-corpus-report.md` and
`evidence/openstax/*-acquisition.json`. Original embedded notices and identified
trademark/third-party limitations remain authoritative.

- [OpenStax](https://openstax.org/)
- [CC BY-NC-SA4.0 terms](https://creativecommons.org/licenses/by-nc-sa/4.0/)

## Model and evaluation sources

`intfloat/e5-small-v2` is pinned to revision
`ffb93f3bd4047442299a41ebb6fa998a38507c52`; its model card records MIT terms.
Exact downloaded model/tokenizer file hashes are in `evidence/corpus/e5_download.json`.
Model weights and their caches are separate local artifacts, not embedded in the
source handover archive.

`cross-encoder/ms-marco-MiniLM-L6-v2` is pinned to revision
`233902d25c440f23af6f7d6e94d2946bac0bee0a`; its owner model card records
Apache2.0 terms. The optional R3 comparison uses separate model/cache/configuration
evidence and does not change the active corpus.

SciQ is acquired from the research owner's `allenai/sciq` repository at revision
`2c94ad3e1aafab77146f384e23536f97a4849815`, with CC BY-NC3.0 source terms.
Its original Parquet and derived private inputs, labels, supporting passages and
preflight records remain evaluator-only under `artifacts/evaluator-private`.
They are not textbook corpus content or learner inputs. Acquisition/projection
evidence is documented in `docs/sciq_acquisition.md`.

The application keeps simulated answer output visibly identified as mock.
Source processing and learned-vector execution do not certify answer correctness,
independent human ratings or complete graphical/mathematical fidelity.
