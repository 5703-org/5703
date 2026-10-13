# Qualification113: opt-in checker, gate and local repair integration

The qualification112 proposal is now executable inside the existing generation
pipeline. This checkpoint changes seven scoped code/prompt/test files, retains the
default checker and installs no dependency. It does not dispatch a model request
or establish real semantic/scientific quality or project completion.

## Behavior and reversible selection

The server setting CHAT_CHECKER_SCHEMA_POLICY accepts the explicit
textbook_context_qualification_v1 value; its default remains None. Use it with the
existing source_relation_contract_v2 and typed_joint_v5 policies. The existing
answering service freezes the setting through checker_schema_submission_fields
into the saved command and restores it into GenerationRequest on execution.
There is no learner-facing selector or new untrusted HTTP request field. Omission
or disabling the trusted setting retains the prior schema, prompts and checks;
old saved commands do not acquire the new policy.

The explicit lane is ordinary E1 interactive textbook V2 checking, without current
attempt or compact output/transport. The existing textbook-only packet/basis
fences remain; this research lane does not silently force guidance/general or
uncited limitation claims into textbook claims. It supports JSON Schema or JSON
object output, with the existing complete schema supplied in trusted instructions.
The older textbook_checker_schema_research_v1 policy still requires JSON Schema.
Unsupported combinations fail before generation. This opt-in selection is not a
default activation or a declaration that every provider profile is qualified.

One joint checker call returns all existing source/unit/coverage/teaching judgments
plus the claim-level qualification_assessments array. Original citation support
and context status are separate. The new trusted prompt explicitly replaces only
Checker110's earlier routing of context-only restrictions to source status,
unit flags or body_ok. Original own-citation gaps still fail the original gates.
No scientific answer key, enzyme special case, extra extractor or online NLI is
introduced. Neither citation_support_exists nor a candidate revision overrides
any existing negative judgment.

## Bound quotes, failure and repair

Original positive quotes must come from the same claim's actual supporting,
selected, allowed citation fragments. Limiting and candidate-revision quotes may
use the complete submitted context, without promoting them into original positive
proof. Every quote is an exact unique contiguous substring of a complete source
block. The program computes Unicode offsets using the established source mapper's
source_unit_id/start/end/offset_basis; the model's schema accepts no coordinates.
Unknown aliases, duplicate/ambiguous/rewritten quotes and incomplete or invalid
source bindings fail. Complete unique textbook-claim coverage is required.

needs_qualification requires quoted limiting evidence, an explicit restriction,
an advisory minimal revision, candidate support quotes and candidate entailment
true/context clear. conflict also requires actual limiting evidence. Absence of a
limiting passage alone does not reject a supported precise answer or authorize an
invented restriction. Exact coordinates establish provenance, not semantic
relevance, entailment or independent scientific truth; all such local certification
flags remain false and human_rating remains null.

Context semantic defects join structural_issues and prevent publication. Their
claim IDs exclude the affected claims from protected_exact_claims even when their
original source statuses are supported. The valid needs-qualification/conflict
codes also admit the existing ordinary source-only local patch when no correct
claim can be protected. Other cases keep the previous repair eligibility rules.
The repair feedback contains the canonical assessment and actual relevant source
IDs/quotes, including real limiting/candidate blocks. The proposed revision is
advisory: no deterministic answer replacement or verdict promotion occurs.

Correct protected spans stay verbatim. The patched answer goes through the whole
existing source/citation/unit/coverage/teaching path AND the qualification checker
again, including unchanged claims. Failed final context or source judgments block
publication. A clean answer uses generation -> joint_check; a local repair uses
generation -> joint_check -> semantic_repair -> joint_recheck. There is one checker
call per draft revision. Malformed output fails QUALIFICATION_CONTRACT_INVALID
without a checker-contract correction request, fallback or additional extractor.

Raw alias judgments and locally resolved canonical assessments remain separate in
private check records; canonical assessments also reach the existing token-budget
report and repair feedback. The existing checks/budget/persistence envelope carries
the new fields; public answer DTOs and source visibility rules are not changed.

## Focused validation

The final source-pinned suite passed81 tests:20 new integration controls plus61
directly relevant source-unit, Checker110 context and output-policy compatibility
controls. Ruff correctness checks passed for the five Python files; new module and
test formatting passed. Unrelated formatter-only changes to the pre-existing
checked/source-relation files were restored with AST equality, preserving their
previous style and reducing the patch scope. No full inventory rehash, unrelated
regression suite or source reset was performed.

New controls cover precise supported answers and absent limiting evidence;
quoted contextual defects while retaining supported source statuses; correct
content protected through local repair; all-unsupported-context cases with no
protected claim; mandatory complete final recheck and failure after repair;
missing/duplicate/foreign claim metadata, invented/non-selected quotes, unknown
aliases, model offsets, missing limits and conflicting candidate metadata;
default behavior and trusted setting freezing; and incompatible scope rejection.
The actual LLMAdapter/compiler/parser path is exercised against an intercepted
synthetic DeepSeek JSON-object provider response. New controls fence sockets and
DNS. These are authored software controls, not measured model efficacy, scientific
labels, normal live publication or latency. No real database was accessed.

Commands are retained in results and the archive. The principal suite is:

python -B -X utf8 -m pytest -q -p no:cacheprovider tests/unit/test_context_qualification_v1.py tests/unit/test_source_relation_units_v2.py tests/unit/test_checker_context_scope110.py tests/unit/test_single_selection_output_integration.py --tb=short

## Controlled real comparison prepared, not dispatched

The accompanying JSON plan freezes three public archived common-input snapshots:
S01 Native111 catalysis scope (64 complete blocks), S02 red-cell osmosis/net movement
(54), and S03 fixed-temperature/volume chemical equilibrium with temporary net
reaction (50). The latter two are adjacent non-enzyme concepts. Each variant uses
the same question, frozen teacher response, full source bytes/IDs and settings;
only the explicit checker policy and its schema/prompt/gate differ. No source
packing, fabricated limits or new model-generated teacher draft changes the inputs.

A retains the existing default checker; B selects qualification_v1. Two repetitions
of each of three cases use balanced A/B and B/A ordering,12 initial checks total.
The sequence is S01A,S01B,S02B,S02A,S03A,S03B,S03B,S03A,S02A,S02B,S01B,S01A.
Each negative run may make one local repair and one complete fresh recheck; maximum
new physical requests36, no extractor/correction/retry. The archived teacher replay
makes no new teacher request and is explicitly a controlled replay, not normal
live generation, Send-to-complete latency, TTFT or p95.

Model/route is official DeepSeek deepseek-flash, non-thinking, temperature0,
max output4096, total window65536, max input61440 and timeout60s. The
[official pricing page](https://api-docs.deepseek.com/quick_start/pricing) was
retrieved by an ordinary public HTTP200 GET on12 October2026 after web-tool
timeouts; retained HTML shows peak cache-miss input USD0.30/M and output USD1.20/M.
At these caps, one request costs at mostUSD0.0233472;12 initial checks at most
USD0.2801664, all36 at mostUSD0.8404992. Proposed new finite batch budget:USD0.90,
with no cache discount assumed. This estimate is not an invoice or a dispatch.
Older closed scopes, costs and UNKNOWN holds are not reused or reclassified.

Before future dispatch, join every archived alias to the frozen original fixture's
program-owned source units/coordinates, freeze current compiled-wire/config/source
hashes, verify A/B common bytes and pre-call windows, and bind a separate finite
request/budget journal under the standing user authorization. This implementation
step deliberately does not create a live controller or access fixture credentials
or PostgreSQL. Missing original coordinate joins must stop; snapshot positions
must never be mislabeled as original source coordinates.

Record own-citation support independently from context status; independently label
source-fidelity false acceptance of unqualified drafts and false rejection of
qualified controls; retain present/absent limitation strata, schema/quote failures,
correct-content preservation and final recheck outcomes, stage timings and exact
physical usage/billing. Independent scientific correctness remains a separate
assessment. A three-case pilot cannot establish global quality or p95 and will not
automatically replace the default.

## Git, preservation and remaining limits

The earlier Git dubious-ownership rejection at E:\5703\learning-assistant was not
worked around: no safe.directory, ownership or security setting changed, and the
denied Git command was not repeated. It blocks optional branch/worktree metadata
inspection, not filesystem source editing. Current scoped edits and free execution
succeeded and are identified by exact content hashes; branch metadata is not
claimed as newly verified. Three changed-file preimages remain in W113.

Original112/111 deliverables, default107/110 prompts, databases, protected staging
directories, experiment data and old billing records remain preserved. No other
project, dependency, remote upload/push, deployment or course submission changed.
The scoped default-prompt hashes were checked, rather than rehashing the entire
historical inventory. The opt-in path is now integrated and free-verified; real
semantic effectiveness, normal-page full-answer latency, broader RAG quality and
project-wide acceptance remain open. project_complete=false.
