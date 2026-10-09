# Week 8 Module Report

Chengzhou Liu | Retrieval and source selection | 2026-09-20

## Domain outcome

The retrieval domain gives the citation and teaching comparisons the same initial real textbook candidates. It adds exact-fragment selection alongside conventional passage display while preserving the existing learned embeddings, PostgreSQL vectors and frozen evaluation baselines.

Original accountable task IDs: RET-01, RET-02, RET-03, RET-04, RET-05, RET-06, RET-07, RET-08, RET-09, RET-10, RET-11, CHAT-04.

## Implemented changes

The three source strategies are conventional full-passage citation, post-generation fragment association and bounded local preselection followed by generation. Preselection uses the existing local evidence rather than an extra planning-model call. Its selected ranges remain linked to the original evidence and source units.

Candidate boundaries and atomic-block eligibility constrain selection before a fragment can support an answer. Post-generation association uses actual claim links and the semantic checker. Local lexical selection is a reference method; it is not presented as a reproduction of a published attribution system or as proof of entailment.

Interactive retrieval retains its configured learned E5 embeddings and local reranking, finite candidate policy and 3,000-token evidence allowance. The comparison freezes real initial candidates and records actual source text and hashes. Formal E0 and E1 retain no-retrieval and basic dense behavior instead of inheriting the interactive policy.

## Interfaces and dependencies

Hongle provides exact source units and conservative boundaries. Sijin consumes selected passages and returns claim support links. Chong freezes matched study inputs and computes task-paired results. Zeping keeps source visibility and request configuration consistent, while Baiqing displays the actual approved passages.

Implementation and dependency paths: retrieval/source_spans.py; retrieval/embedding.py; retrieval/chat.py; generation/evidence_budget.py; evaluation/enhancement/sources.py.

## Current verification

Whole passage: 28/60 published and 27/60 complete supported answers under the corrected automatic rubric. Post-generation spans: 22/60 published and 22/60 complete supported answers under the corrected automatic rubric. Preselected spans: 29/60 published and 27/60 complete supported answers under the corrected automatic rubric.

Published source previews averaged 4,253.6, 1,223.4 and 799.6 characters for whole passages, post-generation spans and preselected spans. These lengths describe each method's successful outputs; the methods published different subsets. Exact slicing and source identity passed for the published projections.

The three strategies begin from matched real textbook candidates. Preselection uses bounded local evidence selection, so a shorter submitted context has a clear operational explanation. The measured publication rates and corrected direct-answer judgments show why context reduction and answer usefulness need separate denominators. Retrieval success alone cannot explain a downstream rejection; the retained stage and repair records identify where the final answer became unavailable.

The fresh CPU installation exercises the actual local retrieval stack against the preserved 384-dimensional corpus. This supplies deployment evidence alongside the research comparison. Existing R0–R3 retrieval and fixed-versus-structure chunking studies remain prior records. The next retrieval experiment should examine the current rejected and incomplete cases before allocating a new held-out set, especially where a short span loses a condition or exposes the answer that a hint should leave to the learner.

| Matched record | Accounted | Planned |
| --- | --- | --- |
| Direct answers and attribution | 180 | 180 |

Independent human ratings recorded for this checkpoint: 0. Prepared review materials are ready for the group's two reviewers.

## Failures and limits

Shorter selected passages may lose a qualification or reveal too much of a worked answer. A local ranking score is not a support judgment, and a changed ranking is not demonstrated relevance improvement. Development failures and unsupported selections must remain visible. Earlier R0–R3 and fixed-chunk comparisons remain prior evidence rather than work to rebuild from zero.

Week 9 work will compare independent support and completeness judgments on the frozen strategy outputs, including unavailable answers. A subsequent selection rule needs a new source-bound development record and the same explicit accounting of source length, model calls and failures.

## Module operation

- Inspect a frozen comparison input and confirm all three citation methods receive the same initial source candidates.

- Compare the full-passage, post-generation and preselected outputs for actual text length, exact positions and missing or coarse links.

- Check the recorded model, device and release identity before reproducing retrieval; use existing verified local assets and retain any failure.

## Week 9 actions

- Use independent source-support and completeness judgments to compare the three frozen methods, reporting paired differences and all failure categories.

- Investigate whether shorter fragments remove conditions or expose worked solutions, then validate any revised selection rule on development material before a new held-out run.

- Extend relevance judgments only with version-compatible source identities; retain existing R0–R3 and chunking comparison artifacts.

## Accountability and evidence

These are accountable project domains from the original team allocation. The implementation and verification cited in the reports were performed through the shared project workflow. Domain ownership does not establish a personal commit, individual execution, independent review or personal authorship. Actual execution record: Codex performed the shared implementation, scripted execution and document preparation. Named members remain the accountable module owners. Independent reviewers have supplied 0 ratings.

Corrected direct-answer citation analysis. Same 180 generated outcomes with corrected direct-answer judging; the original judge is retained.

evidence/week08-enhancement/20260920/formal-citations-judge-v2-analysis.json

SHA256 6aec13d0175ce4f7be47d2f78bf125e405fb82bda94cdf6ac12edb3e4f4c2dd5

Independent structural attribution audit. Exact source relationships and published-only length measurements. Semantic fields from its original judge are excluded here.

evidence/week08-enhancement/20260920/formal-attribution-audit.json

SHA256 aff7b205881e13565688ff455d70bf09abef738cd1722680fbcb7d102504c3e5

Fresh CPU runtime parity. Actual same-host fresh installation and explicitly enumerated deployed runtime subset.

evidence/week08-enhancement/20260920/portable/source-parity-final.json

SHA256 7e855c7a717d7421b8fcd90dbfeed76c4bf325ba7971115d696df0130f7cf0ac
