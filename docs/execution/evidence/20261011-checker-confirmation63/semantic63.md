# Independent selected-fragment review of confirmation63

Status: **COMPLETE_EXPOSED_CONFIRM63_SELECTED_FRAGMENT_REVIEW**. All **19 original literal syntactic units** across 10 claims were independently re-read against their actual selected original fragments. This is an AI reviewer assessment of exposed development data, **not human Gold or held-out validation**.

The complete response is eligible for semantic review: provider finish reason is `stop`, provider error is null, the raw JSON is complete, and data-only checks found no schema, original claim/unit-set, or own citation/selected-fragment scope errors. Root separately reports the production structure gate passed. These gates establish eligible structure and binding, not source entailment.

The raw checker labels remain **10 supported claims and 19 supported units**, with true relation/condition declarations. They are preserved separately from this review. `source_entailment_certified=false` and `all_selected_source_support_complete=false`.

| Unit interpretation | Complete | Partial | Bridge unknown | Total |
| --- | ---: | ---: | ---: | ---: |
| Compatible ATP energy role | 15 | 1 | 3 | 19 |
| Strict shared reduction-predicate ownership | 14 | 2 | 3 | 19 |

“Complete” means the selected records supply the unit's stated predicates and conditions under the recorded reading. “Partial” means a concrete asserted predicate remains unsupported by the selected records. “Bridge unknown” means relevant pieces are present but their necessary product identity or OCR continuation is unconfirmed. Unknown bridges are not counted as complete. These are syntactic-unit counts, not independent facts or a calibrated accuracy score; C2/U01 and C9/U02 repeat the same product-identity issue.

At claim level, both readings give **7 complete, 1 partial and 2 bridge-unknown** claims. C9 is classified partial because U04 lacks the concrete reduction predicate, while its U02 also contains an unresolved bridge.

## Actual remaining support gaps

- **C2/U01 and C9/U02, selected F056 + F058:** F056 proves immediate conversion of the six-carbon compound into two three-carbon compounds. F058 names a later substrate 3-PGA. The selected combination does not explicitly identify both earlier products as that named substrate. The same-product bridge remains unknown; it is not supplied merely by the shared evidence identity, carbon count, or neighboring fragment numbering.
- **C9/U04, selected F058:** energy-mediated conversion to G3P is explicit, but the selected sentence does not classify that conversion as reduction. Other units' selections of F059 or F060 cannot be credited here.
- **C10/U02, selected F011 + F019 + F020:** F011 proves the three-turn/export-one condition. F020 is now genuinely selected and supplies the carbohydrate-object phrase, an improvement in witness-piece inventory. The original F019 still ends with the OCR footer `5 • Key Terms 131`; F020 is a separate record. A trustworthy subject/object continuation across that layout boundary is unconfirmed. The review neither deletes the footer nor invents a joined parent quotation.
- **Strict ATP condition, C9/U03, selected F058:** the literal slice ` which ATP` is not a standalone proposition. F058 supplies ATP's energy role under the compatible reading. Assigning the later shared `reduce to G3P` predicate to that slice adds the same missing concrete reaction classification under the strict reading. Neither reading invents an assertion that ATP independently donates electrons.

C1/U01 is now complete using its own F054/F056/F064/F065: Calvin-cycle initiation context, RuBisCO reactants/reaction, fixation context, and five carbons flanked by phosphates are all selected. The proof does not require a particular predesignated “Gold” fragment such as F055.

## All 19 actual units

C1–C10 follow the original claim order. The companion JSON preserves each exact claim ID and literal unit text, actual selected IDs, own supporting evidence IDs, and full judgments. Its deduplicated quote table contains only the **19 unique fragments actually selected by these units**, retaining exact original text.

| Original unit | Actual selected fragments | Compatible | Strict ATP | Independent reason |
| --- | --- | --- | --- | --- |
| C1/U01 | F054, F056, F064, F065 | complete | complete | F054 explicitly names Calvin-cycle initiation and reactants; F056 supplies RuBisCO's CO2/RuBP reaction; F064 supplies Fixation stage context; F065 explicitly supplies five carbons flanked by two phosphates. No claim-only selections are needed. |
| C2/U01 | F056, F058 | bridge_unknown | bridge_unknown | F056 proves the immediate six-carbon-to-two-three-carbon transition. F058 names the later substrate 3-PGA. Identifying that substrate with the two earlier products remains an unconfirmed same-product co-reference; matching names/counts or evidence identity alone does not settle it. |
| C3/U01 | F058 | complete | complete | F058 directly supplies ATP stored energy. This literal slice does not assert ATP independently donates electrons. |
| C3/U02 | F018, F058, F059, F060 | complete | complete | Own F058 names 3-PGA-to-G3P conversion; F059's reaction-type classification explicitly supplies reduction and electron gain. F018 supplies joint energy context and F060 the reduction definition. The selected classification is credited, not a sibling's selection. |
| C4/U01 | F057 | complete | complete | F057 explicitly gives inorganic CO2 becoming organic molecules and names carbon fixation. |
| C5/U01 | F012 | complete | complete | F012 explicitly states each turn makes two G3Ps. |
| C5/U02 | F011, F012 | complete | complete | F011 explicitly states three Calvin-cycle turns fix enough net carbon to export one G3P; F012 gives each-turn production. No separate unasserted carbon premise is required. |
| C5/U03 | F013 | complete | complete | F013 explicitly gives remaining G3P regeneration of RuBP and preparation for further CO2 fixation. |
| C6/U01 | F001 | complete | complete | F001 explicitly ties a departing G3P to carbohydrate formation, commonly glucose. |
| C6/U02 | F002 | complete | complete | F002 explicitly ties a six-carbon carbohydrate molecule to six Calvin-cycle turns. The literal unit adds no separate glucose-specific quantity assertion. |
| C7/U01 | F003, F021 | complete | complete | F003 and F021 explicitly give remaining G3P regeneration/back-formation into RuBP. |
| C7/U02 | F021 | complete | complete | F021 contains the RuBP antecedent and readiness to react with more CO2. |
| C8/U01 | F004 | complete | complete | F004 directly states ATP is used in RuBP regeneration. |
| C9/U01 | F056 | complete | complete | F056 directly supplies RuBisCO's CO2/RuBP reaction. |
| C9/U02 | F056, F058 | bridge_unknown | bridge_unknown | F056 gives two three-carbon products and F058 the named 3-PGA substrate. The specific product identity bridge remains unconfirmed; F058's use by other units is not credited. |
| C9/U03 | F058 | complete | partial | Literal ' which ATP' is not an autonomous proposition. F058 proves ATP energy participation under the compatible reading; strict ownership of the later shared 'reduce to G3P' predicate also requires concrete reduction classification, absent here. Neither reading asserts ATP is an independent electron donor. |
| C9/U04 | F058 | partial | partial | F058 supports joint energy conversion of 3-PGA to G3P but does not itself classify that conversion as reduction. This unit still selects only F058; other claims' F059/F060 cannot be borrowed. |
| C10/U01 | F013 | complete | complete | F013's one exported versus five retained G3Ps supports the majority meaning of Most and RuBP regeneration. |
| C10/U02 | F011, F019, F020 | bridge_unknown | bridge_unknown | F011 proves the three-turn/export-one condition. F019 supplies G3P leaving with an unfinished destination and OCR footer; newly selected F020 supplies a carbohydrate-object phrase. Their purpose witness now has both pieces, but the cross-layout subject/object continuation remains unconfirmed; no cleaned joined quote or parent is invented. |

Only each unit's own actual selected fragments and legally scoped supporting citations are credited. Claim-only selections, sibling-unit proof, other-claim evidence and unselected pool text do not fill a gap. IDs, offsets, source metadata flags and token overlap do not prove semantic support.

## Comparison with saved59

All 19 actual63 selections were reviewed again; earlier normal labels were not inherited. The prior compatible count was **14 complete / 5 partial**; strict was **13 complete / 6 partial**. The current three-way counts are **15 / 1 / 3** and **14 / 2 / 3** respectively. If all unknown bridges are conservatively grouped as not complete, the current counts are 15 complete / 4 not complete and 14 complete / 5 not complete.

| Saved59 partial unit | Saved59 selected fragments | Actual63 selected fragments | Current independent category |
| --- | --- | --- | --- |
| C1/U01 | F056, F064 | F054, F056, F064, F065 | complete |
| C2/U01 | F056 | F056, F058 | bridge_unknown |
| C9/U02 | F056 | F056, F058 | bridge_unknown |
| C9/U04 | F058 | F058 | partial |
| C10/U02 | F011, F019 | F011, F019, F020 | bridge_unknown |

Six units changed selected-ID sets, including C3/U02's added F060 and C5/U02's added F012. Four of the five previously partial units have additional selected witness pieces; one is now complete under this review. The three bridge-unknown categories record remaining uncertainty, not proven success. Same-input repeated selection changes do not establish causal improvement, general accuracy, or a new RAG-quality comparison.

## Observation and authorization boundary

Root's retained observation records one confirmed POST, one transport attempt, no automatic retries, finish reason `stop`, known cost **$0.0323163**, and **$0 UNKNOWN hold**. The aggregate is **8 slots / $0.19758306 known cost / 0 new UNKNOWN**. There are **0 remaining request slots**; monetary headroom of $0.16241694 does not grant another request.

The actual63 adapter-return observation is **24.0919026 s**, compared with saved59 **17.4793151 s**. Each is a single adapter observation. Neither is browser “send to full answer render,” p95, or evidence of a causal latency change.

This reviewer made **zero external/model calls** and performed no authentication, database access, Main writes, or old-controller/helper import or execution. A second read-only AI reviewer rechecked all 19 current selections and concurred with both count sets. That concurrence is not human Gold.

## Fixed inputs

- `C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-confirm63-candidate\actual63\result63.json`
  - 15549 bytes; SHA-256 `f8e9af7edbc2e66f09cb33222a8ceaf723e7b6a612180d77d46d7c6f0b5e5774`.
- `E:\5703\learning-assistant\docs\execution\evidence\20261011-checker-recovery58-59\capacity59\wire59-PREPARED-UNVERIFIED.json`
  - 88704 bytes; SHA-256 `c14a0748a60e981f03d5f2d5731ba87048909514ac45d4e3d28828e656913b40`.
- `E:\5703\learning-assistant\docs\execution\evidence\20261011-checker-recovery58-59\capacity59\actual59\result59.json`
  - 63952 bytes; SHA-256 `230de5d6ff787f79cddd7161ebbcddbdc40c173af442de1e3081b3bf558e082b`.
- `E:\5703\learning-assistant\docs\execution\evidence\20261011-checker-recovery58-59\capacity59\independent59-review.json`
  - 44235 bytes; SHA-256 `e70843d0bc08b5a8e50d6e25061391ad560b27fe81a4639592384eec7ffc80b9`.

The request wire's exact-byte identity is reported by root as `c14a0748a60e981f03d5f2d5731ba87048909514ac45d4e3d28828e656913b40`, matching the pinned public original59 wire used here for the original 71 source records and 19 units. No frozen input or judgment was modified.

No new RAG experiment, native-page acceptance, held-out accuracy, p95, publication approval, or course-wide completion follows from this review.

