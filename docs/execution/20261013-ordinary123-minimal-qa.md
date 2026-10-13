# Ordinary QA checker checkpoint — 2026-10-13 UTC

The explicit `ordinary_qa_v1` transport now uses the normal application serializer, parser and native publication gates with a task-specific output contract. Paid dispatch remains paused. This checkpoint completes a local checker component; it does not complete project acceptance or measure model quality.

Source-to-target: `generation/ordinary_qa_v1.py` and its short English prompt replace duplicated ordinary-QA input views and inactive teaching decisions only when this transport is explicitly selected. `qualification_v1.py`, `checked.py` and `source_relations_v2.py` integrate admission, parsing and native gates. `tests/unit/test_ordinary_qa123.py` covers the new boundaries. The original source-reference binder, legacy default and rich teaching contract remain unchanged. Exact five original file preimages are retained in `C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-ordinary123-offline\preimages123.json`.

Admission requires the existing qualified ordinary E1 textbook lane, direct help level zero, no current learner attempt or reading assignment and no enabled suggestion, evidence-display or cumulative controls. Unsupported request types reject before generation. Output contains claim/source support, unit relation/condition decisions, contextual qualification, separate source-sufficiency and answer-coverage decisions, disclosed limitations, and the active `answer_only` boundary. The last decision inspects the complete visible answer and maps unchanged to the native tutor-question gate: null tutor metadata cannot pass it. Learner-attempt evaluation is supplied locally as `not_applicable`, with no learner evaluation success. No repair candidate is requested; a genuine qualification defect can be reported without inventing a rewrite. Rich teaching remains on its existing contract.

All supplied source passages remain unchanged and ordered. Claims and units use verified spans into the answer rather than repeated text; original citation scopes are preserved as source-ID groups. Repeated lookup catalogs, source views, inactive task data and redundant summaries are removed. Source sufficiency and answer omissions remain distinct required decisions. Diagnostic prose alone has bounded derivatives; original raw responses, scientific statuses, quotes and gap strings remain unchanged. Unknown, duplicate, ambiguous, incorrectly owned and out-of-scope references fail closed.

| Fixed positive case | Rich wire bytes | Minimal wire bytes | Byte reduction | Exact source passages retained |
| --- | ---: | ---: | ---: | ---: |
| S01 | 84,738 | 35,769 | 57.79% | 64/64 |
| S02 | 79,858 | 34,595 | 56.68% | 54/54 |

The same local Unicode character estimator reports 28,259 → 11,936 and 26,628 → 11,540 tokens. These are labelled estimates, not provider tokenizer counts, billed usage or elapsed-time results. The historical 122 request's 21,228 actual input tokens are a separate measurement. No speedup is claimed. Every uncited passage remains available for limiting or refuting evidence; zero passages were omitted.

Validation: 286 focused unit tests passed in 6.10 seconds, and Ruff passed. Four isolated full native-pipeline controls accept the authored S01/S02 positives and reject the authored S02/S03 negatives. These are transport/gate controls, not independent scientific assessments. Tests also verify pre-generation task rejection, the active answer boundary, uncited contextual limitations, strict inactive-field refusal, scope errors and immutable raw diagnostic prose.

The explicit recent failure set was replayed through the minimal compatibility adapter without altering original records:

| Saved failure | New local adapter outcome; original live result unchanged |
| --- | --- |
| 114 S01 B | Missing active answer-omission decisions; invalid/unknown, no inference |
| 114 S02 B | Missing active answer-omission decisions and an oversized diagnostic reason; invalid/unknown |
| 116 S02 B | Missing active answer-omission decisions; invalid/unknown |
| 118 S02 B | Missing active answer-omission decisions; invalid/unknown; original contradiction retained in historical raw |
| 120 S01 B | Incorrect original evidence owner; projection refused without origin repair |
| 122 S01 B | Full native replay rejects `SOURCE_REFERENCE_OUTSIDE_ACTUAL_CITATIONS` independently of the original inactive boolean failure |

The first five adapter refusals are not completed native semantic evaluations. The sixth preserves every active source selection and reveals the existing claim-2 ev_005 scope error. Historical technical failures, scores, costs and holds remain unchanged; none was converted into a real model pass.

Exact evidence is in `C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-ordinary123-offline\source-evidence123.json` (SHA-256 `1ee37f0f96757985056eb29be547d0b37e836fbac3d98a428a4ec326504b075b`) and its pinned `final-evidence` receipts. `prepared-positive123.json` freezes just two DeepSeek positive inputs, offline and preparation-only. `provider-comparison123.json` freezes the shared question, saved answer, complete sources, schema, temperature and output limit. The checked public configuration inventory identifies DeepSeek only; an existing OpenAI model/configuration is not verified, so no OpenAI model or executable request was invented. Private profiles and credentials were not read.

This task made zero real API, credential or database operations and no installation, archive scan, upload, deployment or course submission. Data, protected staging directories, old reports and all experiment inputs/results were preserved. Remaining work is a separately released small real provider comparison, unified-condition RAG quality evaluation and native send-to-complete-answer timing. Configuration availability and model compliance remain unverified by offline controls. Global project completion remains open.
