# Supported-answer V5/V8 development pilot — 1 October 2026

Current V5 delivered 2/4 requests; opt-in V8 delivered 3/4. All eight scheduled requests remain in the report. This finite comparison used four exposed development questions and the real product generation service. Delivery records automatic publication acceptance. Human ratings and independent correctness scores are zero.

| Public question | Policy | Delivered | Calls | Audit elapsed (s) | Delivered citations | Final error |
|---|---|---:|---:|---:|---:|---|
| selected_energy_explanation | typed_joint_v5 | Yes | 2 | 44.941 | 1 | — |
| selected_energy_explanation | scoped_compact_v8 | No | 3 | 55.883 | 0 | CHECKER_INCONSISTENT |
| enzyme_energy_comparison | typed_joint_v5 | Yes | 4 | 74.012 | 4 | — |
| enzyme_energy_comparison | scoped_compact_v8 | Yes | 2 | 39.331 | 4 | — |
| dna_rna_comparison | typed_joint_v5 | No | 4 | 75.154 | 0 | SEMANTIC_CHECK_FAILED |
| dna_rna_comparison | scoped_compact_v8 | Yes | 2 | 40.556 | 10 | — |
| ideal_gas_units_conditions | typed_joint_v5 | No | 4 | 79.391 | 0 | SEMANTIC_CHECK_FAILED |
| ideal_gas_units_conditions | scoped_compact_v8 | Yes | 4 | 79.589 | 3 | — |

The V8 selected-passage request retained `COMPACT_UNEXPECTED_CITATION_FOR_BASIS` after the bounded checker-contract correction and ended with `CHECKER_INCONSISTENT`. The V5 DNA/RNA request retained `ACTUAL_CITATION_FRAGMENT_INVALID`. V5 gas-law checks retained `CHECK_LIMITATION_BASIS_INVALID` and `UNEXPECTED_CITATION_FOR_BASIS`. Error families, contract issues, semantic negatives and publication-validation issues remain separate in the JSON. Their names alone do not establish whether a rejected draft was factually correct.

V8 enzyme and DNA/RNA requests delivered after generation and one joint check. V8 gas-law delivery followed one semantic repair and recheck. The gas case's final model material-sufficiency label remained partial; the final completeness decision refers to the supported response with its stated limitations. Independent source-support review remains required.

The per-request ceiling was four calls and 180 active seconds. Both roles used `deepseek-flash`, a 32,768-token configured window, temperature 0 and JSON-object output; generation reserved 1,024 output tokens and checking reserved 4,096. DeepSeek documents the alias as DeepSeek-V4.1-Flash. The remote checkpoint is not pinned. The local tokenizer name and revision are recorded separately in the JSON.

Each question and actual submitted source location follows. PDF pages are source PDF page indices recorded by the pipeline.

- **selected_energy_explanation**: In plain language, explain how the selected passage connects sunlight with chemical energy.
  - Concepts of Biology; Chapter 5 Photosynthesis / 5.2 The Light-Dependent Reactions of Photosynthesis; PDF pages 136.
  - Concepts of Biology; Chapter 5 Photosynthesis / 5.2 The Light-Dependent Reactions of Photosynthesis; PDF pages 136, 137.
- **enzyme_energy_comparison**: Compare the effect of a catalyst on activation energy with its effect on the free-energy difference between reactants and products.
  - Biology 2e; Chapter 6 Metabolism / 6.2 Potential, Kinetic, Free, and Activation Energy; PDF pages 185.
  - Biology 2e; Chapter 6 Metabolism / 6.2 Potential, Kinetic, Free, and Activation Energy; PDF pages 187.
  - Biology 2e; Chapter 6 Metabolism / 6.5 Enzymes; PDF pages 194, 195.
  - Biology 2e; Chapter 6 Metabolism / Chapter Summary; PDF pages 202, 203.
  - Biology 2e; Chapter 6 Metabolism / Review Questions; PDF pages 204.
  - Chemistry 2e; Chapter 12 Kinetics / 12.5 Collision Theory; PDF pages 625, 626.
  - Chemistry 2e; Chapter 12 Kinetics / 12.7 Catalysis; PDF pages 633.
  - Chemistry 2e; Chapter 12 Kinetics / 12.7 Catalysis; PDF pages 633, 634.
  - Chemistry 2e; Chapter 12 Kinetics / 12.7 Catalysis; PDF pages 634, 635.
  - Chemistry 2e; Chapter 13 Fundamental Equilibrium Concepts / 13.3 Shifting Equilibria: Le Châtelier’s Principle; PDF pages 673.
  - Chemistry 2e; Chapter 16 Thermodynamics / 16.4 Free Energy; PDF pages 794.
  - Chemistry 2e; Chapter 16 Thermodynamics / 16.4 Free Energy; PDF pages 803, 804.
  - Chemistry 2e; Chapter 16 Thermodynamics / 16.4 Free Energy; PDF pages 804, 805.
  - Concepts of Biology; Chapter 4 How Cells Obtain Energy / 4.1 Energy and Metabolism; PDF pages 110.
  - Concepts of Biology; Chapter 4 How Cells Obtain Energy / 4.1 Energy and Metabolism; PDF pages 111, 112.
- **dna_rna_comparison**: Compare DNA and RNA in their sugars, nitrogenous bases and usual strand structure. Explain each difference separately.
  - Anatomy and Physiology 2e; Chapter 2 The Chemical Level of Organization / 2.5 Organic Compounds Essential to Human Functioning; PDF pages 90.
  - Anatomy and Physiology 2e; Chapter 2 The Chemical Level of Organization / 2.5 Organic Compounds Essential to Human Functioning; PDF pages 90, 91.
  - Anatomy and Physiology 2e; Chapter 3 The Cellular Level of Organization / Review Questions; PDF pages 142.
  - Biology 2e; Chapter 14 DNA Structure and Function / 14.2 DNA Structure and Sequencing; PDF pages 383, 384.
  - Biology 2e; Chapter 3 Biological Macromolecules / 3.5 Nucleic Acids; PDF pages 108.
  - Biology 2e; Chapter 3 Biological Macromolecules / 3.5 Nucleic Acids; PDF pages 108, 109.
  - Biology 2e; Chapter 3 Biological Macromolecules / 3.5 Nucleic Acids; PDF pages 109, 110.
  - Biology 2e; Chapter 3 Biological Macromolecules / 3.5 Nucleic Acids; PDF pages 110, 111.
  - Biology 2e; Chapter 3 Biological Macromolecules / Review Questions; PDF pages 116.
  - Chemistry 2e; Chapter 20 Organic Chemistry / 20.4 Amines and Amides; PDF pages 1000, 1001.
  - Chemistry 2e; Chapter 20 Organic Chemistry / 20.4 Amines and Amides; PDF pages 1001, 1002.
  - Concepts of Biology; Chapter 2 Chemistry of Life / 2.3 Biological Molecules; PDF pages 64, 65.
  - Concepts of Biology; Chapter 9 Molecular Biology / 9.1 The Structure of DNA; PDF pages 212, 213.
  - Concepts of Biology; Chapter 9 Molecular Biology / 9.1 The Structure of DNA; PDF pages 213, 214.
  - Concepts of Biology; Chapter 9 Molecular Biology / Chapter Summary; PDF pages 234.
- **ideal_gas_units_conditions**: In the ideal gas law PV = nRT, why must temperature be expressed in kelvin, and which pressure and volume units are consistent with R = 8.314 J mol-1 K-1?
  - Chemistry 2e; Chapter 9 Gases / 9.2 Relating Pressure, Volume, Amount, and Temperature: The Ideal Gas Law; PDF pages 428.
  - Chemistry 2e; Chapter 9 Gases / 9.2 Relating Pressure, Volume, Amount, and Temperature: The Ideal Gas Law; PDF pages 431.
  - Chemistry 2e; Chapter 9 Gases / 9.2 Relating Pressure, Volume, Amount, and Temperature: The Ideal Gas Law; PDF pages 431, 432.
  - Chemistry 2e; Chapter 9 Gases / 9.2 Relating Pressure, Volume, Amount, and Temperature: The Ideal Gas Law; PDF pages 434.
  - Chemistry 2e; Chapter 9 Gases / 9.2 Relating Pressure, Volume, Amount, and Temperature: The Ideal Gas Law; PDF pages 436, 437.
  - Chemistry 2e; Chapter 9 Gases / 9.2 Relating Pressure, Volume, Amount, and Temperature: The Ideal Gas Law; PDF pages 437.
  - Chemistry 2e; Chapter 9 Gases / 9.2 Relating Pressure, Volume, Amount, and Temperature: The Ideal Gas Law; PDF pages 437, 438.
  - Chemistry 2e; Chapter 9 Gases / 9.6 Non-Ideal Gas Behavior; PDF pages 461.
  - Chemistry 2e; Chapter 9 Gases / 9.6 Non-Ideal Gas Behavior; PDF pages 462, 463.
  - Chemistry 2e; Chapter 9 Gases / 9.6 Non-Ideal Gas Behavior; PDF pages 463.
  - Chemistry 2e; Chapter 9 Gases / Exercises; PDF pages 476.
  - Chemistry 2e; Chapter 9 Gases / Exercises — Image text transcription; PDF pages 475.
  - Chemistry 2e; Chapter 9 Gases / Key Terms; PDF pages 465.
  - Chemistry 2e; Chapter 9 Gases / Summary; PDF pages 466.

The local audit recorded 25 opener invocations, 25 durable finish records and 25 confirmed nonempty provider replies. Unknown outcomes: 0. Recorded usage: 313,385 input, 27,781 output and 341,166 total tokens; input cache hits 159,744, misses 153,641.

A separate conditional calculation gives USD **0.040193982** for this named sequence at the [published DeepSeek price observation](https://api-docs.deepseek.com/quick_start/pricing/), retrieved between 13:30:51 and 13:30:56 UTC on 1 October 2026: OFF-PEAK USD 0.003/cache-hit input million, 0.15/cache-miss input million and 0.6/output million. No rate-validity interval is asserted. The original terminal receipt preserves null conditional-cost totals, 0 priced calls and 25 unpriced calls. This calculation is separate from invoice reconciliation and the week's total cost.

Request elapsed and adapter latency include audit guard and durable-record overhead. Opener elapsed stops at response-handle return and excludes response-body reading. These are development-audit measurements, not production or model-only latency.

All 65 table fingerprints, the 10,594 active 384-dimensional vectors, four official original files, configuration, environment and frozen 808-file code inventory matched before and after this sequence. Database writes and HTTP authentication actions were zero. The recorded source snapshot identifies this historical candidate even when later code changes exist.

The paired differences describe these four runs only. The fixed-order, exposed development inputs, same-provider generation/checking and absent independent ratings do not support a causal improvement estimate, population correctness rate or confidence interval. Earlier V7 trials remain historical evidence and are not the comparison arm in this run.

Terminal SHA-256: `e68579771494582c8a4fa0a98ef622b223498254f4f52fb4e926594dafc6d681`. Source-snapshot SHA-256: `5bdc2a4b0c7ce15f30b5ed2a367f5dcb1729b22241132f85dac617eb1a06a94b`.
