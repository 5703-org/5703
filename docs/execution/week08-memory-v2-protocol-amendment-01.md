# Protocol amendment 01: precise repair and context contrasts

Registered on 21 September 2026 before new formal outputs. The original registration remains preserved at SHA-256 `8f4d630f13284e1c6f6898427ec72234645ef82ccb4ac51a726b8ba4ccb678e2`.

The implementation review distinguishes generation context from the visible citation highlight. The existing whole-passage packer already performs complementary selection. The new context selector first chooses complete contiguous blocks, neighbouring causal/qualification content and facet anchors across the same frozen candidate pool, then uses the unchanged 3,000-token evidence cap. Exact original source offsets remain attributable. C1 uses `generation_context_policy=legacy_context_v1`; B2 uses `complementary_context_v2`. This is a context-selection comparison, not an increase in the evidence budget or a replacement corpus.

C2 precisely compares the **cause-specific answer repair plan** with the legacy generic answer-repair instruction on the same new v2 schema, semantic-support, derivation and citation gates. Use `repair_policy=generic_answer_repair_v1` for C2 and `cause_specific_repair_v2` for B2. Checker-contract inconsistency handling remains identical in these two arms and cannot grant publication. This contrast does not isolate the entire claim gate. The original description of C2 as legacy claim/marker repair is narrowed accordingly. The primary B2 versus B1 comparison remains a combined pipeline comparison.

Sample sizes, primary contrasts, memory writing/reading isolation, task grouping, maximum calls/time, stopping rules and human-review requirements remain as registered. No formal results were available when this amendment was written.
