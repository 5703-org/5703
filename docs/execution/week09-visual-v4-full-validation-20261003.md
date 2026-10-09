# Week 9 full official Visual V4 validation — 3 October 2026

The integrated opt-in V4 parser processed every page of the four hash-verified official OpenStax originals. It scanned 4,638 pages and retained all 5,543 V2 and V3 region lineages with zero failed pages. The actual new catalog contains 339 table records: 325 body candidates and fourteen linked inline references, with no unresolved table body or reference target. These are mechanical extraction results. Human content ratings, semantic approvals and answer-evidence eligibility remain zero.

| Book | Pages | Region candidates | Table bodies | Linked references |
| --- | ---: | ---: | ---: | ---: |
| Anatomy and Physiology 2e | 1,347 | 1,101 | 145 | 8 |
| Biology 2e | 1,475 | 1,425 | 75 | 3 |
| Chemistry 2e | 1,203 | 2,442 | 90 | 3 |
| Concepts of Biology | 613 | 575 | 15 | 0 |

The original V3 catalog retains its 333 rectangular records and six unresolved records. V4 recovered two actual body candidates, classified ten prior rectangles as linked prose references, and linked the other four former failures to their distinct target pages. Native word/glyph positions remain available for notation and merged-cell inspection. A rectangular shape alone does not establish complete headings, units, reading order or formula meaning.

The source reference retains its own page, text and geometry. The target locator identifies a distinct same-source table region; ten of the fourteen targets share the reference page. Native PDF links provide page-and-label association. Their destination points are checked against the target page; no containment or semantic-association claim is made. V4 requires confined, hash-pinned V3 sidecars with one-to-one V2/V3 lineage checks. Import also verifies declared dimensions against each original PDF.

The new immutable review bundle is at artifacts/visual-catalog-staging/native_tables_v4_408b66676c84e6e9. Its source manifest hash is 246422ef03bbb97901c4378fce703e0f67187dd4291ffd058ea6654bda9374d5. The full extraction manifest hash is 408b66676c84e6e9df134b4fd3f1d942b8792baeedb955ce2e5c28b1082d46bb. The companion scalar receipt records the four source/catalog hashes, exact producer freeze and current validation scope. Original acquisition manifests retain official URLs, dates and licence information.

Dedicated current checks passed 27 Python source/consumer cases, 60 disposable PostgreSQL/API cases and 17 frontend cases. The database cases include V3/V4 coexistence, repeated imports, forged-parent rejection and comparison with actual PDF dimensions. Their authored fixtures are software evidence. The full official bundle separately passed load_bundle on all 5,543 entries. The full official bundle was then imported into a new isolated PostgreSQL database, cs30_week09_visual_v4_20261003_04 on port 16549: four staged catalog versions and 5,543 candidates were committed. Repeating the import added zero candidates. Hash snapshots retained all original rows and column definitions across 65 tables, and the donor database stayed unchanged. A consistent local pg_dump/pg_restore created the clone while preserving existing connections. The first two attempts stopped before database creation after an authentication failure and an active-connection guard respectively; both failure records are retained. The current unified software gate is running; earlier 864-source results remain dated evidence.

The default V2 builder and existing catalogs, vectors, citations, source records, review history and keys are preserved. V4 remains an explicit review candidate. Source-content assessment, a human-approved publication and downstream visual answer quality still require their own acceptance evidence.
