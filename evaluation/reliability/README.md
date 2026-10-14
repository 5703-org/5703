# Week 8 reliability evaluation

This evaluation uses the published four-book OpenStax corpus. The HTTP suite exercises the interactive application; the CPU retrieval pool separately measures query preparation, retrieval, reranking and screening. The authored questions are evaluation inputs; they are never ingested as textbook material. Formal SciQ E0/E1 definitions, historical outcomes and published corpus identities remain separate.

## Fixed question set

`week08_cases_v3.json` contains 120 cases: 30 standard, 20 wording, 15 multi-turn, 10 ambiguity, 15 outside-scope, 10 partial-support, 10 cross-chapter/formula and 10 isolated attack/failure cases. Thirty science topics bind 60 immutable passages with book, edition, license, section, physical pages, text and hash. These are source review targets selected within specified textbook sections. Independent relevance and answer judgments remain blank.

Knowledge groups determine the development/review split (75/45). The v1 binding draft remains preserved. V2 refined section bindings; its first raw retrieval and HTTP runs retain their original plan hashes and 77/43 grouping. V3 merges ambiguous and clarified RAG dialogues into one family. It changes grouping only, before any relevance labels or fitted threshold. Derived review artifacts must explicitly record that correction and verify unchanged case questions, expectations and source passages. A derived artifact is not a new execution. This developer regression set includes previously inspected concepts, and cannot be described as an independent unseen scientific benchmark.

## Commands

Run from the repository with `PYTHONPATH=.;backend` on Windows. Retain each attempt in a new output path.

```powershell
python -m scripts.verify.week08_retrieval_pool --plan evaluation/reliability/week08_cases_v3.json --output evidence/week08-retrieval-new.json
python -m scripts.verify.week08_reliability run --plan evaluation/reliability/week08_cases_v3.json --output evidence/week08-http-new.json
python -m scripts.verify.week08_reliability teaching --plan evaluation/reliability/week08_cases_v3.json --output evidence/week08-teaching-new.json
```

Retrieval uses real E5, PostgreSQL/pgvector and the pinned MiniLM reranker on CPU, with a read-only corpus transaction and no answer-provider calls. Its history contains the declared user turns; it does not generate prior assistant answers or execute application evidence reuse and packing. The HTTP suite requires a tested enabled live provider, creates its own verification learner/sessions, executes every scheduled case including failed cases, and preserves actual generated history turns, states, citations, timings and request budgets. The 14 teaching cases cover three questions at three levels, two hint requests, two false premises and one detailed explanation. The supplemental `robustness` command adds six spelling, negation, condition and comparison cases. None of these scripts supplies textbook answers or evaluator labels to the chat service.

The ten attack/failure cases are deliberately executed in isolated tests or the disposable CPU installation. Sources are not revoked in the development corpus to simulate a test. The final evidence map identifies the exact test/job and whether its scope is injected transport, loader failure, source visibility or real provider execution.

## Calibration workflow

The retrieval pool exports each question/chunk pair with the exact model revision, raw score, source text/hash and blank `label`, `reviewer_id` and `reviewed_at`. An independent reviewer assigns topical relevance 0 or 1 and completes every scheduled pair. The reviewer keeps difficult negatives and uncertainty notes; unresolved labels remain blank and block fitting.

```powershell
python -m evaluation.reliability.calibration --pool original-pool.json --judgments reviewed-pool.json --model cross-encoder/ms-marco-MiniLM-L6-v2 --revision 233902d25c440f23af6f7d6e94d2946bac0bee0a --output calibration-proposal.json
```

The fitter reconciles every reviewed pair against the original pool, rejecting omitted pairs or changed source text, identity, grouping and scores. It also rejects blank judgments, group leakage, duplicate pairs, mixed model revisions and missing development classes. It chooses a cutoff from development data alone, reports holdout confusion counts separately and never activates its proposal. The current -4.0 prototype cutoff remains provisional until reviewed calibration and a separately versioned activation pass. Topic relevance does not establish claim entailment.

## Review rubric

Review answer correctness, evidence coverage, citation support and presentation separately. Use 0 (incorrect/unsupported), 1 (major gaps), 2 (minor gaps), or 3 (fully meets the criterion). Record the concrete incorrect or omitted statement and the source location. Use an empty value where a judgment cannot be made; do not convert missing ratings to zero.

For each important claim, inspect its actual cited passage and applicable conditions. Check structure (ID and source resolve), support (the passage warrants the claim), and completeness (important claims and qualifications have sources). The runtime lexical/locality flags are review aids. Their absence does not certify truth, and their presence does not prove an error.

For partial-support questions, verify that the supported science is answered and the unrelated requested part is explicitly identified without an invented textbook citation. For hints, verify one useful step without revealing the final solution. For false premises, verify a respectful, source-supported correction. For levels, inspect terminology definitions, prior-knowledge assumptions, causal steps and examples rather than using response length as a quality score.

## Independent learning protocol

The next human study uses consenting learners and an instructor-reviewed item set. Randomize presentation condition within balanced prior-knowledge groups; freeze the condition order, source material, scoring rubric and exclusion rules before recruitment. Collect an unaided pretest, the assisted task, an immediate unaided transfer question, and a delayed unaided test after seven days. Keep assisted task performance distinct from transfer and retention.

Candidate source-bound topics are enzyme activation barriers, buffer capacity and gas-law conditions. A transfer item changes the example or asks which condition invalidates a conclusion. The instructor must approve item difficulty, marking keys and timing before recruitment. Do not infer learning gains from the 14 generated teaching outputs. Human reviewer identity, ratings, participant outcomes and physical-device/assistive checks remain external evidence until actually collected.
