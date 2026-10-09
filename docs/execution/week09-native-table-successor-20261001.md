# Week 09 native table extraction successor — 1 October 2026

The opt-in `pymupdf_visual_regions_v3` extractor generated a new private, unapproved catalog from all four stored official OpenStax PDFs. Of 339 table candidates, 333 now have a rectangular cell candidate, compared with 285 under the preserved v2 extractor. All 6 remaining failures are retained. This result measures candidate geometry and traceability; independent cell, symbol, reading-order and teaching-quality review remains pending.

## Implementation and version boundary

`pipelines/native_tables_v1.py` recovers open-border table candidates from native horizontal rules and sustained interior vertical rules. It derives exterior boundaries from source drawing endpoints, checks native word-to-cell assignment, and keeps the original extracted strings, character baselines, sizes, bounding boxes and order. A separate position-ordered string is a recovery candidate. Neither a transcription dictionary nor a book/page lookup participates in extraction.

`pipelines/visual_regions_v3.py` adds versioned region identities with v2 lineage. Previously extracted cells remain in `previous_table_structure` when a larger native grid adds a missing header. Adjacent-page assembly requires the same source hash, consecutive physical pages, table label, header, column boundaries and page dimensions, together with end/start page placement. Joined records retain the individual physical-page cells.

The existing builder exposes `--extractor-revision pymupdf_visual_regions_v3`; its default remains `pymupdf_visual_regions_v2`. The startup flow, published corpus and original v2 catalogs continue to use their existing identities. A verify-only import accepts the new 5,543-candidate catalog without writing to a database. The existing per-source database catalog guard prevents replacing an already registered v2 catalog. A separately reviewed coexistence/import policy is still required before publishing v3 candidates.

The five owned implementation, builder, test and module README files were frozen before the remaining legacy reserved cases and other failed candidates were processed. Freeze SHA-256: `19feb27901a2386f8b4d51a1b159e2067cc6600a498c1722e97cf3ef65382c54`. Source hashes and exact parameters appear in the [mechanical receipt](../../evidence/week09-continuation/20261001/visual-native-tables-v3-mechanical-20261001.json). No algorithm changes followed the frozen evaluation.

PyMuPDF 1.28.2 performed the local extraction. Its documented explicit table boundaries and native character layout provide the implementation primitives. See [PyMuPDF table extraction](https://pymupdf.readthedocs.io/en/latest/page.html#Page.find_tables) and [native text extraction](https://pymupdf.readthedocs.io/en/latest/recipes-text.html).

## Actual full-source execution

The full scan ran from `2026-09-30T23:18:37.994963+00:00` to `2026-09-30T23:23:29.820354+00:00`, taking approximately 291.83 seconds. All 4,638 physical pages were processed, with zero failed pages. The same 5,543 region lineages and 339 table candidates remain accounted for.

| Official book | Physical pages | Region candidates | Table candidates | v2 rectangular candidates | v3 rectangular candidates | Remaining failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Anatomy and Physiology 2e | 1,347 | 1,101 | 153 | 126 | 148 | 5 |
| Biology 2e | 1,475 | 1,425 | 78 | 67 | 78 | 0 |
| Chemistry 2e | 1,203 | 2,442 | 93 | 80 | 92 | 1 |
| Concepts of Biology | 613 | 575 | 15 | 12 | 15 | 0 |
| Total | 4,638 | 5,543 | 339 | 285 | 333 | 6 |

All four original PDF hashes were checked before and after processing. The original v2 extractor SHA remains `4a6b071e2d3e68503514dc1bd92c57a76ee7f2094918d617d4b354480f98d4ca`. The original formal v2 result remains 35 of 40 table grids, with the same five unresolved cases. No provider calls, database connections, database writes, chunk changes, vector changes or corpus publications occurred in this extraction work. The baseline published corpus contains 10,594 vectors; no fresh database measurement is claimed here.

## Frozen populations and checks

The five targeted examples became exposed development material, including two cases originally reserved in the earlier study. All five received native structure candidates. Biology physical pages 592–593 and Anatomy physical pages 908–909 received separately traceable adjacent-page continuation candidates.

The remaining 21 original reserved table cases were processed after the freeze: all 21 reached a terminal result and retained a rectangular candidate. The other 49 originally unresolved candidates were also all processed: 43 received a structure candidate and 6 remained unresolved. These populations provide mechanical regression evidence. They have no independent semantic labels, and their results do not establish a semantic holdout score.

The focused suite passed 22 tests, covering the new detector, preserved v2 behavior, formal mechanical checks, visual source access, review and import guards. Ruff checks and formatting checks passed for the four Python files. The parent integrated gate provides the broader software result separately.

## Six retained failures and original-page observations

Each failure was rendered from the hash-verified original PDF using independent native Poppler at 100 DPI and actually inspected at original image detail. The observations below were made by the development AI contributor. They are source diagnostics, with zero independent human scores and zero content approvals. The frozen algorithm and the failure denominator remain unchanged.

| Failure | Original physical page | Original label | Source observation and next investigation |
| --- | ---: | --- | --- |
| F01, Anatomy and Physiology 2e | 858 | Table 20.2 | A real table continuation is visible above a colored disorders panel. The table's final horizontal rule is at 185.51 pt; the panel's aligned top rule at 208.03 pt triggers the frozen partial-interior-line rejection. Distinguishing separate aligned panels from additional table rows needs a future version and fresh evaluation. |
| F02, Anatomy and Physiology 2e | 905 | Table 20.11 | The retained native caption is a prose link to the table; this page shows a veins diagram and prose. Caption/reference disambiguation requires source review. |
| F03, Anatomy and Physiology 2e | 1062 | Table 23.6 | The retained native caption is a prose link to the table; this page shows stomach histology and explanatory text. Caption/reference disambiguation requires source review. |
| F04, Anatomy and Physiology 2e | 1169 | Table 25.3 | A real unruled single-column symptoms list is visible. The frozen native ruled-grid detector requires at least two columns and cannot reconstruct this layout. Single-column/unruled handling needs a separately tested extension. |
| F05, Anatomy and Physiology 2e | 1309 | Table 28.4 | The retained native caption is a prose link to the table; this page shows inheritance information and a diagram. Caption/reference disambiguation requires source review. |
| F06, Chemistry 2e | 1058 | Table 21.4 | The retained native caption is a prose link to the table; this page shows radiation units, a formula and figures. Caption/reference disambiguation requires source review. |

The local failure packet preserves each exact native quote and bounding box, previous and new region IDs, original hash and official URL, original-page PNG hash, and a blank review row. Its private location is `E:/5703/week09-private-db/visual-general-recovery-20261001/retained-failures/`. The source diagnoses do not remove any of the six candidates from the measured failure population.

## Review and publication state

The verify-only catalog check accepted all 5,543 candidates. Review preparation checked all four catalogs for identity and on-page geometry and produced 120 blank rows using deterministic spread across distinct physical pages. Clipped native image counts remain visible in the audit. The six retained failures have a separate blank review sheet. No independent human rating or semantic approval has been entered.

The new catalog is retained privately at `evidence/week09-continuation/20261001/private/visual-full-v3-native-tables-v1/`; the 120-row sheet is at `evidence/week09-continuation/20261001/private/visual-review-v3-native-tables-v1/`. Public receipts expose source hashes, counts, terminal statuses and provenance. Original page observations and raw glyph/cell material stay in local review records.

Next work is independent cell/header/notation and reading-order review, a versioned database coexistence/import decision, and new-version evaluation of the aligned-panel, caption-reference and unruled single-column layouts. Approved content, retrieval use and answer-quality effects each require their own evidence. The 5,543 visual candidates remain pending full content review.

Evidence: [mechanical frozen execution](../../evidence/week09-continuation/20261001/visual-native-tables-v3-mechanical-20261001.json), [source inspection and blank review preparation](../../evidence/week09-continuation/20261001/visual-native-tables-v3-source-review-preparation-20261001.json), and [module operation instructions](../../pipelines/README_visual_tables_v3.md).
