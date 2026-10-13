# Atomic support candidate and Vertex route repair - 11 October 2026

Main now contains a runnable, offline single-atom support-check candidate and the
missing opt-in Vertex high route. This addresses the concrete configuration failure
and provides a smaller experimental interface; it does not establish that the online
checker detects the saved59 false-positive support judgments. No provider, credential
or database operation occurred, and no budget slot or expense was added.

The actual failure was `ValueError: Unsupported fixed OpenRouter route profile`:
`LLMAdapter._call` at `generation/adapters.py:209` calls `ModelConfig.validate`, whose
`generation/types.py:121` resolves a profile absent from `PROFILES`. The adapter
converts this to `CONFIGURATION_ERROR`, `request_submitted=False`, before `_key`
at adapters.py:211. This was reproduced locally, not inferred from a formal denial.
The historical 58/59 specific actions were accepted and returned HTTP 200; 58 was
output-truncated and 59 completed. Historical refusals stay recorded separately.

The functional fix adds only `gemini35_google_vertex_high_research_v1`, preserving the same
Gemini model, Vertex-only route, no fallback, high reasoning, price caps and endpoint.
`CURRENT_PROFILE_IDS` and default bindings are unchanged. Pre-existing formatting
deviations in the touched route file are normalized with an identical Python AST.
Current Main
`generation.providers.payload` rebuilds saved59 into exactly the same 88704 bytes.
Its saved-cap conservative hold is USD0.0688; this preflight did not reserve it.

Old controllers are not reusable current senders: their source pins, budget positions
and exclusive output directories belong to closed observations. Their public key
calls are selection58.py:192-195 and capacity59.py:135-138:
`legacy.PINS["credential_helper"]` -> `approved_credential(WORKSPACE_ID)`, guarded by
`TARGET_DB == "cs30_week10_pair_b_20261009_01"`. The public archive does not expose
that consumer's exact path or workspace value. No old loader, consumer, private
configuration or substitute credential path was followed. Thus the missing-profile
fault is fixed; a current one-shot sender and the same approved consumer remain
unverified. No new formal platform refusal is claimed.

The candidate is [atomic_support_v1.py](../../generation/atomic_support_v1.py), with
[a short prompt](../../generation/prompts/atomic_support_v1.txt) and an offline
[CLI](../../scripts/verify/atomic_support.py). One input contains one proposition,
its main-proposition condition plus explicit necessary conditions, and actually cited
excerpts with source/evidence identities and Unicode offsets. Full local snapshots
are checked for provenance and excluded from provider messages. Limits are six
conditions, six excerpts and 6000 source characters; messages/schema have a 32768-byte
ceiling, not a verified token/window measurement.

Each condition must retain a supported/unsupported/uncertain opinion. Supported
requires bound exact subquotes and a short semantic explanation. Unsupported requires
reported counterevidence; absence remains uncertain. Explicit reported conflicts
require uncertain overall. Missing conditions, unknown fragments, wrong offsets,
malformed/duplicate JSON and invalid Unicode fail locally. A single injected provider
invocation has no retry; the default has no provider. Quote matching checks provenance
only. Every result keeps semantic truth, decomposition and condition completeness
unverified, human_rating null and production publication unauthorized. The current
production checker is not connected to this candidate.

From the repository root, using the existing interpreter:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = 'E:\5703\learning-assistant\backend'
& '.\.venv\Scripts\python.exe' -B -m scripts.verify.atomic_support --cases tests/fixtures/atomic_support_v1/development_cases.json --case DEV01_guarded_relay_positive
```

This returns `NOT_RUN/PROVIDER_NOT_CONFIGURED`, validated local bindings and zero
provider invocations/POSTs. `--judgment <local-json>` validates a saved reported opinion
without a provider. The actual Main CLI also validated the separately saved authored
counterevidence case, preserving its unverified semantic status.

Actual Main verification passed 128 tests (19 atomic-contract and 109 fixed-route),
with 21 optional SDK skips; configured Ruff lint and format checks passed. Before the route fix, its seven
regressions had 2 failures/5 passes. Independent AI review replayed 12 newly invented
development examples: 3 supported, 3 explicit-counterevidence unsupported, 6 uncertain.
These are authored replies/expectations, not model predictions, human ratings, Gold
or a held-out benchmark. Wrong-subject and false-identity opinions with exact quotes
can still pass structure while every semantic certification flag stays false. The
case inputs and [AI expectations](../../tests/fixtures/atomic_support_v1/independent_ai_expectations.json)
are separate. No quality gain on the 71-block case, RAG comparison or native model
latency is measured.

The [concrete new send scope](evidence/20261011-atomic-support62/next-scope/scope.json)
proposes three cases: complete support, an explicit guarded-rule counterexample and
an unresolved identity bridge. Each prepared request contains one atom, its conditions,
actual excerpts and common instructions/schema. Neutral source IDs prevent expected
label leakage; local mappings, filenames, full snapshots, expectations and manual
judgments must not be appended to the wire. The same Gemini/Vertex high destination
uses 4096 output tokens, at most 3 POSTs, one per case, no retries. The saved-cap
conservative total is USD0.0397527 and the proposed finite cap is USD0.06. This is an
unexecuted new-input plan for parent handling, not an extension of the restricted
same71 grant or a new fee request. The old grant stays 7/USD0.16526676 used,
1/USD0.19473324 unused. General fee authorization persists. No new reservation,
UNKNOWN, model observation or project-completion claim is made.

The [free same-wire preflight](evidence/20261011-atomic-support62/main-wire-preflight62.json)
and [actual Main test XML](evidence/20261011-atomic-support62/main-all62.xml) provide
software evidence. Canonical task/acceptance states remain unchanged and
project_complete=false. The next scientific step needs the concrete new input scope,
current controlled sender/approved consumer, finite reservations and independent
review of actual positive, negative and uncertain model judgments.
