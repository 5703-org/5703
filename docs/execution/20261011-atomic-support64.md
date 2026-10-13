# Atomic support pilot - 11 October 2026

Only **one of three actual responses qualifies under the original atomic contract**.
The guarded relay response is complete, correctly bound and agrees with the independent
AI review. The gate counterexample response is truncated. The packet-identity response
preserves uncertainty but has an invalid quote interval. The historical all-supported
failure remains unresolved by eligible negative or uncertain results.

The [preregistered standard](evidence/20261011-atomic-support64/preregistered-standard64.json)
was frozen before opening the outputs. Sources and expectations are invented AI development
fixtures, not human ratings, Gold labels or held-out material. Expected labels, local review
opinions and full source snapshots were excluded from the request bodies.

| Actual case | Output cap | Original-contract outcome | Service-reported cost (USD) | Complete adapter return (ms) |
| --- | ---: | --- | ---: | ---: |
| [DEV01 guarded relay](evidence/20261011-atomic-support64/case01-result64.json) | 4096 | Complete supported; exact witnesses and independent semantic concurrence | 0.0094622 | 9849.5493 |
| [DEV03 dropped guard](evidence/20261011-atomic-support64/case02-result64.json) | 4096 | OUTPUT_TRUNCATED, finish=length; incomplete JSON, no complete verdict | 0.010675 | 13133.6101 |
| [DEV11 identity bridge](evidence/20261011-atomic-support64/case03-result64.json) | 8192 | Complete raw uncertain; C1 quote interval fails binding | 0.0113754 | 13084.0855 |

The [raw contract audit](evidence/20261011-atomic-support64/audit64-final.json) records
DEV11's `JUDGMENT_SLICE_MISMATCH`. The model's C1 quote is 45 Unicode characters long,
but interval 78-125 includes an extra ` I`; the unchanged quote ends at 123. The
[independent review](evidence/20261011-atomic-support64/independent-review64.md)
agrees with the semantic opinions and unresolved-identity gaps, while retaining this
binding failure. This diagnostic does not overwrite the response or turn it into a
historical pass. DEV03 remains a failed execution, rather than a passed unsupported
judgment or an observed supported error. One qualifying response out of three attempts
is a qualification count, not an accuracy estimate.

The [first leg](evidence/20261011-atomic-support64/batch64-stopped.json) stopped after
the truncated second response. The third case had not been sent. Its
[amended wire](evidence/20261011-atomic-support64/wire64-third8192.json) changes only
`max_tokens` from 4096 to 8192; restoring 4096 reproduces the original wire exactly.
Messages, schema, excerpts, offsets, model, route and preregistered expectations remain
unchanged. The differing output caps prevent a uniform-condition comparison. There
was no replay of the failed case, retry or fourth request.

All three HTTP POSTs are settled: this scope used USD0.0315126 of its USD0.06 cap,
with new UNKNOWN0 and zero remaining request slots. The old eight-call batch remains
unchanged at USD0.19758306. Combined known cost is USD0.22909566 under the existing
USD0.36 cap. Durable UNKNOWN reservations preceded transport and cost settlement
preceded optional validation. General fee authorization persists; this work creates
no additional request allowance. The destination remained OpenRouter's
`google/gemini-3.5-flash-lite`, Vertex only, high reasoning, without fallback.

Added an explicit local helper,
[`bind_atomic_quote_offsets`](../../generation/atomic_quote_binding_v1.py), plus
[nine portable boundary tests](../../tests/unit/test_atomic_quote_binding_v1.py).
It adjusts invalid coordinates only when the unchanged quote occurs exactly once
inside its own actually cited fragment, counting overlapping occurrences. Existing
valid coordinates remain unchanged. Missing, ambiguous, sibling-fragment or altered
Unicode matches fail; no source, condition, verdict, reason, gap or quote is changed.
The original strict validator checks the result. The default execution path remains
unchanged, and this helper has no production integration.

Main verification completed: **28 targeted tests passed** (nine new binding tests and
19 existing atomic contract tests), and Ruff lint/format checks passed for both new
files. The [independent code review](evidence/20261011-atomic-support64/binding-review64.md)
also passed the nine tests and three separate boundary probes. The
[Main test receipt](evidence/20261011-atomic-support64/main-tests64.xml) and
[free saved-output replay](evidence/20261011-atomic-support64/main-binding-replay64.json)
retain the current code pins. The replay changes only C1's end coordinate 125 to 123;
the normalized local judgment passes strict binding with its uncertain verdict and
identity gaps intact. Original raw validation and default execution still reject it.
This uses one in-memory saved-reply fixture and **zero external requests**. It is
provenance repair, not a new model observation or semantic truth certification, and
does not upgrade the historical one-of-three qualification.

The [bounded evidence manifest](evidence/20261011-atomic-support64/evidence-manifest64.json)
pins the published public results and reviews. Original provider reads remain preserved
in their existing workspace locations; no credentials, private learner data or large
provider-reasoning archive is added to the repository.

These are three single checker observations. They do not establish a causal improvement,
noninferiority, p95, native send-to-complete-answer latency, or unified RAG quality.
Human ratings remain zero/null, canonical acceptance statuses remain unchanged and
`project_complete=false`. The complete negative response and a binding-valid uncertain
response remain gaps in this original pilot. Whole-project acceptance remains open.
