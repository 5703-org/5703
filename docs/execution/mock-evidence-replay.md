# Mock answering against genuine OpenStax retrieval

On 2026-09-08, the actual `GenerationService` replayed the recorded candidates from the four-book E5/pgvector release `39483e7f-efbe-42e7-855e-469fd924383e`. Every outcome is explicitly `model_mode=mock`. This is a deterministic answer-adapter regression, not live model evaluation, relevance calibration, or proof that an answer is scientifically complete.

The original adapter incorrectly answered “Who won the 2026 Formula One world championship?” with Rice University's mission and philanthropic-support text. Incidental overlap on words such as “world” and “who” was enough to qualify a factual answer. The Kubernetes TLS and yen/euro requests already refused. The original candidates, source hashes, budget-selected evidence, provider messages, response, attempts and timing are preserved in [the before record](../../evidence/openstax/mock-generation-before.json).

The mock-only guard in `generation/adapters.py` now requires every query content word to occur in one contiguous extract of at most three sentences. It normalizes accents, possessives and a limited set of regular English inflections. Generic question scaffolding is ignored; presentation words are ignored only for prepared re-explanation requests. Numbers, named subjects and negation remain required. The guard does not inspect retrieval scores, use a score cutoff, or contain domain/test-question exceptions. Live transport, MCQ option comparison, the evidence-free E0 control and teaching-study behavior are unchanged. The refusal explicitly describes a limitation of the mock answerer rather than asserting that the books lack the answer.

The complete [final after record](../../evidence/openstax/mock-generation-after-correction-scaffolding.json) retains the final adapter and query-preparer hashes and the same input-source hash as the before record. Earlier after records preserve the successive pre-format, formatted-adapter, query-preparer and teaching-regression runs. Actual prompt budgeting kept one to three of the five candidates per question; discarded passages were not used to decide the answer.

| Recorded request | Before | After |
| --- | --- | --- |
| Kubernetes ingress TLS certificates | Refusal | Refusal |
| 2026 Formula One world championship | Incorrectly qualified factual answer | Refusal |
| Current yen/euro exchange rate | Refusal | Refusal |
| Negative feedback and homeostasis | Answer | Answer |
| Erythrocytes, leukocytes and platelets | Answer | Answer |
| Glycolysis, ATP and glucose | Answer | Answer |
| Natural selection and genetic drift | Answer | Answer |
| Food chain versus food web | Answer | Answer |
| Plant light energy and photosynthesis | Learning objectives and question incorrectly qualified as an answer | Mock abstention |
| Prokaryotic versus eukaryotic cells | Answer | Answer |
| Phineas Gage after brain injury | Answer | Mock abstention |
| Crossing over and genetic variation | Answer | Mock abstention |
| Le Chatelier and chemical equilibrium | Answer | Mock abstention |
| Rutherford's gold foil experiment | Answer | Mock abstention |
| Gas pressure when its volume decreases | Clarification | Mock abstention; query-preparer v3 now correctly retains the explicit current subject |
| Photosynthesis: why it needs light | Answer | Answer |
| Photosynthesis: make it simpler | Answer | Answer |
| Photosynthesis: give an example | Answer | Answer |

“Answer” in this table is the actual response category, not a correctness rating. The last three cases reuse the actual photosynthesis candidate set and pass user history through query preparation; they do not claim fresh retrieval or semantic teaching adaptation.

The six on-topic abstentions are a known limitation, including five previously answered cases and the gas case that previously requested clarification. The mock cannot equate injury with trauma, crossing over with crossover, or infer a chemical context absent from the short submitted excerpt. Even when the complete passage contains all words, a request can abstain when those words are too far apart for one short extract. This conservatism is intentional for a mock and does not establish corpus insufficiency. Conversely, co-occurrence can still be misleading: lexical coverage does not establish entailment, temporal correctness, negation scope, complete scientific relations or graphical meaning. Filtering comparison/function request words can leave a source mentioning both subjects without demonstrating the requested relationship. A live answer model and independent source-grounded review remain necessary for those claims. The mock returns source extracts; profile settings do not create unverified simplifications or examples.

Regression fixture [openstax_mock_candidates.json](../../tests/fixtures/openstax_mock_candidates.json) preserves exact unmodified hits for the three unrelated and seven textbook requests, including the acquisition record hash. Six textbook requests retain answers; the plant/light request now explicitly tests the learning-objective/question limitation. [test_mock_evidence_coverage.py](../../tests/unit/test_mock_evidence_coverage.py) checks actual service responses, exact cited excerpts, three prepared follow-ups, numbers/negation, regular inflections, distant incidental matches and independence from retrieval scores. Existing generation engine and response-contract tests are run alongside it. The fixture is not a gold relevance annotation set.

Replay command: `.venv\Scripts\python.exe scripts/verify/replay_openstax_mock_generation.py --output evidence/openstax/<new-record-name>.json`. Output creation is exclusive so a prior record is never silently overwritten. The replay is offline, makes no provider calls, and does not write to the application database.

Validation: 99 tests passed across the targeted candidate regressions, generation engine/contracts, conversation, profiles, evaluation runner and teaching study. Ruff checks passed for the three changed Python files; formatting was applied only to those files. A second agent reviewed the initial guard and tests read-only and found no blocking mismatch, while noting the relationship/co-occurrence limitation above. This is software review, not independent human scientific validation.

The broader PostgreSQL teaching suite initially exposed a supported energy-form question that abstained because of generic form/made scaffolding. The guard now handles the general form/kind/type and make/makes/made families; its new test reads the original unmodified authored integration passage. This adjustment is not a scientific synonym list. All three unrelated real-candidate requests still refuse in the final replay. The earlier after-query-v3 record remains preserved.

Visual review of the actual browser run `2026-09-08T08-09-56-620Z` exposed a further error: a source exercise question was selected as a short answer. Interrogative sentence extracts are now excluded. This also exposed that the broader plant/light request had previously matched learning objectives ending in a question; it now abstains because the assertive text discusses autotrophs, a relationship the mock cannot infer. The unchanged actual candidate fixture retains this as an explicit limitation test. First-turn “What is photosynthesis?” and its light/simpler/example follow-ups still select assertive source text; their response category does not establish teaching quality.

The final correction-family adjustment ignores generic mean/meant scaffolding and preserves the existing clarification-completion request. Consolidated evidence is vidence/openstax/frontend-prompt-consolidation-final.json: 56 actual service outputs, all 16 required frontend/control/source/example/correction software-category checks passed, and all 40 turns in the unchanged 12-family authored workload recorded without invented gold/category expectations. The wider workload still exposes mock abstentions for extended style/topic wording and long prefixes, plus query-preparation limits for extended greetings and an unsupported-premise question. These outcomes remain explicit limitations rather than semantic successes. The earlier consolidation and successive after records are retained.
