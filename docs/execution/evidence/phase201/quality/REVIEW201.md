The fixed five-question set has 4/5 core-correct, complete OFF deliveries and 2/5 ON deliveries. Four cells failed publication and remain in the ten-cell denominator. Strictly clean means no identified inaccurate extra factual statement, alongside a correct and complete core answer; it is not a numeric quality score or exhaustive correctness proof.

| Cell | Published/core complete | Strictly clean | Complete visible answer | Finding |
| --- | --- | --- | --- | --- |
| N1 OFF | Yes | No: minor precision | 6.0608 s | Correct isotope definition and Mg example; absolute chemical identity repeats the submitted textbook wording. |
| N1 ON | Yes | No: minor precision | 11.6132 s | Same issue remains despite native CHECK passed. |
| N2 OFF | No | Not assessable | — | ASSERTION_COMPLETE_CLAIM_REQUIRED; no published answer. |
| N2 ON | No | Not assessable | — | Same validation failure before CHECK; no published answer. |
| N3 OFF | Yes | No: limited-scope precision | 4.9811 s | All three RNA roles correct; each-codon statement omits the sense/stop distinction in both full and short answer. |
| N3 ON | No | Not assessable | — | Checker evidence array length 9 exceeds its maximum 8; no answer published. |
| N4 OFF | Yes | Yes | 4.9626 s | Correct conversions, arithmetic and 0.200 mol/L to three significant figures. |
| N4 ON | No | Not assessable | — | CHECK_DERIVATION_INVALID / body_ok false; no published answer. This alone does not establish an incorrect unpublished calculation. |
| N5 OFF | Yes | Yes | 3.4312 s | Correct Moon-phase/eclipses explanation; zero RAG, evidence and citations. |
| N5 ON | Yes | Yes | 10.3628 s | Correct general-knowledge explanation; native passed does not turn it into textbook authority. |

All five cells remain in each mode denominator. OFF has 4/5 core-complete deliveries within ten seconds, including 2/5 strictly clean deliveries within ten seconds. ON has 2/5 core-complete deliveries and 1/5 strictly clean delivery; neither published ON answer meets ten seconds. Combined, strict-clean and within-ten-second delivery is 2/10. Failed cells have null successful-answer latency. These are saved browser observations, not new measurements or a causal comparison from a representative benchmark.

The four published textbook responses are faithful to their actually submitted evidence. Faithful citation does not establish scientific truth. N1's chemical-identity wording comes from Chemistry 2e 2.2 (PDF p82). Isotope substitution can change kinetics and equilibria, so very similar chemical behavior is a better generalization. This is a minor extra precision issue, not an error in the requested isotope definition. The independent counterexamples are system-specific and do not imply a large effect for every isotope or directly measure the listed magnesium isotopes. [Original deuteration study](https://pubmed.ncbi.nlm.nih.gov/22190693/), [original equilibrium-isotope study](https://pubs.aip.org/aip/jcp/article/138/1/014112/191928/Efficient-methods-and-practical-guidelines-for).

N3's unqualified all-codons statement is already present in the cited Biology 2e 3.5 excerpt (PDF p111); no selected submitted passage explains stop codons. The answer did not omit an existing qualifier from that excerpt. The standard code includes termination codons, and the complete book explains termination separately. This is a limited-scope precision issue; the requested mRNA, tRNA and rRNA roles are complete. [NCBI standard code](https://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi#SG1), [OpenStax translation/termination](https://openstax.org/books/biology-2e/pages/15-5-ribosomes-and-protein-synthesis).

N4's synthetic numbers are problem inputs; the textbook supports the mole/molarity relationships, while unit cancellation and arithmetic supply the derived answer. Its result need not occur verbatim in a source passage. [OpenStax Molarity](https://openstax.org/books/chemistry-2e/pages/3-3-molarity). N5 appropriately has no citations and retains model_general_knowledge_unverified provenance; its science agrees with the reviewer-only NASA references. [Moon phases](https://science.nasa.gov/moon/moon-phases/), [lunar eclipses](https://science.nasa.gov/moon/eclipses/).

The JSON binds full published responses, answer/short/citation hashes, actual GEN-wire evidence, source locators/fragments and all ten saved browser/native records. No failed raw draft was read or graded as delivered content. Both new source-wording flags remain PENDING_SCIENTIFIC_REVIEW with no human approval. The earlier RBC source-pending files remain byte-identical. No corpus, DB, runtime, model/evaluator call or rating registry was changed.
