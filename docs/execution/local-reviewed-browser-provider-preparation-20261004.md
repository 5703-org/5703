# CS30-1 reviewed gate, browser and provider preparation, 4 October 2026

## Review results

Five files were promoted with per-file compare-before-write checks and retained
originals: `scripts/verify/all.py`, its snapshot-control unit test and the chat,
lifecycle and session-controls Playwright tests. No production UI behavior or
answering behavior changed in this promotion. The gate now captures 921 inputs,
including 25 previously omitted deterministic registries, foundation records,
retrieval evidence, OpenAPI files and tokenizer cache blobs. Its 18 input controls
passed after promotion. Generated schema outputs remain excluded. Every child
stage is forced to use the captured in-repository tokenizer cache.

The expanded authored browser run passed all 15 cases with disposable PostgreSQL,
an API, both worker lanes and a local frontend. Three initial failures were
retained: two selectors matched both New chat and Learning workspace, and an
incomplete topic-only restatement was incorrectly expected to answer. Exact
button selectors and complete-question clarification assertions corrected these
test defects. The 15-case pass used the reviewed candidates before promotion;
the final expanded browser and full eight-stage gate must run on the eventual
unchanged completed source. The previous 896-input full gate remains historical
evidence for exactly that earlier source, not a 921-input pass.

A fresh C-workspace offline provider audit passed 171 cases and two subtests,
including 27 new candidate controls. These cover all eight preset mappings,
frozen answer/checker metadata, native OpenAI/local localhost transport and finite
401/429/503 behavior. These candidate tests are not yet promoted. No external
provider was called. Localhost transport tests establish protocol behavior, not
account connectivity or model teaching quality.

## Bounded business repair awaiting integration

The original selected question combines a leading example preference with a
photosynthesis explanation request. V21/V7 treats the preference as required
knowledge, which creates a spurious retrieval/coverage obligation. Separately,
the unchanged mock requires literal prefer/examples/sunlight content absent from
the authored passage and correctly retains its refusal. Neither cause establishes
a semantic source-support judgment.

New V22/V8 candidates separate only a verified leading, period-separated example
preference with an explicit matching science owner. They preserve science IDs,
literal spans, conditions, global constraints and saved predecessor behavior.
Nine implementation files remain C-only; current source defaults to V21. Initial
81 candidate controls passed. Independent review found an omitted V8 comparison
consumer; its one-line registration correction is prepared. Native API, worker,
SQL, retry/regeneration, practice, comparison and unit-lookup checks plus a fresh
full gate remain prerequisites to promotion/default rollout. Strict mock terms
were not relaxed and no paid model was used.

## Credentials and provider scope

The user enters credentials locally: Administration > Models > New configuration,
Provider preset, Model name, Base URL, API key, then Save configuration. Do not send
keys in chat. The saved active revision overrides environment-only configuration.
Compatibility Test connection and Enable tested version are separate operations;
real tests can contact providers. No existing `.env`, key store or key file was
read, printed or copied in this audit.

Required current preset routes are openai, azure_openai, anthropic, gemini, ollama,
deepseek, custom and mock. Supported protocols also include local. DeepSeek and
custom use openai_compatible. Models are editable; the local DeepSeek default
deepseek-flash is not proof of current account availability. Record endpoint,
deployment, protocol and managed revision separately from underlying base-model
identity. Duplicate gateway/original model routes still need connection tests but
must not inflate the count of distinct base models in quality comparisons.

The user authorizes an unlimited experiment budget. Numeric budget is no longer
a missing input. Stages still require finite call/token/time bounds, actual usage
and cost accounting, abnormal-stop rules, exact model identities and approved
data destinations. No recharge, subscription, new credential configuration or
public deployment is implied. Visible reports use Review results; underlying
methods and actual participation remain accurately traceable.

## Offline installation blocker

Read-only cached-image inspection matched 50 of 55 runtime pins with no conflicting
pins. Missing distributions are cffi==2.1.1, cryptography==50.0.1,
pymupdf==1.28.2, pycparser==3.0 and tiktoken==0.14.0 for Linux CPython 3.13.
This finding is bounded to the inspected CS30 images and visible built-wheel cache.
The prepared isolated Compose candidate passed syntax validation only and was
not built or started. It uses owned temporary data, new volumes, cached images,
localhost ports and mock configuration. Completing installation requires trusted
matching offline wheels/image or permission to download the exact missing pins.
No dependency was installed and no internet connection was used.

An attempted image inspection including Config.Env was rejected by automatic
approval review because it could expose embedded credentials. That action was
abandoned; safe ID and package-version inspection completed instead. Old artifact
directory access refusals were respected and not bypassed.

## Delivery and remaining inputs

Retained originals include COMP5703-(GP)-Project_Final_Report_template.docx,
PG Capstone Third Individual Report Template.docx, Presentation.pptx and
AI_Acknowledgement.docx. The v5 engineering specification requires a separate
English technical final report and reproducible implementation/validation/research
evidence. It does not mandate a final report filename or LaTeX in the inspected
sections. Existing Week09 reports are weekly deliverables. The four directly
inspected final-delivery folders were empty; this is not a global claim that no
final draft or LaTeX source exists.

Needed course inputs are the current Canvas brief/rubric/template, deadline and
submission format/naming, real member identifiers/contributions and signatures
where required. If LaTeX is desired, supply the approved source/template location.
Missing final score sheets do not block current engineering. Physical device and
independent-host observations remain distinct from local desktop browser evidence.
Frozen model-comparison design and exact available account model IDs remain
needed before actual provider execution. An old zero-provider practice study
runner can trigger current saved text-assessment providers; do not run it as a
free test until its fail-closed repair has been reviewed.

All work remains confined to CS30-1. Protected staging installations, real
databases, experimental inputs/results and historical deliveries were preserved.
The next continuation must finish the C-only candidates, independently review
them, promote with exact source hashes, run isolated native tests, run the final
full gate and expanded browser checks, and save current evidence.

[Retained round evidence](../../evidence/week09-continuation/20261004/task2-round2-reviewed-01/manifest.json).


## Completed 921-input regression, 4 October 2026

The unchanged 921-input source passed all eight mock software stages on 4 October 2026 at 13:04:56 UTC: 3,311 Python cases, two subtests and 196 frontend cases. The owned temporary database container was removed. E-source parity was checked before saving these results. V22/V8 native candidate verification separately passed 148 cases; its implementation is still unpromoted and V21 remains the source default. A blank local API draft and instructions were created outside the project under C:/Users/PC/Documents/5703-private-api. That private file may now contain user credentials and must not be read, copied, overwritten or included in evidence. Only its original creation metadata was retained. A separate fictional-file validator is under development; no actual credential consumption, database import or provider call occurred. [Exact completed gate and cleanup](../../evidence/week09-continuation/20261004/task2-current921-full-06/manifest.json).
