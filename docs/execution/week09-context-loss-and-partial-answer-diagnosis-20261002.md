# Fresh V18/default-V5 local failure diagnosis

Executed on 2 October 2026 from the newly created public-question development run. The terminal receipt is `fdc27afefb857132511559cd2351faaabc3bdae498e103a9172fd9034205efa0`. Its five scheduled questions produced three publications and two retained failures across 18 confirmed provider calls. This diagnosis reads the new local records and current source. Independent human quality labels remain zero.

## Actual failure path

Both the sugar-axis follow-up and ideal-gas units question executed generation, joint check, local semantic repair and mandatory final recheck. Each used all four allowed calls. Each final checker returned `body_ok=true`, `coverage=supported_partial`, `limitations_explicit=true` and `complete_answer=false`. Every final factual claim was recorded as supported. The publication block reports only `complete_answer` as a failed gate, with no structural or requirement-contract issue and no remaining calls. The application preserved `SEMANTIC_CHECK_FAILED` and published no final answer for these requests.

## Sugar-axis context loss

V18 correctly resolved the current follow-up to the prior DNA/RNA comparison's sugar axis. The immutable V5 requirement retains DNA, RNA and sugars, with its request span located in the current `requirement_source_text`.

The newly retrieved Biology 2e passage contains an eligible complete source sentence on PDF page 110: “sugars is the presence of the hydroxyl group on the ribose's second carbon and hydrogen on the deoxyribose's second carbon.” It occupies original chunk offsets 154:277, with fragment `span_3958a4d05189776117ecec79704454ab` and `complete_block=true`. The separate page-109 passage has unresolved/clipped mapping issues, which remain recorded.

The existing lexical selector preferred the later DNA-backbone sentence because it matched both the object name and sugar noun. The submitted context was offsets 846:1218. The complete structural-difference sentence at 154:277 was absent. The first draft added positional and stability claims with insufficient current bindings. After repair, the final draft named the sugars and explained the missing structural evidence. The checker accurately described the limited submitted context; the omitted eligible sentence shows a concrete selection loss earlier in the pipeline.

The private candidate retains every complete block with a literal requested-axis match, in addition to every existing object/facet anchor. Its range becomes 154:1218, keeping the exact source wording, intervening qualifiers, offsets and hash. The original selected context remains a substring. The second evidence range stays 96:607. Re-mapping the candidate excerpt yields the identical complete structural fragment, including its original ID, coordinates, hash and completeness flag. Source-map issues remain unchanged. The candidate retains existing complete-block filtering and every final support/highlight/publication check.

The second passage comes from Anatomy and Physiology 2e review questions and includes a multiple-choice distractor among the surrounding material. Candidate retention establishes provenance and lexical coverage. It supplies no independent scientific support judgment for that passage.

## Ideal-gas units evidence

The fresh input contains 19 original candidates. The relevant Chemistry 2e passage explicitly lists `8.314 kPa L mol−1 K−1` and `0.08206 L atm mol−1 K−1`, with dimensional-analysis wording. The final submitted context and checker quote retain this passage. The raw candidate set also includes the pressure definition `1 Pa = 1 N/m2`; it contains no joule definition or explicit J-to-kPa·L equivalence identified in the inspected text.

The final checker records the kelvin requirement as sufficient and covered. It records the J-based pressure/volume requirement as partial, then accepts the repaired answer's explicit limitation. The available records establish an evidence/derivation gap in this finite direct-service run. They provide no comparable omitted eligible J-equivalence sentence for the proposed axis-anchor fix. Full-product targeted supplementation and a newly grounded dimensional derivation require separate execution and assessment.

## Publication-contract observation

`generation/prompts/joint_check_v5.txt:15` defines completeness as the full direct question and permits supported partial bodies. Line 24 says supported portions with explicit named limitations can publish. Its example at line 29 combines `complete_answer=true` with `supported_partial`. `generation/checked.py:1934` still requires `complete_answer=true`, and line 2184 includes that active gate. The two actual final records consistently returned completeness false while all their asserted facts passed.

This wording leaves the desired completeness treatment of an honest partial direct answer unresolved. The observed failures remain rejected under the current contract. The candidate changes context selection only; it leaves prompts, verdicts, schema, budgets and publication gates intact.

## Additional consumer observation

`generation/coverage_v2.py:39` rebuilds typed requirement terms from the literal short request. For the sugar follow-up it produces language/sugar in place of the producer's DNA/RNA/sugars targets. Those presentation words appear in coverage and teaching-plan traces. The minimal context candidate leaves this consumer unchanged and records it for a separate scoped follow-up.

## Verification and next step

The private candidate passed 27 authored packing regressions and 33 existing reliability-v2 tests. Tests cover generic comparison axes, retained conditions and negation, exact offsets/hashes, old anchors, invalid coordinate metadata, and unchanged clipped/atomic exclusions. Project-configured lint and formatting passed. These tests validate packing behavior. Actual regenerated answer quality and delivery for the same exposed five questions remain pending a reviewed candidate, new source gate and finite run. All current Gate04 failures remain part of the development baseline.
