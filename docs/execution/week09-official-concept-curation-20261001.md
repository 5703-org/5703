# Week 9 official OpenStax concept-relation curation

Twelve finite relation proposals now use exact source passages from the current four-book OpenStax release. Three proposals belong to each book, with four `prerequisite`, four `related` and four `confusion` proposals overall. All twelve passed current released-source, chunk-span and original-PDF checks and were created through the existing administrator API in the isolated installed stage. Their registry state remains `proposed`, with independent human subject ratings pending.

The English [candidate catalog](../../configs/knowledge/openstax_concept_relation_candidates_v1.json) carries the exact API proposal, source-unit and quote hashes, processing/release IDs, chapter and physical PDF page, official URL, existing edition and licence record, real chunk IDs and ranges, rule and AI curation provenance. Its SHA-256 is `5c4dec9c35ff3d0986d44c4f50b5247bca0b64d65cc25635638f82ff775ba7cf`. The active release is `4f11bd70-a486-4d16-b216-78cfe499530a`.

| ID | Book | Type | Proposed concepts | Quotation page |
| --- | --- | --- | --- | ---: |
| AP-01 | Anatomy and Physiology 2e | prerequisite | Action potentials → skeletal muscle excitation-contraction coupling | 390 |
| AP-02 | Anatomy and Physiology 2e | related | Parathyroid hormone → bone resorption and calcium regulation | 240 |
| AP-03 | Anatomy and Physiology 2e | confusion | Innate immune response ↔ adaptive immune response | 937 |
| BIO-01 | Biology 2e | prerequisite | Light-dependent ATP/NADPH production → Calvin cycle carbon fixation | 239 |
| BIO-02 | Biology 2e | related | Photosynthetic energy storage → cellular respiration energy extraction | 207 |
| BIO-03 | Biology 2e | confusion | Mitosis ↔ meiosis | 312 |
| CHEM-01 | Chemistry 2e | prerequisite | Balanced chemical equations → reaction stoichiometry | 189 |
| CHEM-02 | Chemistry 2e | related | Chemical equation amounts → reaction enthalpy | 242 |
| CHEM-03 | Chemistry 2e | confusion | Heat transfer ↔ temperature measurement | 222 |
| CON-01 | Concepts of Biology | prerequisite | Chromosome structure → chromatin | 80 |
| CON-02 | Concepts of Biology | related | Photosynthesis → aerobic cellular respiration | 144 |
| CON-03 | Concepts of Biology | confusion | Prokaryotic cells ↔ eukaryotic cells | 75 |

## Curation and evidence rules

The local curation pass read only source units represented by real chunks in the active release. Each selected character range matched its pinned published source unit. Every overlapping chunk fragment was checked against its actual chunk text, and the union of those ranges covered each entire quotation. The four original stored PDFs passed their acquisition SHA-256 checks; all twelve passages matched text extracted from the recorded original physical page after explicit layout normalization. Eleven comparisons used whitespace and removed line-end hyphenation. CON-03 required retaining the wrap hyphen in `membrane-bound`; that exact adjustment is recorded per candidate. The original files and published texts were unchanged.

Prerequisite rules distinguish explicit pedagogical guidance from an AI-proposed study sequence based on a stated biochemical, mathematical or physiological dependency. CON-01 quotes the book's explicit suggestion to consider chromosomes first. AP-01, BIO-01 and CHEM-01 propose conceptual study order from the stated mechanism. Their recommendations remain subject to disciplinary review. Related proposals use an explicit named connection or energy/amount relationship. Confusion proposals use an explicit contrast to propose a distinction reminder; measured learner confusion remains unassessed. Qualifications such as aerobic respiration, ploidy and reaction amounts are retained in the quotation and rationale.

The [public curation receipt](../../evidence/week09-continuation/20261001/official-concept-relation-curation-20261001.json) pins the catalog, source dataset and importer/test hashes and records twelve original-page matches and twelve complete released-chunk range checks. It contains source IDs, hashes and counts. Full read-only source snapshots and the curation builder remain in `E:/5703/week09-private-db/concept-relation-curation-20261001/`. Curation used zero provider calls and zero database writes.

## Installed administrator import

The [import tool](../../scripts/release/import_concept_relations.py) calls the existing `POST /admin/learning/concept-relations` route. Its `validate` mode checks catalog structure, exact quote hashes, distinct sections and proposed-only provenance locally. `preflight` reads the current installation's administrator registry, book identities, published sections and exact reading units. `submit` repeats that preflight before creating proposals. Existing identical proposed/approved records are reported, changed quotes produce a conflict, and partial successes remain in the receipt. The tool has no approval operation.

The isolated local API preflight on port 18847 passed for all twelve source records. The subsequent authorized import created **12 proposals**, with **0 approval calls** and **0 provider calls**. The [public import receipt](../../evidence/week09-continuation/20261001/official-concept-relation-import-20261001.json) records their actual registry IDs and `proposed` state. Before/after fingerprints of the active release, 10,594 vector contents, original hashes and processing configuration hashes matched. Corpus activation, rebuilding and republishing were not called. This run verifies installed registration and quarantine; recommendation usefulness, subject review and learner effects remain pending.

Seven focused unit tests passed in 0.19 seconds, including quote/approval tampering and partial-import evidence. Scoped Ruff lint and format checks passed. Runtime source preflight and actual registration provide separate real-source evidence from these labelled HTTP unit fixtures.

## Reusable commands

Run from the installed project directory with an administrator bearer token already present in `CS30_ADMIN_TOKEN` for API modes. The token is read in-process and excluded from receipts.

```powershell
python -m scripts.release.import_concept_relations --catalog configs/knowledge/openstax_concept_relation_candidates_v1.json --mode validate --receipt artifacts/concept-relations-validate.json
python -m scripts.release.import_concept_relations --catalog configs/knowledge/openstax_concept_relation_candidates_v1.json --mode preflight --api-url http://127.0.0.1:8000/api/v1 --receipt artifacts/concept-relations-preflight.json
python -m scripts.release.import_concept_relations --catalog configs/knowledge/openstax_concept_relation_candidates_v1.json --mode submit --api-url http://127.0.0.1:8000/api/v1 --receipt artifacts/concept-relations-import.json
```

Independent subject reviewers can inspect the catalog's exact excerpts and chapter/page locators, assess the direction and teaching use of each relation, and use the existing administrator review workflow. Human review counts remain zero at this checkpoint. The separate 5,543 visual-candidate inventory and five unresolved sampled table grids retain their previous review status; this prose curation supplies no visual-content approval.
