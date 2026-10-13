# Saved59 source-gap taxonomy

The five definite selected-proof gaps have relevant candidate witness components already present in each original claim's allowed source binding. **No knowledge-not-retrieved case is established here.** All five current selected combinations are incomplete, and all five omit relevant allowed candidates. ATP predicate ownership is a sixth, conditional diagnostic case rather than a sixth unconditional factual gap.

This is a seen development-case diagnosis, not Gold, held-out evaluation, a new paid-model observation or an automatic proof repair. The frozen59 response, labels, review and measurements remain unchanged. [Structured evidence](saved59-gap-taxonomy.json) records the six cases, original binding scopes, legal candidate groups and exact source locations.

## Minimal available data interface

| Saved interface | Useful fields | Provenance boundary |
| --- | --- | --- |
| `SOURCE_FRAGMENTS` | fragment_id, evidence_id, exact_text, block_kind, complete_block | Original serialized fragments; no complete source parent |
| `BINDING_BANK` | binding_id, evidence_id, allowed_fragment_ids | Legal same-claim candidate selection |
| `ACTUAL_CITATION_BINDINGS` | claim_id, binding_ids | Which source banks actually belong to the claim |
| `SOURCE_SYNTACTIC_UNITS` | literal unit text, start/end/hash, actual scope, candidate anchor hits | Unit offsets belong to the answer; source_hits locate tokens inside a fragment |
| Existing `source_span_cards` | original serialized row/column, fragment UTF8 SHA, proof_quote, quote code-point/byte offsets | Exact quote location inside each frozen fragment, explicitly **not original PDF/HTML offsets** |

The sole additional metadata file read was Main's public `docs/execution/evidence/20261010-offline-provenance-performance51/remaining-unit-evidence.json`. None of its listed `source_pins` paths were followed. Fifteen cards were checked against59 identity, exact text, UTF8 SHA and character slices. A secondary read-only review also matched seven relevant cards' character and UTF8-byte slices.

**Unavailable:** full original source parent, parent ID, original document/page/global span, and child start/end relative to a complete original parent. Missing parent metadata remains unknown. The retained `complete_block=true` flag is not a guarantee of grammatical or scientific completeness.

## Four diagnostic categories

- **Knowledge not retrieved:** the required knowledge is unavailable in the allowed retrieved pool. This is not established for these six cases; related witness components exist in the original allowed records. It is not a claim of general retrieval sufficiency.
- **Candidate present but not selected:** a relevant original candidate is available under that claim's existing binding, but omitted from that unit's selected IDs.
- **Syntactic predicate ownership:** a lossless unit boundary cuts a coordinated subject from a shared predicate, requiring an explicit obligation policy.
- **Selected combination insufficient:** the actual selected texts do not establish every asserted part. Merely identifying legal candidate additions does not change the old selection or establish a new PASS.

These categories overlap; their counts must not be summed. There are five definite candidate/combination gaps, one ownership-sensitive case and zero confirmed knowledge-not-retrieved cases.

## Exact five gaps plus ATP mapping

| Original claim/unit | Missing assertion | Diagnosis | Original-identity local candidate group |
| --- | --- | --- | --- |
| C1-U01 | RuBP carbon/phosphate attributes | Candidate present/unselected; current combination insufficient | F056+F064+F055 or F056+F064+F065 |
| C2-U01 | Named 3-PGA product identity | Candidate present/unselected; current combination insufficient | F056+F058 |
| C9-U02 | Named 3-PGA product identity | Candidate present/unselected; current combination insufficient | F056+F058 |
| C9-U04 | Reduction classification | Candidate present/unselected; current combination insufficient | F058+F059 |
| C10-U02 | Carbohydrate purpose | Candidate present/unselected; current combination insufficient | F011+F019+F020 |
| C9-U03 | Shared reduce predicate versus ATP energy role | Ownership ambiguity; conditional insufficiency | F058+F059 |

The groups are **available source candidates for a fresh local selection assessment**, not hardcoded Gold choices or automatic sufficiency verdicts.

- **C1 U01:** F055 directly states five carbon atoms and a phosphate group on each end. F065 states five carbons flanked by two phosphates and is an alternative attribute candidate under this claim's ev_008 binding. Retain reaction/stage evidence; never infer explicit molecular properties solely from its name.
- **C2 U01 / C9 U02:** F056 supplies six-carbon to two three-carbon conversion; F058 supplies the named three-carbon compound 3-PGA. Offer distinct original records as complementary evidence. F058 alone does not reproduce the whole conversion/quantity assertion, and a shared name match is not a semantic PASS. In C9, F058 is already a claim-level/other-unit selection; U02 still needs its own explicit selection and assessment.
- **C9 U04:** F058 supplies joint energy-driven conversion, and F059 names this reaction type as reduction. F060 alone is a definition, not a classification of the specific conversion. Do not require a separate electron count or claim ATP independently donates electrons.
- **C10 U02:** F011 already establishes three turns to export one G3P. The purpose witness requires the F019 subject/predicate and F020 carbohydrate object as separate exact records. F001 is direct carbohydrate proof elsewhere but belongs to ev_001 outside this claim's original binding.
- **C9 U03:** the literal slice ` which ATP` is energy-role complete with F058 under the compatible reading, but inherits a reduction-classification obligation under strict shared-predicate ownership. F058/F059 may be offered if that ownership is explicit. Selection cannot silently turn the slice into an independent assertion that ATP is an electron donor.

## F019/F020 layout and parent boundary

F019's full retained text includes `5 • Key Terms 131`. The existing metadata locates its subject/predicate proof quote at fragment code-point and byte range **[0,69)**. F020's whole `part of a carbohydrate molecule.` quote occupies **[0,32)**. Both have original evidence identity ev_003 and are legal under B003 (F016-F022).

Their serialized rows are adjacent, and the texts form a plausible complementary purpose witness. This does **not** establish original-document adjacency, recover a complete parent, or supply original PDF/HTML offsets. The earlier59 review's word “continuation” describes this lexical compatibility, not certified parent provenance.

A local source-selection helper can expose the separate, located original quotes while preserving the full records and F019's layout pollution. It must not create a cleaned joined serialized quotation, derive a parent from F numbers, substitute source_hits/answer offsets for source-global spans, or retrospectively credit unselected F020 to59.

| Fragment | Evidence | Serialized row (zero-based) | exact_text column | Quote code points | Quote UTF8 bytes |
| --- | --- | ---: | ---: | --- | --- |
| F011 | ev_002 | 10 | 3 | [36,122) | [36,126) |
| F019 | ev_003 | 18 | 3 | [0,69) | [0,69) |
| F020 | ev_003 | 19 | 3 | [0,32) | [0,32) |
| F055 | ev_007 | 54 | 3 | [0,64) | [0,64) |
| F056 | ev_007 | 55 | 3 | [0,147) | [0,147) |
| F058 | ev_007 | 57 | 3 | [0,129) | [0,129) |
| F059 | ev_007 | 58 | 3 | [0,96) | [0,96) |
| F064 | ev_008 | 63 | 3 | [0,284) | [0,284) |
| F065 | ev_008 | 64 | 3 | [0,57) | [0,57) |

All offsets in this table are **within the named fragment**. They are not complete-parent spans or original PDF/HTML locations.

## General repair interface boundaries

Use the original evidence/fragment records, same-claim binding limits and bounded multi-fragment candidates. Keep every exact source identity and text. A legal source combination is a candidate for a source assessment, not an entailment certificate.

Runtime correction must be triggered by an explicit negative/partial result or an actual contract failure. The current59 raw `supported` labels do not themselves trigger live supplementation; this case serves as an already seen offline development fixture. The implementation must not encode these biology claim IDs, F numbers or candidate groups as universal rules.

Parent restoration requires actual source metadata and preserved child spans. Without that data, offer separate original records and keep provenance unknown. Multiple-choice option occurrences such as F041/F067 have no saved answer key and cannot be promoted to scientific proof.

## Fixed inputs

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| independent59-review.md | 9607 | `1b569d0a83d51904ca1847f12b75643df2d46d71badae67819055e844fee9f9c` |
| independent59-review.json | 44235 | `e70843d0bc08b5a8e50d6e25061391ad560b27fe81a4639592384eec7ffc80b9` |
| wire59-PREPARED-UNVERIFIED.json | 88704 | `c14a0748a60e981f03d5f2d5731ba87048909514ac45d4e3d28828e656913b40` |
| remaining-unit-evidence.json | 75290 | `af4ead0d425e53420ea4569fa1bc1a2965ab3fe674aa602c7f52c84904e1a4b4` |

Only the new English taxonomy Markdown and JSON were written in `W/5703-proof60-diagnosis`. No frozen59 input was modified; no source_pins path, Git, authentication, database, network, old controller or Main write was used. No last-slot request was scheduled or consumed.
