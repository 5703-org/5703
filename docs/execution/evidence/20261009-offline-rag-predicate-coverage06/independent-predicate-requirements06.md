# Independent frozen-fragment support requirements

This manifest supplies analyst-authored support-bundle availability labels for one offline comparison of the 13 actual wire-evidence items and 67 preserved fragments. It does not evaluate the historical 20-item retrieval pool, the full corpus, model semantic accuracy, new RAG quality, automated publication success, or human teaching quality. Retained wire order has no retained dense/RRF scores and must remain labelled retained order.

There are two separate dimensions: **10 exact candidate-claim support requirements** and **4 high-level question facets**. The original canonical `requirement_01` remains unchanged. The four analyst facets concern light-to-chemical energy, ATP/NADPH outputs, energy delivery to Calvin reactions at the stroma, and Calvin use of that energy for carbohydrate products. They do not introduce recycling as an extra requested facet; the exact candidate's recycling claim still requires both of its actual citations to contribute. G3P details are scored in the exact claims rather than invented as extra canonical question obligations.

Each machine-readable requirement has exactly `id`, `kind`, and `complete_support_bundles`. The kind is `claim_support` or `question_facet`. A bundle is a conjunction of exact aliases; alternative bundles are disjunctions. The separate audit preserves predicate groups, actual citation-contribution groups, allowed source scopes, and parallel real-fragment-ID bundles. All 67 aliases map to exact retained real fragment identities, evidence/chunk/source-unit/page metadata, text, and SHA256.

| Exact candidate contribution | Complete citation-bound support |
| --- | --- |
| Light-dependent conversion and Calvin sugar assembly | F042 + F043 |
| Generic photosystem/electron-transport conversion | F007, excluding its NADH product assertion |
| PSI second photon and NADPH formation/use | F051 |
| Temporary ATP/NADPH storage and carbohydrate long-term energy storage | F012 |
| ATP/NADPH production and stroma delivery | F036 + F037 |
| Full/empty carrier movement and return, with ev_001 and ev_005 both contributing | F002 + F031 **or** F002 + F003 + F030 |
| ATP/NADPH-driven G3P conversion | F053 |
| G3P can leave and become part of carbohydrate | F054 **and** F055 |
| Calvin stroma location | F037 |
| Short-answer carrier storage/delivery summary | F036 + F037 |

Question-facet alternatives can use different frozen sources because this dimension concerns available knowledge, not the fixed candidate's citations. Every alternative was assessed against the full exact fragments; reasons are recorded in the audit. Source wording need not be lexically identical, and necessary energy-carrier inferences are distinguished from unprovided detailed mechanisms. A different evidence item cannot rescue an exact claim whose displayed citation does not bind it.

The source caveats remain. F007's ATP/NADH product inconsistency is not adopted by the narrow mechanism or facet. F054 and F055 are separate neighboring cross-unit prose with page-layout noise; both are required, and no synthetic merged quote or changed offset is supplied. The F013 facet alternative asserts only named ATP/NADPH products, not its lifespan claims. `complete_block` flags are not entailment certificates, and universal source correctness/title/license/edition provenance is not established here.

Root's pure helper was reviewed and used for meaningful availability controls: selecting all 67 aliases covers the 10 declared claims and 4 facets; selecting none covers none; either F054 or F055 alone fails the paired-link requirement; selecting only ev_001 fails the two-citation recycling requirement; both declared full recycling alternatives satisfy it. These are availability controls using the analyst labels, not independent model-accuracy measurements. An unselected fragment in the original pool never counts.

The manifest and this report are frozen after publication for the comparison runner. No provider, database, native fixture, credential, denied seed field, main repository, actual model log, scientific gate, or label was changed. Old candidate/results and the blocked third-call state remain preserved.
