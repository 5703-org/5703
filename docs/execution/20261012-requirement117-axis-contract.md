# Requirement 117: offline requirement-axis contract repair

The qualification116 response conflates selected-claim proof defects with question-level source availability. It does not describe a genuine missing required knowledge point. The normalizer and requirement assessor did not invent that gap: the raw provider response itself says partial, covered and missing_information="". The same requirement reason says all three solution comparisons are covered.

## Exact diagnosis

The fixed answer already states hypertonic outward and hypotonic inward water movement, as well as isotonic normal-volume retention. The raw missing_facets list nevertheless calls those delivered predicates missing. Original complete submitted F021 and F023 state the movement directions; F015 states normal volume and shape in isotonic solution. The raw claim reasons instead identify proof absent from each claim's selected citations. These are different scopes. F018 additionally contradicts the stop-crossing assertion, which remains a real contextual/source rejection, not an omitted question requirement.

This evidence supports an axis-conflation diagnosis; it cannot disclose the model's private intention. No omitted knowledge point can be manufactured from the empty missing_information field. A source gap, an answer omission, a selected-citation support failure and an overbroad/context-conflicting assertion are now explicitly distinguished. Exact provenance validation remains separate from semantic entailment.

## Small opt-in patch

- generation/requirement_axes_v1.py defines a requirement schema with explicit source-versus-delivery semantics. missing_information is required: exactly empty asserts no source gap, without certifying sufficiency; missing, null or whitespace is invalid. The model must name a real requested source gap for partial/absent/conflicting. An answer omission belongs to response_coverage and its reason, not a fabricated source gap.
- generation/qualification_v1.py applies that schema only to the existing opt-in policy, observes raw gap-field states in the decision derivative, and never fills absent fields or rewrites statuses. Named missing_facets cannot be empty/whitespace.
- generation/checked.py selects the new requirement assessor only in the qualification lane. All existing V5 identity, quote, proof, sufficiency, condition, direct/hint, coverage and limitation gates remain active. Nearby additional checks reject absent-with-evidence, inapplicable-with-gap, unrelated-with-proof and named facets with no source/delivery gap.
- generation/prompts/qualification_check_v1.txt gives the matching axis precedence and a single-call final consistency pass. The full submitted bank establishes question-level source availability; actual selected citations still establish each original claim's own proof. Contextual qualification cannot create a requirement gap. No semantic override, answer rewrite or extra checker call is introduced.

Production defaults, baseline compiler requests, sources, fixed answers, old raw responses and prior experiments are preserved. A small public fixture retains the exact historical raw content and five original relevant complete fragments; it is a requirement-gate regression fixture, not a new corpus or an independent quality score.

## Verification

137 targeted controls passed (32 new, 105 existing); Ruff check and three-file format check passed. Commands and final source/log fingerprints are in C:/Users/PC/Documents/Codex/2026-10-04/task-2/5703-requirement117-free/final-free-complete-v2/free-verification117.json. The runnable unified patch is in that directory as requirement117.patch (43,123 bytes; SHA-256 2948854d59908987be38fc2cbae75006607be3e0bd36c800bf105bf5425449d0).

Controls cover a genuinely missing requested rate, a complete answer, available-but-omitted content, explicit empty versus absent/null/whitespace, malformed containers, exact quote/proof/conditions, required limitations, direct/hint/inapplicable semantics and separate context/source gates. Permitted hint deferral is explicitly not a missing facet at the current help level; both the allowed empty-facet and inconsistent named-facet cases are tested. Network and DNS are fenced in new controls. The original initial formatting failure and earlier receipts remain saved; the final receipt passes.

The complete ordinary pipeline replay of the unchanged116 response remains technically invalid, with only REQUIREMENT_GAP_UNSPECIFIED. Semantic acceptance remains null. Its requirements, original claim/unit statuses and contextual conflict remain unchanged. The old raw envelope SHA-256 remains e9ff96a8af4996c0ef659e6bc8c41447956db86c6f26121cd6c0c01630973136. Raw model-content SHA-256 is 6c9bf7378f84547ca2933d4725dff0afdafec56f6876fbfe540359d16eed4e98. No historical failure becomes a pass or valid paired sample.

Run the relevant local suite from the repository with .venv/Scripts/python.exe -B -X utf8 -m pytest -q -p no:cacheprovider tests/unit/test_requirement_axes117.py tests/unit/test_context_qualification_v1.py tests/unit/test_qualification_decision_transport115.py tests/unit/test_source_relation_units_v2.py tests/unit/test_checker_context_scope110.py tests/unit/test_single_selection_output_integration.py --tb=short.

## Exactly which prepared requests remain valid

| Complete comparison | Current request IDs | Content/scope | Old wire validity |
| --- | --- | --- | --- |
| S02 negative | S02-negative-B, S02-negative-A | Preserved | A exact; B superseded |
| S03 negative | S03-negative-A, S03-negative-B | Preserved | A exact; B superseded |
| S01 positive | S01-positive-B, S01-positive-A | Preserved | A exact; B superseded |
| S02 positive | S02-positive-A, S02-positive-B | Preserved | A exact; B superseded |

All eight rows/four complete comparisons retain their reviewed labels, complete fixed questions/drafts and identical A/B source context. Four baseline A body hashes remain exact; all four B bodies have been regenerated with the current schema/prompt. New operational IDs and wire/source pins are frozen in W117/prepared-eight117-final.json. Old116 prepared B bodies/source pins must not be dispatched. S03 positive remains outside the proposal; the old114 S01-negative pair and invalid116 sample are not reused as current valid pairs.

No real requests, keys, DB operations, new lease or new holds occur in this step. Existing source snapshots and budget receipts are reused without a corpus/billing re-audit or current-pricing assertion. Saved116 off-peak rates yield total eight-request upfront protective holds CNY0.822584; the old proposal cap is CNY0.80 and original remaining capacity is CNY0.818598. Therefore all eight cannot be guaranteed by an upfront reservation within either bound. Individual complete-pair upper holds are CNY0.202681, 0.205601, 0.210275 and 0.204027 in table order. A later reviewed rolling complete-pair controller must admit each entire pair against actual remaining protected capacity and stop before any unfunded pair; it cannot promise all eight or silently expand the budget. Real-time pricing/window validation belongs to that future admission step. Current dispatch is disabled.

This checkpoint repairs the opt-in transport contract and routing instructions, not model semantics or overall project acceptance.

Independent final source review: checker87_terminal_review RELEASE for the six final source/test/fixture pins and final-v2 verification receipt. No remaining source blocker. Review confirms all original V5 gates and invalid historical decisions remain intact.
