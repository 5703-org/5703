# Week 8 protocol amendment 03

Recorded on 21 September 2026 before formal generation. The three six-question development pilots have been inspected and remain immutable; they delivered four, three and four answers respectively. No formal question outputs informed these changes.

## Marker correction

The v2 pipeline can correct markers locally when every factual claim has positive support, teaching and coverage checks pass, and the only remaining issues are exact inline citation-to-source mismatches. Each claim must still match its exact answer substring and map to complete, existing source fragments. The correction changes markers and adjacent whitespace only, rebuilds the citation list and learner projection, and requires a fresh semantic check. Unsupported content, ambiguous spans, clipped sources and other issues retain the ordinary model-repair path. Failed checks retain their failure outcome.

A corrected request typically uses three calls: generation, check and recheck. C2 keeps generic model repair, which typically uses four calls. Both have the same four-call and 180-second ceiling. The B2 versus B1 comparison remains a combined pipeline comparison; C2 measures the registered repair mechanism including its actual call use. Call savings are reported separately from quality scores.

## Lossless checker encoding

When repeated fragment-field names cause the checker request to exceed the model window, encode the same fragment bank as a column table with explicit names. Preserve every identity, block kind, completeness flag and exact source text. Count the complete serialized request again, retaining the configured window and output reservation. Remaining excess returns `CONTEXT_LIMIT`. This representation change neither removes evidence nor increases the context ceiling.

## Numerical notation

Numeric comparisons recognize superscript exponent digits and signs in exact scientific-notation quotes. Original quotes remain unchanged, and the same arithmetic/rounding tolerances apply. The retained calculation failure's final proof validates under local replay after this correction. Its original model outcome remains failed; a local arithmetic replay supplies no new semantic verdict.

The [implementation and retained diagnoses](answer-reliability-v2-20260921.md) give the exact source hashes, measured context sizes and regression evidence. Freeze this amendment alongside the registered protocol and previous amendments before formal calls.
