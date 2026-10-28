# Native table candidates, opt-in visual extractor v3

`visual_regions_v3` adds `native_ruled_tables_v1` to the retained visual v2 extractor. The default build and startup use v2. Existing catalogs, region IDs, source units, vectors and saved citations retain their original identities. New v3 IDs include the previous region ID and extractor revision as lineage.

Build a separate candidate catalog from the original official PDFs:

```powershell
python -m scripts.verify.build_visual_region_catalog --extractor-revision pymupdf_visual_regions_v3 --out evidence/week09-continuation/20261001/private/visual-full-v3-native-tables-v1
```

The destination must be new; the builder refuses to overwrite its catalog or manifest. Omitting `--extractor-revision` continues to select `pymupdf_visual_regions_v2`. `--max-pages` creates a development sample, which the existing full-source verification/import contract rejects as incomplete.

The native recovery groups aligned horizontal drawing rules and sustained interior vertical rules. Rule endpoints supply the missing external borders. Native text must occur inside the grid, each scoped word must belong to exactly one cell, and partial vertical coverage, ambiguous nearby grids and inconsistent row/column shapes remain unresolved. Configuration limits and source code are frozen before successor mechanical comparisons.

Each recovered cell retains the library's raw table string, native textbox text, character coordinates, origins, font sizes and source order. The position-ordered string is a separate candidate; it leaves the raw string intact. Superscript/subscript baselines remain available for notation review. This local extraction supplies no independent semantic labels.

Adjacent-page continuation candidates require the same original source hash, consecutive physical pages, identical printed table label, matching normalized first-row header candidates, compatible page sizes, matching table width and normalized column boundaries, and bottom-to-top page placement. Each fragment retains its own header and physical-page locator. A join remains a source-review candidate.

The existing `prepare_visual_review` and verify-only `import_visual_regions` commands can audit complete source-hash-bound catalogs. Their reviewer fields remain empty until reviewers fill them. The database importer protects its existing immutable per-source catalog and refuses a different catalog where v2 is already registered. V3 coexistence needs an explicitly versioned import policy before any database import; this iteration supplies no database writes, approval or publication. A later approved structure review and a separately validated corpus release are required for answer-evidence eligibility.

The five previously examined failures are development observations, including the two that originally carried a reserved split. The remaining original reserved table rows supply a legacy mechanical regression set. Page separation alone supplies no independently labeled semantic holdout, and the prior formal v2 result remains 35/40 table grids.

Implementation reference: [PyMuPDF table detection](https://pymupdf.readthedocs.io/en/latest/page.html#Page.find_tables) documents explicit vertical/horizontal boundaries and source drawing paths. Execution is pinned to the installed PyMuPDF version recorded with each catalog.
