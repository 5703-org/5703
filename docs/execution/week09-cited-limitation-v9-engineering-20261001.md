# V9 cited-limitation repair: actual MAIN engineering verification

The opt-in `scoped_compact_v9` policy adds a narrowly checked answer-repair route
for a current source-gap sentence that carries textbook citation markers. The
shared runtime retains `typed_joint_v5` as its default. Actual MAIN verification
passed 277 checks: 66 new authored cases and 211 retained V1/V6/V7/V8 regressions.
The [engineering receipt](../../evidence/week09-continuation/20261001/citation-limitation-v9-main-engineering-20261001.json)
records exact before/after hashes for fifteen participating source and test files.
They remained unchanged during verification. No provider, HTTP or database
connection was attempted; connection guards were active throughout the test run.

## Observed failure and repair boundary

The [retained real V5/V8 pilot](week09-supported-answer-v5-v8-pilot-20261001.md)
delivered 2/4 V5 and 3/4 V8 requests. In the selected-passage V8 request, the
checker independently classified a cited sentence as `evidence_limitation`.
The valid compact guidance union contains only `claim_id`, `basis` and `reason`.
Its actual draft citation produced `COMPACT_UNEXPECTED_CITATION_FOR_BASIS` and
`UNEXPECTED_CITATION_FOR_BASIS`. The existing V8 path requested another judgment
of the unchanged draft and retained a three-call `CHECKER_INCONSISTENT` failure.
These automatic findings leave independent draft correctness unscored.

V9 requires both named codes to identify the same current claim. The new
`generation/semantic_negative_v2.py` helper validates the strict complete compact
schema, the exact raw guidance union and matching normalized claim identity,
basis and reason. The normalized record must be nonfactual with empty fragment
IDs and null problem/calculation proof fields. It reconstructs the current
`PROPOSED_DELIVERY` response, scientific unit ranges and unchanged V8 citation
scope, then verifies actual evidence IDs and known allowed fragment identities.
Missing, stale, foreign or duplicate identities retain contract failure.

Only this proven defect can defer the two named basis/citation diagnostics into
the blocking `CITATION_ON_EVIDENCE_LIMITATION` repair obligation. The original
binding issues and `CHECK_LIMITATION_BASIS_INVALID` remain in structural validation.
The current draft cannot publish. Existing bounded claim patching preserves
protected scientific spans and the changed response receives a fresh complete
final check. Raw model judgments, bases and citations remain recorded. Unknown
schema, quote, source, proof and gate issues stay in the original contract path.
Other semantic findings use the unchanged V1 routing.

The V9-only generation appendix separates plainly stated source gaps from cited
scientific statements. V9 retains the existing V8 scope and prompt text, strict
compact V6 output schema, complete lossless source context, teaching/source gates
and four-call/180-active-second budget. V5/V6/V7/V8 keep their recorded dispatch.
Ordinary textbook answers remain complete, with honestly bounded partial answers
subject to the existing requirement and limitation checks.

## Actual verification and retained failures

The MAIN test run used the reviewed six-file implementation and the existing
verified offline tokenizer cache. In authored fixtures, V9 completed a local
patch and final check in four calls; the same V8 fixture retained its three-call
failure. Two protected scientific clauses stayed exact and in order. A negative
final check, missing repair/final-check budget, missing independent gates, invalid
union fields and source/quote/proof faults all blocked publication. Plain uncited
limitation records kept ordinary validation. These are execution and contract
observations; they supply no independent scientific or learning-quality labels.

Ruff format and static checks passed with `--no-cache`; all five Python files
were already formatted. The first checks failed before content inspection when
Windows denied temporary-file creation in the existing `.ruff_cache`. Those
failures remain in the receipt. No source formatting was performed. The native
patch preserved CRLF in `checked.py` and `service.py`; their exact MAIN hashes
differ from the private LF candidate while normalized text and Python AST match.
The four original V1/V8 implementation/prompt files remain byte exact.

The earlier private candidate runs and their fixture/cache failures remain
retained separately. This focused suite overlaps the unified software gate.
Full final-source software verification, installed runtime acceptance, actual
V9 output, cost and independent human judgments require separate receipts.

## Next comparison

The [prospective four-case V5/V9 protocol](week09-cited-limitation-v9-pilot-protocol-20261001.md)
keeps the original exposed public material and schedules all eight requests.
Current gate/source/helper bindings and full executor review precede any model
call. Previous generated drafts and the separately blocked review batches stay
outside successor model inputs. Human ratings and independent quality scores
remain zero at this engineering checkpoint.
