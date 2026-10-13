# Paired RAG 69 independent semantic review

Both retrieval arms explicitly cover 32 of the 38 frozen facts; E0 covers 27. All three arms explicitly cover every required fact in 7 of the 12 questions. These are descriptive, unblinded AI review counts for the already exposed, source-conditioned synthetic DEV cohort. They are not a scientific correctness rate or a claim of general RAG superiority.

| Arm | Explicit frozen facts | Inferred | Missing | Required-fact contradictions | Questions with every fact explicit |
| --- | ---: | ---: | ---: | ---: | ---: |
| E0 | 27/38 | 5 | 6 | 0 | 7/12 |
| E1 | 32/38 | 4 | 2 | 0 | 7/12 |
| HYBRID_R2_MINILM | 32/38 | 3 | 3 | 0 | 7/12 |

RAG supplies additional measurements/calculations in Q01, explicit membrane ion concentrations in Q02, cuticle protection in Q07, and the colloid mechanism in Q10. It still omits surface-wide water uptake in Q07. Every arm omits explicit prophage excision in Q06 even though both retrieval arms receive the relevant passage; the lytic-return outcome is stated but the frozen excision-to-return relation is implicit. E1 states the full unconverted-colloid causal chain in Q10; the hybrid answer leaves the conversion step implicit or incomplete. The retrieval answers in Q11 state salt loss without water loss but leave dilution implicit.

Q03 is a designated-support miss in both retrieval arms. All arms give a reasonable cell-type protein/receptor explanation; E1 leaves the distinct-response outcome implicit. Related retrieved passages describe receptor proteins and signaling cascades, while the precise cell-type differential-expression statement is absent. These observations do not establish a deterministic relationship between a retrieval miss and answer failure.

Q12 is also a designated-support miss in both retrieval arms, and all three answers contain the complete diversity definition. E1 has alternative passages providing species count and relative abundance. The hybrid context has related biodiversity/community material but no complete relative-abundance definition; the correct answer therefore cannot be fully attributed to those supplied passages. The exact alternative chunk IDs and text are preserved in the detailed JSON.

Extras such as the E0 Q06 plasmid/repressor/SOS explanation and E1 UV trigger are source-unverified in this frozen evidence scope, rather than declared false. The E0 Q11 active-transport phrasing also needs a caveat: the source distinguishes thin-limb diffusion from thick-limb active transport. This caveat is separate from its coverage of the three required dilution facts.

The frozen lexical evaluation remains separate and unchanged. Missing source propositions can indicate incomplete coverage of this source without proving that an alternative answer is scientifically wrong. No human gold, calibrated judge, held-out evaluation, API, database, network, or native-page timing is included in this review.

Detailed exact answer excerpts, frozen quote links, current-evidence notes, input/result hashes, and all 114 fact assessments: [independent-semantic-review69.json](./independent-semantic-review69.json).

Review JSON SHA-256: `52e4c70fede905159031bfcb4d290374709483469a36ed0c845486873b8cdf36`. Integration checked 36 answer identities, 112 exact answer evidence excerpts, and 114 frozen fact/quote links.
