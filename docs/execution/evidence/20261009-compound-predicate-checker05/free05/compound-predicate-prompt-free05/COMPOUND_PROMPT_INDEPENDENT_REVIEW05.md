# Compound-predicate prompt review and free controls

The proposed generic per-predicate audit is suitable for adoption. It makes the selection and final output audit explicit using the existing claim `reason` and citation fragment IDs. It changes no schema, source text, binding, scientific flag or publication gate.

Reviewed proposal: `../compound-predicate-root05/joint_check_v5_predicate_audit_PROPOSED05.txt`, 16,953 bytes, SHA-256 `475d8bee5ba754c672be1b9a65f3b4b60777cc6bb0a23fdaea99381869a85c76`.

The current 15,931-byte prompt already requires inspecting every asserted predicate and qualifier and using the actual supporting citation set to establish the whole claim. Actual checker result 04 therefore demonstrates model noncompliance with an existing rule. The additional paragraph is an instructional repair, not evidence that semantic accuracy improved.

The addition requires each assertion and condition to be supported by the fragment union actually returned for that claim. It excludes fragments merely available elsewhere, passages selected for another claim, and the draft itself. It retains complementary support and the existing permission for meaning-preserving paraphrases and necessary inferences. It does not create a word-match guard or demand fabricated joined quotes. The existing reason field is limited to 800 characters; concise support links fit the contract.

Five authored controls ran through the current `GenerationService` with the proposed checker template supplied only in the local free process:

| Control | Authored judgment | Pipeline result |
| --- | --- | --- |
| Original compound, only F053 selected | Partial: G3P formation is supported; carbohydrate consequence and stroma qualifier are unestablished | Blocks publication |
| Three separately scoped facts, selecting F053, F054+F055, and F037 | Supported with complementary source links | Accepts authored gates |
| The G3P consequence selects F054 without F055 | Partial: the carbohydrate continuation is absent from selected support | Blocks publication |
| A complete location and carbon-fixation claim cites two complementary passages | Supported with F037 and F051 | Accepts authored gates |
| Original false-pass pattern is deliberately replayed | Supported incorrectly, despite missing predicate support | Accepts, reproducing the known dependence on checker semantics |

All five expected gate outcomes passed in 0.144 seconds. The fifth case is a recorded limitation, not scientific certification. The controls retain separate F054 and F055 source strings and never fabricate one exact quotation across their boundary.

The separate source reviewer confirmed that F054 and F055 are adjacent prose within the same retained chunk, across source units/pages. Together they establish the conservative statement that G3P can leave the cycle and become part of a carbohydrate molecule. The intervening page furniture supplies no scientific condition. That independent interpretation is the basis of the authored positive fixture; executable fixture success does not independently establish its scientific truth.

The control geometry is synthetic and uses byte-exact retained source text. The normal fixture packing step assigns `ev_001` to the original `ev_007` material and `ev_002` to the original `ev_010` material; this lineage is recorded. This was not a replay of the full actual request, original fragment metadata or all 67 submitted fragments.

Before imports, the harness blocked sockets, urllib and SQLAlchemy engine construction and disabled dotenv loading. There were zero provider POSTs, database reads/writes and Main writes. The proposed template overlay was process-local. Two authored fixture setup errors were retained: unsupported helper keyword arguments, then citation IDs incompatible with the normal synthetic packing alias assignment. Only the fixture setup was corrected.

Deliverable: `ACTUAL_FREE_COMPOUND_GATE_CONTROLS05.json` retains complete authored checker inputs, source fragments, citation bindings, claim spans and actual pipeline checks. Its SHA-256 is `58ff7275e06f2bec4f4bae8ed173fbfe74b212726896d8acea36c359dd848eb9`.

A real affected checker regression and independent review of the actual selected source union remain necessary. These controls provide no live semantic-accuracy result, native publication, Send-to-full-DOM timing, RAG quality gain, human gold score or p95 measurement.
