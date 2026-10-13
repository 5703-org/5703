# Opt-in current modal statement reference

The exposed case02 input was self-contained but prepared as clarification with no model calls. V22 wraps V21/V20/V19. The earlier declarative anchor in `conversation/query.py:91` requires an article and a limited finite predicate; it does not recognize a named subject followed by `can enter`. The V19 whole-observation rule only covers `What does this illustrate/show/demonstrate/reveal about ...?`. The resulting `missing_referent` makes retrieval unavailable. The frozen lossless-output lane rejects that clarification preparation with `CHECKER_OUTPUT_POLICY_INCOMPATIBLE`. This candidate retains that lane guard and its error classification.

The new opt-in V23 owns one named modal statement followed immediately by `Does this` and a bounded generic event predicate. It preserves the whole original input without substituting a subject. Exactly one dependent pointer must occur within that immediate question. Competing statements, external pointers, extra dependent words, demonstrative noun phrases and unmatched forms delegate to V22. Existing non-reference semantic clarification is preserved: `RAG can operate in a system. Does this require energy?` still needs abbreviation clarification.

The resolution records original-text SHA256 and original-coordinate spans. Semantic equivalence, sufficiency and human rating remain null. Requirement content, conditions, negation, presentation requests and source coordinates remain unchanged. This establishes retrieval eligibility; the existing checker and publication gates still determine support.

The rule is deliberately incomplete: other pronouns, question forms, decimal-bearing initial sentences, coordinated events and several external-pointer-like words are outside it. Some unmatched coordinated subjects are already admitted by V22. Negative controls establish no new promotion rather than claiming all old ambiguity handling is repaired.

## Candidate integration

`integration-candidate` contains four code files and one portable test file, with Main-relative paths. Settings registers `anchored_reference_v23` and retains default V22. Submission freezes V23 plus requirements V8; the normal worker uses those frozen versions for preparation, requirements and trace. The restatement-history allowlists and practice preparer/requirements selectors include V23. Old versions retain their original dispatch. No old command or trial is migrated. Root is the sole Main writer and may use `cas-plan85.json` only while all exact preimages still match and both new targets are absent.

No output schema, lossless codec, publication gate, unit partition, source registry, model configuration, runtime freeze, budget or default policy is changed by this candidate. The original cohort is permanently closed; case02 remains its original failed zero-call result. Root's separate posttrial `generation/checked.py` change is outside this patch. No unseen questions or rubric were read. This is a posttrial local development fix, with no online acceptance or scientific quality claim.

## Free verification

The original 29 controls passed before the additional semantic guard; their XML remains unchanged. `pytest-first85.xml` also preserves the first 26 PASS / 3 FAIL run: its failures were incorrect one-argument test calls to the existing two-argument `evidence_strategy`. Correcting those fixture calls produced `pytest-final85.xml` (29 PASS).

After adding the independent RAG guard, only the affected 13 query/requirements controls were run: 13 PASS, 17 deselected. They include the already-exposed case02 input, water/router examples, literal negation and numeric conditions, history independence, the RAG ambiguity and preparation tampering. Ten additional integration controls passed using actual candidate service AST expressions for submission, worker preparation, requirements and trace, together with real Settings validators and pure practice dispatch. These tests perform no API, SQL, engine, retrieval or publication journey; their selection-policy fixture only activates the preparation path. Six portable controls passed through normal module imports in the W package overlay. Ruff passed with Main's configuration. Audit runners recorded no denied I/O attempts, and used no DB, auth, network or paid service.

The original 29 controls and their initial diagnostic failures are retained; no whole unit suite was repeated. The current focused receipts are `pytest-semantic-guard85.xml`, `pytest-hooks-first85.xml` and `pytest-portable85.xml`. The frozen source and evidence hashes are in `review-receipt85.json`.

From W, the focused hook command is:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
& 'E:\5703\learning-assistant\.venv\Scripts\python.exe' -B '.\5703-checker85-local-reference-fix\run_free_query85.py' '.\5703-checker85-local-reference-fix\test_query_v23_hooks85.py' -q --junitxml='.\5703-checker85-local-reference-fix\pytest-hooks-review85.xml'
```

For the portable candidate test, add `--candidate-v23` and select `integration-candidate/tests/unit/test_query_v23.py`. After Root adopts it, the same portable test imports Main's `conversation.query_v23` directly. Actual SQL/API/retry/worker end-to-end execution was not performed, and remains outside this free preparation verification.
