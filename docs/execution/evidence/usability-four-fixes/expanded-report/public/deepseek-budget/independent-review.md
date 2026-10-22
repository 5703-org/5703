# Independent source and evidence review

Reviewer: Codex delegated `preset_review`, separate from the candidate author. Disposition: **CLEAR for the scoped isolated change; Main adoption remains pending**. This review read source and existing results and recomputed file hashes. It did not rerun tests, execute the replay, access a database, call a provider, inspect processes or edit Main.

The only product change prepares the official DeepSeek preset with a 32,768-token application working window and explains that it is not the provider maximum. The nested conditional retains Luna at 65,536 and every other preset at 16,384. Python's conditional-expression precedence makes the entire concatenated description apply only when `provider != "mock"`; the mock description remains exactly the authored-local statement. The DeepSeek-only prefix cannot leak into other preset descriptions. Generic configuration defaults and immutable saved revisions remain unchanged; existing saved 16,384-token DeepSeek revisions are not migrated.

The replay source removes exactly one adapter-added schema suffix from a copied system message, checks the separate captured native schema and schema name, and requires the actual compiler to regenerate the original compact request bytes. It then cross-checks `request_input()` against counting those original bytes plus the existing 128-token reserve. The preset's default labelled CHECK estimate is **21,856 input + 4,096 output = 25,952 total**, already including output once. It is not 25,952 plus another output reservation. GEN totals 20,111 under that estimate; both fit 32,768 and exceed the old preset. The historical local HF CHECK total is separately 19,661. The retained oversized fixture totals 67,669 and records `CONTEXT_LIMIT`.

The existing focused log records 26 PASS and zero forbidden attempts; the Ruff log records PASS. These are reviewed author-produced results, not a second independent test execution. The initial platform-bootstrap setup stop remains retained. The local tokenizer is not certified equivalent to the mutable provider alias; whole-request framing remains estimated. No broad quality, accuracy, latency, browser, native installation or all-future-request guarantee follows from this repair. No new provider call or cost was introduced by this review.

All paths below are relative to this review's directory. Actual SHA256/byte pins read during review:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `candidate/backend/app/modules/model_settings/service.py` | 20737 | `a6a70ab51c2a69c567459ca69050a00134c791960d42a33405f06ef7b1c697eb` |
| `DEEPSEEK-PRESET-ACTUAL-DIFF.patch` | 7378 | `08d5ab0227d112f2f301c6e1d9b16620f859195c3b07013b1d6bb0ae981cd670` |
| `RESULT.json` | 6601 | `9d8bf7b3dd3af851d60c5bc491bc3fc2ff4aee651538b3586d0f56a63cd88c3b` |
| `BEFORE-WIRE-BUDGET.json` | 7912 | `07c3bc859c416212595e6e67f3ebdda4ef9481e6dfd39f938778201084e1aea8` |
| `AFTER-WIRE-BUDGET.json` | 7908 | `acd6cf6150ca88c44518aab695945216ad83b5fd1ff8e4e7cf20d84154b56c94` |
| `README.md` | 4128 | `fe8aea538a83c14fd3f8907bc297a3efcd5d16439dad03e336b198268908c999` |
| `replay_wire_budget.py` | 9479 | `9da3cbb0196d5cfa2ef791a1f62ced5021d24eb621e234b1ef6796be80ab5eaa` |
| `FOCUSED-PYTEST.log` | 285 | `daed41367be7f6745e4f4f041937c12bc995550aa78465c4f9e049edd669b51e` |
| `RUFF.log` | 20 | `a4443afdcfb6d7363adb285762515ccf7cf50473b1a05c20c1a50f6bed4d26b0` |
