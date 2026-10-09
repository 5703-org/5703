# Source sufficiency: retrospective development audit

The [structural source audit](../../evidence/week09-learning/20260930/source-sufficiency-development-audit.json) and [eight-case AI pilot](../../evidence/week09-learning/20260930/source-sufficiency-ai-pilot-v1.json) use previously inspected Week 9 V8 OpenStax retrieval material. They are development diagnostics. They do not add V10/V11 formal outcomes, independent human labels, or learner-benefit measurements. The [selection receipt](../../evidence/week09-learning/20260930/source-sufficiency-ai-selection-v1.json) was frozen before the eight model calls.

## Verified source identities and unresolved semantics

The source audit read the frozen 52-concept-group catalogue and both read-only CPU preparations: 52 textbook QA cases and 52 tutoring cases. It hashed the four local original OpenStax PDFs and checked them against the active release's verified package record. All 106 authored official anchors and 1,166 accepted-passage observations had valid source-text hashes and official source URLs. The frozen corpus metadata records 10,594 real E5 vectors of 384 dimensions. The audit made no new database or model calls and excluded no difficult case.

| Structural observation | Count |
| --- | ---: |
| Concept groups with every declared anchor accepted in both tasks | 48 / 52 |
| Cases with every declared anchor accepted | 96 / 104 |
| Individual declared anchors accepted with exact source identity | 98 / 106 |
| Authored required knowledge points | 257 |
| Points in cases with all declared anchors accepted | 237 |
| Points in cases missing at least one declared anchor | 20 |
| Accepted-passage observations / unique passage identities | 1,166 / 575 |
| Retained `UNEXTRACTED_VISUAL_CONTENT` warnings | 1,150 |

Anchor presence establishes a retrieval and source-identity fact. It does not prove that a particular point is semantically supported. The private review packet therefore records **257 unknown point-support labels and 104 unknown context-sufficiency labels**. The 20 points in anchor-missing cases are not automatically unsupported; other accepted passages could still contain their information. No warning-bearing passage was silently removed.

The eight-case follow-up was selected by a fixed rule before calls: four anchor-present and four anchor-missing cases, four QA and four tutoring cases, eight distinct concepts spanning all four books. The judge saw only the accepted source passages, the question and authored required points. An absent declared anchor's text was withheld. The runner required a structurally valid result and exact source-substring quotes for supported or partial point labels.

All eight `deepseek-flash` calls returned valid terminal AI ratings. Across 20 required points the AI gave 14 `supported`, three `partial`, two `unsupported` and one `uncertain`; at case level it gave four `sufficient`, two `partial`, one `insufficient` and one `uncertain`. All quoted snippets occurred verbatim in the cited accepted passages. The runner did not independently establish semantic entailment or evaluate generated answers. There were zero answer-generation calls, online-checker calls and human ratings. The judge belongs to the same provider family used in earlier product outputs.

Provider usage was 16,873 input and 2,471 output tokens, including 2,688 cache-hit input tokens. The sum of provider-call wall times was 13.8522 seconds; the eight-call median was 1.6629 seconds. The USD 0.003618414 estimate uses the observed off-peak period and [DeepSeek's model pricing](https://api-docs.deepseek.com/quick_start/pricing/) checked on 30 September 2026. It has not been reconciled to an invoice. All eight calls and all failed-attempt slots remain in the terminal denominator; this run had no provider failure or retry.

## Reproduction and evidence boundary

The project includes the generic [structural audit runner](../../scripts/verify/source_sufficiency_development_audit.py) and [AI pilot runner](../../scripts/verify/source_sufficiency_ai_pilot.py). Both match their preserved private work copies byte-for-byte. The AI runner also matches its executed version. The structural runner received formatting and an error-type cleanup after the first receipt; a new read-only execution of the packaged bytes reproduced the private 104-case review packet **byte-for-byte**, while the two public receipts differ only in audit timestamp. They take all private catalogue, preparation, provider-config and `.env` paths as command arguments; no credential or private machine path is embedded. The structural audit uses only Python's standard library. The AI pilot uses the existing provider adapter, limits each selected case to two attempts, and stores every raw prompt and provider reply outside the distributable project. Its public receipt contains blinded IDs, source hashes, usage, timing, terminal states and explicit label provenance.

Run `python -m scripts.verify.source_sufficiency_development_audit --help` and `python -m scripts.verify.source_sufficiency_ai_pilot --help` to obtain the required input arguments. To reproduce the source audit, supply the coordinator-held frozen catalogue, QA/teaching `preparation.json`, original preflight, verified runtime-parity receipt and original-PDF directory. The two outputs must be new paths: one private review packet and one sanitized public receipt. The AI runner first uses `prepare` to freeze its eight selections and then uses `run` with that manifest, a separate new result directory and the configured local `LLM_API_KEY`. Existing outputs are never overwritten. A new run is a separate observation, not a replacement for the preserved eight calls.

Focused software checks passed: five unit tests cover concept-distinct deterministic selection, quote and submitted-source binding, sufficient/uncertain consistency, original-PDF/text identity and unknown-cost handling. Both runners and the tests passed Ruff lint and format checks. The [V8 formal receipt](../../evidence/week09-continuation/20260930/formal-v8-automatic-sanitized.json) remains unchanged: its 240 terminal outcomes belong to two families, and it has no independent source-sufficiency labels. Its saved QA evidence is not always an exact copy of the live generation prompt, so these retrospective preparation labels cannot be backfilled into V8 answer-quality endpoints.
