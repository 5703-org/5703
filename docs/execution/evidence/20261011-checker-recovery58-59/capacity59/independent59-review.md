# Capacity59 independent selected-fragment review

The retained response is structurally eligible, and the current production V2 local contract accepts it. The model labeled all 10 claims and all 19 literal syntactic units `supported`. Independent inspection of each unit's own selected source text finds **five definite partial units**, plus **one ATP unit whose shared predicate ownership changes its classification**. All-selected-source support is therefore **incomplete**.

This is a review of one repeatedly exposed saved case, not human Gold or held-out data. It evaluates selected proof sufficiency, not whether every original statement is scientifically false or true. Original provider labels, the accepted local result, and frozen artifacts remain unchanged. [Machine-readable evidence](independent59-review.json) preserves all 19 exact literal texts, spans, supplied text hashes, selected fragments, own citation bindings, original labels and separate classifications.

## Qualification and distinct gates

- Provider `finish_reason=stop`, `error=null`; complete JSON is retained without repair.
- Original schema, typed/full schema, repeat structure and scoped validation gates all pass.
- All 19 original syntactic units are present. Every selected fragment is assessed in a supporting citation belonging to its own claim; invalid own bindings: **0**.
- Current production V2 `assessment.accepted=true`; local binding/relation/declared-semantic checks pass.
- Production `source_entailment_locally_certified=false`, `semantic_atomicity_locally_certified=false`, `independent_evaluation=false`, `human_rating=null`. Its acceptance does not independently establish all selected-text entailment.
- Native publication and publication override remain false.

| Diagnostic convention | Complete | Partial | Total |
| --- | ---: | ---: | ---: |
| ATP energy-role compatible literal-unit reading | 14 | 5 | 19 |
| Strict ownership of shared reduction predicate | 13 | 6 | 19 |
| Entire claims, either convention | 6 | 4 | 10 |

These counts are case diagnostics, not a calibrated accuracy estimate. The denominator is **19 literal syntactic slices**, whose semantic atomicity is not certified. Two additional read-only reviews concurred on the five definite gaps and ATP sensitivity; they add no paid-model observations or human Gold.

## Review rules

Only fragment IDs actually selected for the same unit are credited, and only when assessed in that claim's own supporting citations. Sibling-unit fragments, claim-only citations, other claims and the rest of the original 71-source pool cannot complete a unit's proof. The original claim resolves syntactic coordination and pronouns; a required scientific predicate, quantity, condition or purpose must still appear in that unit's selected source text.

`complete` means selected text suffices for the literal unit under the specified ownership convention. `partial` means selected proof establishes some content but misses an asserted part. Unselected context IDs recorded in JSON are audit references, not Gold selections, appended proof or a guaranteed repair recipe.

## All 19 original units

C1-C10 follow the provider's original claim order. Exact claim IDs and literal unit text are preserved in JSON.

| Claim / unit | Own selected fragments | Compatible | Strict | Selected-proof finding |
| --- | --- | --- | --- | --- |
| C1 U01 | F056, F064 | partial | partial | RuBP five-carbon and phosphate-at-each-end attributes are absent. |
| C2 U01 | F056 | partial | partial | Counts and immediate split are present; the product name 3-PGA is absent. |
| C3 U01 | F058 | complete | complete | ATP stored energy is explicit; no independent electron-donor claim is made. |
| C3 U02 | F058, F059, F018 | complete | complete | Own selected F058/F059/F018 establish named conversion, reduction and electron gain. |
| C4 U01 | F057 | complete | complete | Inorganic-to-organic fixation and its name are explicit. |
| C5 U01 | F012 | complete | complete | Two G3Ps per turn is explicit. |
| C5 U02 | F011 | complete | complete | Three Calvin-cycle turns to export one G3P is explicit in F011 itself. |
| C5 U03 | F013 | complete | complete | Remaining G3P regeneration and readiness for more fixed CO2 are explicit. |
| C6 U01 | F001 | complete | complete | G3P departure for carbohydrate, commonly glucose, is explicit. |
| C6 U02 | F002 | complete | complete | Six-carbon carbohydrate and six Calvin-cycle turns are explicit in F002 itself. |
| C7 U01 | F021, F003 | complete | complete | Remaining G3P becomes RuBP; both own sources establish regeneration. |
| C7 U02 | F021 | complete | complete | F021 includes the RuBP antecedent and readiness for more CO2. |
| C8 U01 | F004 | complete | complete | ATP use in RuBP regeneration is directly stated. |
| C9 U01 | F056 | complete | complete | RuBisCO/CO2/RuBP reaction is directly stated. |
| C9 U02 | F056 | partial | partial | Six-carbon to two three-carbon products is explicit; 3-PGA identity is absent. |
| C9 U03 | F058 | complete | partial | ATP energy-role compatible; shared reduce-predicate ownership is incomplete. |
| C9 U04 | F058 | partial | partial | Conversion is explicit; reduction classification is absent. |
| C10 U01 | F013 | complete | complete | One export plus five retained regeneration participants establishes Most. |
| C10 U02 | F011, F019 | partial | partial | Three-turn export quantity is explicit; carbohydrate purpose is absent. |

## Definite selected-proof gaps

1. **C1 U01, F056/F064:** the reaction and Fixation stage context appear, but neither selected fragment states RuBP has five carbon atoms or a phosphate group on each end. The molecule name is not proof of these explicit attributes. F055/F065 elsewhere in the input were not selected for this unit.
2. **C2 U01 and C9 U02, F056:** the chosen text says a six-carbon compound is immediately converted into two three-carbon compounds. It never names those products **3-PGA**. C9's claim-level F058 cannot be borrowed into U02; C2 also selects only F056.
3. **C9 U04, F058:** the selected text says ATP/NADPH use stored energy to **convert** 3-PGA into G3P. It does not itself classify this conversion as **reduction**. F059 supplies reduction/electron-gain language elsewhere, but this unit and claim did not select/assess it.
4. **C10 U02, F011/F019:** F011 explicitly proves the three-turn/export-one condition. F019 ends with `leaves the cycle to become a 5 • Key Terms 131`; the carbohydrate-purpose object is absent. F020 is the unselected continuation. Claim-only F009 merely names other compounds, and a sibling/other claim's carbohydrate source cannot be borrowed.

The last point does **not** imply C5 U02 has a three-turn deficit. F011 itself contains `it takes three “turns” of the Calvin cycle to fix enough net carbon to export one G3P`. That is the condition C5 U02 asserts, despite the clipped leading clause. C10's quantity is also supported; its missing part is the destination's purpose.

## ATP predicate ownership

C9 U03 is the literal slice ` which ATP`; the next slice is ` and NADPH reduce to G3P [ev_007].`. This split is not an autonomous semantic decomposition.

Under the energy-role compatible reading, F058 establishes ATP's participation through stored energy, so U03 is complete. Under strict ownership of the shared `reduce to G3P` predicate, U03 also requires explicit reduction classification, which F058 lacks, so it is partial. U04 is partial under either reading. Neither convention turns ATP into an independent electron donor or an independent reducing agent. The raw model status stays `supported`.

By contrast C3 U01 explicitly says `The energy in ATP`, and its selected F058 directly supports that literal energy slice. C3 U02 selects **both F058 and F059**, preserving the named conversion and the reduction/electron-gain classification with its antecedent. Its proof does not depend on borrowing another unit's selection.

## Fixed input evidence

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| actual59/result59.json | 63952 | `230de5d6ff787f79cddd7161ebbcddbdc40c173af442de1e3081b3bf558e082b` |
| actual59/provider-result.json | 13062 | `47a6ef6cc5e8da463b75955fc96510501ebaab6552a7a467693362b72e6dfc11` |
| wire59-PREPARED-UNVERIFIED.json | 88704 | `c14a0748a60e981f03d5f2d5731ba87048909514ac45d4e3d28828e656913b40` |
| review59.json | 3903 | `8da3fea42534fdedf249b6acde3a0f9695c377354a7442f9b18ab60027dd5ac8` |

The wire differs from fixed58 only by `max_tokens: 8192 -> 16384`; all other outbound fields and the three message role/content strings match. The original 71 fragments, 10 claims and 19 units are unchanged.

## Execution limits and interpretation

The retained observation used one POST with zero automatic retries. Reported settled cost is **$0.0260363**, aggregate **7 requests / $0.16526676**, new UNKNOWN hold **$0**; remaining authorized scope is **1 request / $0.19473324**. This review does not schedule or spend that remaining slot.

The measured **17,479.3151 ms** is one adapter-return observation, not native browser send-to-render latency or p95. Capacity59 produced a complete output after the capacity change; this single exposed case does not establish a causal quality improvement from the correction or token limit, a RAG comparison, wider course acceptance or deployment readiness.

Only these two new review files were written. Frozen controllers, wire, receipts, results and prepared reviews were not modified. No authentication, database, network, model execution or Main write was performed for this review.
