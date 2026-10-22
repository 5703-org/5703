# DeepSeek new-preset working-window repair

This isolated candidate changes one product file: the known official DeepSeek
preset now prepares new configurations with a 32,768-token application working
window. Its description explicitly distinguishes this working budget from the
provider maximum and preserves saved revisions. GPT-6 Luna remains 65,536; all
generic/unknown presets and generic configuration defaults remain 16,384.

No Main file, saved or active configuration, credential, provider/model identity,
tokenizer, output reservation, runtime service or database was changed. Selecting
a preset prepares a new draft; saving, testing and enabling that draft remain
separate actions. Existing saved 16,384-token DeepSeek revisions retain their
explicit window. An operator can deliberately prepare and test a successor.

## Actual verification

The approved synthetic Q2 GEN and CHECK wire requests (physical captures 28 and
29) were replayed locally. Each payload was reconstructed from the exact schema
capture and original messages after removing only the adapter-appended schema
suffix. The real payload compiler regenerated the exact original compact bytes.
`TokenCounter.request_input()` matched counting those complete original bytes
plus its existing 128-token protocol reserve.

| Actual captured stage | Output reserved | Total with historical configured HF tokenizer | Total with preset's labelled estimate |
| --- | ---: | ---: | ---: |
| GEN | 1,024 | 14,264 | 20,111 |
| CHECK | 4,096 | 19,661 | 25,952 |

The old 16,384 preset fails the checker reservation under both counters; its
default estimate also rejects generation. Both stages fit 32,768 for this
representative native multi-turn request. This is not a promise that all legal
or future requests fit. A separately authored oversized full checker input
reserved 67,669 tokens and retained `CONTEXT_LIMIT`. The existing real pipeline
one-token-overflow control also passed and blocked CHECK dispatch after only the
authored GEN stage.

The local tokenizer is the already configured historical
`deepseek-ai/DeepSeek-V4-Flash-0731`, revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`. Its local text count is exact for those
files; the whole-request framing remains an estimate and this does not establish
equivalence to the current mutable provider alias. Provider usage remains the
authority for actual consumption. The new preset retains its existing explicit
estimate setting; this change does not install or silently select a tokenizer.

Fresh results: 26 focused offline tests PASS; Ruff PASS; exact-wire replay before
and after PASS; all 589 accepted Main source rows reverified unchanged. Network,
database and provider attempt counters were zero. No new model calls or cost.
These are mechanics and budget checks, not answer-quality, latency, browser or
native installation acceptance.

The initial wire-replay setup stopped when its subprocess fence blocked Python's
read-only Windows platform version bootstrap during SQLAlchemy import. Its log
is retained as `BEFORE-WIRE-BUDGET-SETUP-STOP01.log`. The rerun completed that
standard-library platform bootstrap before installing the fence, then passed
with zero forbidden attempts. Product code and admission gates were not relaxed.

## Files and remaining work

- `DEEPSEEK-PRESET-ACTUAL-DIFF.patch`: one runtime change, two existing test
  expectation updates, and one new focused test file.
- `RESULT.json`: exact before/after pins, current results and explicit limits.
- `BEFORE-WIRE-BUDGET.json` and `AFTER-WIRE-BUDGET.json`: captured wire/schema
  hashes, counter metadata, role reservations and genuine-overflow diagnostics.
- `FOCUSED-PYTEST.log` and `RUFF.log`: current command output.

Root must review and integrate this change into the approved consolidated
candidate, then perform the combined native/source verification once. This lane
did not adopt Main, alter its original saved v5 32,768 configuration, repeat the
prior semantic suite, or create a delivery archive. Carry these new-draft-only
and tokenizer limits into the runnable full package and member package notes.
