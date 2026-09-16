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
The 8 September source-only archive excluded weights. The 13 September complete
runnable package includes the fixed checkpoint, tokenizer and original model card
under `artifacts/huggingface`; its embedded manifest identifies every byte by hash.

`cross-encoder/ms-marco-MiniLM-L6-v2` is pinned to revision
`233902d25c440f23af6f7d6e94d2946bac0bee0a`; its owner model card records
Apache2.0 terms. The checkpoint and original model card are included in the complete
package. The configured interactive R2 candidate reranking and optional R3 comparison
keep explicit configuration identities and do not change the active corpus or E1.

`deepseek-ai/DeepSeek-V4-Flash-0731` tokenizer files are pinned at
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`. The package retains its original README,
MIT LICENSE and source URL/hash manifest beside the tokenizer. No DeepSeek model
weights or provider credential are distributed. The service alias `deepseek-flash`
is tested separately; provider-side checkpoint equivalence is not asserted.

SciQ is acquired from the research owner's `allenai/sciq` repository at revision
`2c94ad3e1aafab77146f384e23536f97a4849815`, with CC BY-NC3.0 source terms.
Its original Parquet and derived private inputs, labels, supporting passages and
preflight records remain evaluator-only under `artifacts/evaluator-private`.
They are not textbook corpus content or learner inputs. Acquisition/projection
evidence is documented in `docs/sciq_acquisition.md`.

The application keeps simulated answer output visibly identified as mock.
Source processing and learned-vector execution do not certify answer correctness,
independent human ratings or complete graphical/mathematical fidelity.
