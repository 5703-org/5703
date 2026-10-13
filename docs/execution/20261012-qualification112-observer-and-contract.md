# Observer112 repair and single-call qualification proposal

Verified on 12 October 2026 UTC against the current local 5703 repository. This
checkpoint installs verification helpers and delivers an unregistered contract
prototype. Project completion, live quality and native latency remain open.

## Delivered change and free verification

Native111's async `waitForFunction` predicate accepted a truthy Promise before the
durable answer was displayed. Its negative raw elapsed value remains historical;
complete-answer and refusal elapsed times remain null. The new helper arms before
Send, preloads the existing renderer outside the clock, polls with one in-flight
read, and uses synchronous predicates. Accepted receipt, job, request, answer,
schema and answer/refusal status must join. A persisted answer alone cannot finish
observation: the matching answer node must render the complete reference text,
visible text and ordered citation labels without generation progress. The reference
uses the installed ReactMarkdown/GFM/math/KaTeX pipeline; current Markdown.tsx is
SHA-pinned and drift fails before Send. Source rendering is verified separately
from scientific correctness.

The source resets an invalid render candidate and waits through two animation
callbacks. A failure requires the matching user's exact failed/cancelled visible
state; failure is not answer/refusal timing. Every bounded wait exit disposes the
interval, abort controller, mutation observer, animation callback and click
listener. Temporary reference DOM is removed in finally. HTTP401/403 stops
observation without retry or bypass. Caller browser closure follows the bounded
observation. The new observe_one_submission wrapper exercises arm -> Send -> 202
receipt -> durable join -> complete DOM -> cleanup, rather than leaving an unused
utility next to the original faulty predicate. Old111 files are not overwritten.

Installed paths:

- scripts/verify/browser_terminal_observer.cjs
- scripts/verify/observe_one_submission.cjs
- scripts/verify/test_browser_terminal_observer.cjs

Run `node scripts/verify/test_browser_terminal_observer.cjs` from the repository.
The existing installed Chrome and Playwright are used; CS30_CHROME can specify an
existing Chrome executable. All fixture HTTP is intercepted by route.fulfill:
there is no real server, provider, authentication fixture or database. The current
candidate and installed copy both passed 15 browser controls. These reproduce the
old async-false bug; reject stale IDs, matching-citation truncated text, wrong
citation identity, hidden final text and DOM-before-commit; handle durable refusal,
matching failure state, denial, wrong request, invalid/elapsed timeout and cleanup;
and exercise the integrated lifecycle. The invalid/restored candidate control
asserts no terminal at restoration; it does not separately assert absence of a
terminal after the first restored frame. Independent static review confirms the
reset and two-callback source logic. This is a focused software regression, not a
live observer acceptance, recovered Native111 clock, TTFT or p95.

## Smallest proposed change inside the existing checker call

Current UnitAssessment has status, fragment_ids, relation_preserved and
conditions_preserved. These boolean flags do not separately represent actor,
time scale, temporary/net change, definition scope, causation or modality. Keep
all existing claims, units, citations and gates; add one claim-level
qualification_assessments array to an opt-in ReliableUnitCheck subclass. No new
atomic-claim extractor, decomposer or runtime round trip is proposed.

Each record contains claim_id; citation_support_exists; context_status (clear,
needs_qualification, conflict, insufficient_evidence); exact supporting/limiting
quotes; applicable qualifier dimensions and restriction; optional minimal_revision;
separate revision_supporting_quotes, revision_entailed and revision_context_status;
and a short reason. For example, a needs_qualification record requires an actual
quoted limitation, explicit restriction and minimally revised candidate whose
quoted source entailment is true and contextual status is clear. This contrastive
assessment stays in the same call and does not automatically rewrite an answer.

Original supporting quotes can come only from that claim's actually selected and
assessed cited fragments. The original proof is their necessary union, not maximum
chunk support or a requirement that every fragment individually entail the whole
compound claim. Limiting quotes can use relevant complete submitted context.
Candidate-revision evidence can also use other submitted fragments, but never
retroactively proves the original. No supplied limitation means no invented quote,
automatic model-knowledge rejection, or silent interpretation of unchanged as
throughout/net. Different actors or conditions do not constitute contradiction.
clear describes supplied-context fidelity, not independent scientific truth.

The proposal validator enforces complete/unique textbook-claim coverage, known
aliases, own-citation positive proof and exact contiguous unique quote occurrence.
Coordinates are computed from existing program-owned evidence/source/start/end
bindings in Unicode code points; the model cannot supply offsets or new IDs.
Ambiguous repeated quotes fail instead of selecting an arbitrary occurrence.
These checks certify shape and binding only. They cannot determine semantic
entailment, actual relevant contradiction or scientific correctness.

The seven proposal unittests include 24 authored combinations: six cross-concept
pairs (cyclic working substance, heat definition/contact route, plant-population
generality, survey association/causation, temperature condition, coating possibility)
crossed with original/precisely qualified text and limiting-context present/absent.
Positive controls use the precise supplied source sentence; negative controls
expand scope. Expected judgments are authored; the original text is not passed to
a model by these tests. Model predictions, false-acceptance and false-rejection
rates and independent science scores remain null. Additional controls reject
unknown/uncited/noncontiguous/ambiguous quotes, coverage errors, model offsets,
negative context without quoted limits and empty revisions. The prototype, full
JSON schema, contract, pair inventory and executable tests are in the evidence ZIP.

## Evidence-based limits and research rationale

[TriQua](https://arxiv.org/html/2608.05228v1) reports strong direct few-shot
verification on supplied-evidence short claims and degradation from decomposition.
Explicit qualifier slots here are an unproven hypothesis, not a paper-established
fix for this application. [FactCG section5.3](https://aclanthology.org/2025.naacl-long.258.pdf)
uses the highest score over document chunks; swapping the checker alone would not
resolve supporting versus limiting-context interactions.
[Auto-GDA](https://arxiv.org/html/2410.03461) provides a possible future offline
domain-adapted NLI direction, which needs representative adaptation/evaluation
data. No added online NLI call or training run is included here.

Before integration, independently label source fidelity and scientific correctness
on balanced cross-concept pairs. Track false acceptance of unqualified originals,
false rejection of correctly qualified controls, present/absent limitation strata,
JSON/quote failures, candidate failure and total answer time. No scientific answer
key or fixed enzyme rejection belongs in the production gate. Existing science
NO_GO and costs are not rewritten as PASS by these authored controls.

## Payload and latency sensitivity

Offline measurement replaces only the frozen Native111 wire's compact checker
schema and adds this contract. Current compact-schema equality is checked first;
all non-system source/user messages and existing output claims/units are retained.
Serialized wire grows from 90,229 to 95,141 bytes: +4,912 bytes. Representative eight
clear records add 3,582 output bytes; three qualified plus five clear add 4,614.
Example quotes are illustrative payload strings, not rejudgments or resolved
Native111 evidence. Hashes describe this local compact serialization, not a new
provider dispatch or the original dispatch's raw bytes.

At the rough UTF-8-bytes/4 sensitivity convention, added input is about1,228 tokens
and output about896 or1,154 tokens. This is not the provider tokenizer or billable
usage. The old measured checker used21,516 prompt/2,121 output tokens and8.134s.
The unchanged4,096 output cap would fit these illustrative sizes under this
heuristic; longer quotes/claims may not. No cap is silently raised and no context
is removed to fit. Extra output at1/3/5ms per token gives about0.90/2.69/4.48s for
eight clear records, or1.15/3.46/5.77s for the three-qualified example. These are
scenarios, not latency predictions: changed input prefill, reasoning, scheduling,
network and parsing are omitted. Additional runtime calls proposed: zero.

The observer clock ends at confirmed durable/full visible DOM and includes polling,
DTO/reference comparison and stable-frame overhead. It is not the earliest
unobserved render time. A new continuously observed normal journey is needed to
measure that boundary; no model or real-data test was run at this checkpoint.

## Preservation, review and remaining work

Independent reviewer checker87 released exact helper702a8c1c…54dc94 and
testbcf8bb93…7535aa after source and retained-receipt inspection; reviewer did not
rerun tests. Exclusive installation and installed free rerun passed. Sixty-nine
predecessor source/delivery files retained their hashes; all prior raw answers,
billing, databases, experimental inputs/results and protected staging directories
were preserved. Zero provider calls, database operations, credential reads,
dependency installs, remote operations or course submissions occurred.

Git branch/worktree inspection was blocked by Git's dubious-ownership check at
E:\5703\learning-assistant. No safe.directory configuration or bypass was made;
branch/worktree state is not newly verified. File-based scoped changes and exact
predecessor pins remain inspectable.

The contract is unregistered and no production checker prompt/schema/default or
repair eligibility changed. Integration must be explicitly versioned through
compiler/parser, coverage/binding validation, gate and protected-claim eligibility,
repair and mandatory full fresh recheck. A contextual defect must not be accepted
just because own-citation support is true. Both original and candidate context
must be checked; correctly qualified controls must not be rejected unnecessarily.
Existing Native111 scientific scope failure and unknown continuous DOM time remain
open. Project-wide acceptance, unified-condition RAG quality, full-answer latency
and formal p95 are not marked complete by this checkpoint.
