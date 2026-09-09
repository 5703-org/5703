# Real OpenStax corpus execution report

This report is generated from current PostgreSQL counts and the linked source, retrieval and activation evidence. Only answer generation remains mock. Counts are units unless explicitly marked pages or chunks; unresolved blocking units and retained historical issue codes are different quantities.

Observed: 2026-09-08T08:53:22.826963+00:00. Active release: `4f11bd70-a486-4d16-b216-78cfe499530a`. Scope owner: `sources/COMP5703/tut5/HongleYang/WEEK4_SUMMARY_AND_WEEK5_PLAN.md`, section 1.1, `cs30_openstax_v0.2`; all four full PDFs.

| Book | Physical pages | Ready units | Excluded units | Recovered originals | Blocking units | Chunks / real vectors | Dimension |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Anatomy and Physiology 2e | 1347 | 1575 | 15 | 4 | 0 | 3281 / 3281 | 384 |
| Biology 2e | 1475 | 1803 | 18 | 2 | 0 | 3534 / 3534 | 384 |
| Chemistry 2e | 1203 | 1338 | 24 | 7 | 0 | 2373 / 2373 | 384 |
| Concepts of Biology | 613 | 737 | 16 | 2 | 0 | 1406 / 1406 | 384 |

## Shared embedding, storage and validation

The actual model is `intfloat/e5-small-v2`, fixed revision `ffb93f3bd4047442299a41ebb6fa998a38507c52`, with the tokenizer from the same revision. Query/passages use their E5 prefixes and normalized 384-dimensional vectors. CUDA execution used the local RTX 5070 Ti. The 512-token model window is enforced: maximum measured full input was 353 tokens; target body 320, configured cap 448, overlap 48. The exact release configuration in `evidence/openstax/v5/release-build.json`, `requirements-embeddings.lock` and `evidence/corpus/e5_download.json` pin the configuration and files.

Database: PostgreSQL at `127.0.0.1:55432/learning`; pgvector 0.8.6. Docker volume `cs30-learning_pgdata` is mounted at `/var/lib/postgresql/data`; Docker's volume location is `/var/lib/docker/volumes/cs30-learning_pgdata/_data`. This Linux path belongs to the local Docker engine. Text/source lineage is in `source_units`/`chunks`, vectors in `release_chunks`, and the publication pointer in `active_corpus`. Immutable original and recovery files are under `E:/5703/learning-assistant/artifacts/storage`.

The formal source check covers every original hash, page accounting, chunk hash/span, embedding input and vector relationship. It re-extracted 63 original PDF pages for 50 deterministic chunk samples, including every recovered page. [Formal check](../../evidence/openstax/v5/formal-source-validation-summary.json), [full report](../../evidence/openstax/v5/formal-source-validation.json), [all real queries](../../evidence/openstax/v5/retrieval-verification.json), [activation and unchanged-history proof](../../evidence/openstax/v5/publication.json). The earlier query-verifier metadata failure is retained in [initial attempt](../../evidence/openstax/retrieval-before-fix.json).

## Anatomy and Physiology 2e

Edition identity: Anatomy and Physiology 2e; original publication 2022-04-20, digital ISBN `978-1-951693-42-8`. The actual downloaded PDF is pinned by hash and acquisition time, rather than an invented revision date. Acquired 2026-09-08T07:19:42.937317+00:00; HTTP Last-Modified: Mon, 20 Apr 2026 22:32:36 GMT. Full physical pages 1–1347 were processed, including front matter, exercises and appendices.

[Official PDF](https://assets.openstax.org/oscms-prodcms/media/documents/anatomy-and-physiology-2e_-_WEB.pdf) · [Official catalog](https://openstax.org/apps/cms/api/v2/pages/?type=books.Book&slug=anatomy-and-physiology-2e&fields=*) · [License](https://creativecommons.org/licenses/by-nc-sa/4.0/). Embedded physical page 4 states ©2026 Rice University and CC BY-NC-SA 4.0. Preserve attribution and applicable license/trademark notices; the original publication year and current PDF copyright year are distinct.

Original: `E:/5703/learning-assistant/artifacts/openstax/originals/anatomy-and-physiology-2e-aa2e577b2083c343f4d57b38f00dd935dd2d98befdb38c0f368d72d636d0ff46.pdf` (476,335,014 bytes). Registered storage: `E:/5703/learning-assistant/artifacts/storage/originals/aa2e577b2083c343f4d57b38f00dd935dd2d98befdb38c0f368d72d636d0ff46.pdf`. SHA-256: `aa2e577b2083c343f4d57b38f00dd935dd2d98befdb38c0f368d72d636d0ff46`.

Source version `9c4407ea-5c75-4d39-9eb8-8864f0c4ad57`; processing run `45a52e51-a625-47b7-813e-59ad16a5f492`; release `4f11bd70-a486-4d16-b216-78cfe499530a`. 1594 total units: 1575 ready, 15 explicitly excluded, 4 originals retained with recovery linked, 0 unresolved blockers. 3281 chunks and 3281 real 384-dimensional vectors.

Exclusion reasons/counts: `{"cover_art": 1, "blank_page": 1, "furniture_only": 13}`. Recovered physical pages: 470, 604, 756, 935. [Full page/unit decisions](../../evidence/openstax/v5/anatomy-and-physiology-2e-quality.json) preserve initial issues, exact reasons and source hashes; historical blocked attempts are not rewritten.

Actual query: **What are the functions of erythrocytes, leukocytes and platelets?** Rank 1, score 0.909444. Chapter/section: Chapter 18 The Cardiovascular System: Blood / 18.4 Leukocytes and Platelets; physical PDF pages 763; chunk `c3017c5ce14a408a93b21ba6e41291d45059`; text hash `b05db4eeddbf88e7333c49887feeddf138244abc784977f9a67a3d46a7db51d4`.

Exact source excerpt:

> 18.4 Leukocytes and Platelets LEARNING OBJECTIVES By the end of this section, you will be able to: • Describe the general characteristics of leukocytes • Classify leukocytes according to their lineage, their main structural features, and their primary functions • Discuss the most common malignancies involving leukocytes • Identify the lineage, basic structure, and function of platelets The leukocyte, commonly known as a white blood cell (or WBC), is a major component of the body’s defenses against disease. Leukocytes protect the body against invading microorganisms and body cells with mutated DNA, and they clean up debris. Platelets are essential for the repair of blood vessels when damage t […]

The complete unabridged hit is in the machine report and query evidence. Full-book image/equation fidelity, independent scientific review and real answer-model evaluation remain unverified.

## Biology 2e

Edition identity: Biology 2e; original publication 2018-03-28, digital ISBN `978-1-947172-52-4`. The actual downloaded PDF is pinned by hash and acquisition time, rather than an invented revision date. Acquired 2026-09-08T07:19:42.944153+00:00; HTTP Last-Modified: Thu, 11 Jun 2026 16:58:17 GMT. Full physical pages 1–1475 were processed, including front matter, exercises and appendices.

[Official PDF](https://assets.openstax.org/oscms-prodcms/media/documents/Biology-2e_-_WEB.pdf) · [Official catalog](https://openstax.org/apps/cms/api/v2/pages/?type=books.Book&slug=biology-2e&fields=*) · [License](https://creativecommons.org/licenses/by-nc-sa/4.0/). Embedded physical page 4 states ©2026 Rice University and CC BY-NC-SA 4.0. Preserve attribution and applicable license/trademark notices; the original publication year and current PDF copyright year are distinct.

Original: `E:/5703/learning-assistant/artifacts/openstax/originals/biology-2e-4d1f413fd779f114838cdaeab7859dcb2922ca7529230d3bfd7d36a77b4e27b6.pdf` (401,298,122 bytes). Registered storage: `E:/5703/learning-assistant/artifacts/storage/originals/4d1f413fd779f114838cdaeab7859dcb2922ca7529230d3bfd7d36a77b4e27b6.pdf`. SHA-256: `4d1f413fd779f114838cdaeab7859dcb2922ca7529230d3bfd7d36a77b4e27b6`.

Source version `bb336e9b-ef43-466f-9e65-ca6d1d196c4b`; processing run `242be583-8e03-448f-8009-9db23179fdb9`; release `4f11bd70-a486-4d16-b216-78cfe499530a`. 1823 total units: 1803 ready, 18 explicitly excluded, 2 originals retained with recovery linked, 0 unresolved blockers. 3534 chunks and 3534 real 384-dimensional vectors.

Exclusion reasons/counts: `{"cover_art": 1, "blank_page": 1, "furniture_only": 16}`. Recovered physical pages: 1453, 1455. [Full page/unit decisions](../../evidence/openstax/v5/biology-2e-quality.json) preserve initial issues, exact reasons and source hashes; historical blocked attempts are not rewritten.

Actual query: **How does negative feedback maintain homeostasis?** Rank 1, score 0.901460. Chapter/section: Chapter 33 The Animal Body: Basic Form and Function / 33.3 Homeostasis; physical PDF pages 988; chunk `4728394426b1887680c0d27417d2bfa84d6b`; text hash `59330c52678997ad81fe99c72e9eb2ca4a9b2880d22335cb97e657294bd9d2b9`.

Exact source excerpt:

> is maintained by negative feedback loops. Positive feedback loops actually push the organism further out of homeostasis, but may be necessary for life to occur. Homeostasis is controlled by the nervous and endocrine system of mammals. Negative Feedback Mechanisms Any homeostatic process that changes the direction of the stimulus is a negative feedback loop. It may either increase or decrease the stimulus, but the stimulus is not allowed to continue as it did before the receptor sensed it. In other words, if a level is too high, the body does something to bring it down, and conversely, if a level is too low, the body does something to make it go up. Hence the term negative feedback. An exampl […]

The complete unabridged hit is in the machine report and query evidence. Full-book image/equation fidelity, independent scientific review and real answer-model evaluation remain unverified.

## Chemistry 2e

Edition identity: Chemistry 2e; original publication 2019-02-14, digital ISBN `978-1-947172-61-6`. The actual downloaded PDF is pinned by hash and acquisition time, rather than an invented revision date. Acquired 2026-09-08T07:19:36.357653+00:00; HTTP Last-Modified: Wed, 22 Apr 2026 11:41:36 GMT. Full physical pages 1–1203 were processed, including front matter, exercises and appendices.

[Official PDF](https://assets.openstax.org/oscms-prodcms/media/documents/chemistry-2e_-_WEB.pdf) · [Official catalog](https://openstax.org/apps/cms/api/v2/pages/?type=books.Book&slug=chemistry-2e&fields=*) · [License](https://creativecommons.org/licenses/by-nc-sa/4.0/). Embedded physical page 4 states ©2026 Rice University and CC BY-NC-SA 4.0. Preserve attribution and applicable license/trademark notices; the original publication year and current PDF copyright year are distinct.

Original: `E:/5703/learning-assistant/artifacts/openstax/originals/chemistry-2e-fd89db1b8a1fee06b8ad3e8982f4f4b34bde4e93654a4ce28b724f8c0efe98d6.pdf` (217,794,376 bytes). Registered storage: `E:/5703/learning-assistant/artifacts/storage/originals/fd89db1b8a1fee06b8ad3e8982f4f4b34bde4e93654a4ce28b724f8c0efe98d6.pdf`. SHA-256: `fd89db1b8a1fee06b8ad3e8982f4f4b34bde4e93654a4ce28b724f8c0efe98d6`.

Source version `d50e0f43-86dc-4b18-9be5-a6da4407f8d4`; processing run `cc12c354-b6a1-4fa9-a259-5e388cfaf342`; release `4f11bd70-a486-4d16-b216-78cfe499530a`. 1369 total units: 1338 ready, 24 explicitly excluded, 7 originals retained with recovery linked, 0 unresolved blockers. 2373 chunks and 2373 real 384-dimensional vectors.

Exclusion reasons/counts: `{"cover_art": 1, "blank_page": 1, "furniture_only": 22}`. Recovered physical pages: 17, 475, 1008, 1071, 1079, 1160, 1195. [Full page/unit decisions](../../evidence/openstax/v5/chemistry-2e-quality.json) preserve initial issues, exact reasons and source hashes; historical blocked attempts are not rewritten.

Actual query: **How does Le Chatelier's principle predict changes in chemical equilibrium?** Rank 1, score 0.898962. Chapter/section: Chapter 13 Fundamental Equilibrium Concepts / 13.3 Shifting Equilibria: Le Châtelier’s Principle; physical PDF pages 669; chunk `f251ac85a7b109487a067a46e67633d9e7fe`; text hash `1d0eb4d0c45400c72905fc98d518269114efed56e61ee280dc4dea55185f7a4b`.

Exact source excerpt:

> 13.3 Shifting Equilibria: Le Châtelier’s Principle LEARNING OBJECTIVES By the end of this section, you will be able to: • Describe the ways in which an equilibrium system can be stressed • Predict the response of a stressed equilibrium using Le Châtelier’s principle A system at equilibrium is in a state of dynamic balance, with forward and reverse reactions taking place at equal rates. If an equilibrium system is subjected to a change in conditions that affects these reaction rates differently (a stress), then the rates are no longer equal and the system is not at equilibrium. The system will subsequently experience a net reaction in the direction of greater rate (a shift) that will re-estab […]

The complete unabridged hit is in the machine report and query evidence. Full-book image/equation fidelity, independent scientific review and real answer-model evaluation remain unverified.

## Concepts of Biology

Edition identity: Concepts of Biology; original publication 2013-04-25, digital ISBN `978-1-947172-03-6`. The actual downloaded PDF is pinned by hash and acquisition time, rather than an invented revision date. Acquired 2026-09-08T07:19:36.364982+00:00; HTTP Last-Modified: Thu, 11 Jun 2026 17:02:05 GMT. Full physical pages 1–613 were processed, including front matter, exercises and appendices.

[Official PDF](https://assets.openstax.org/oscms-prodcms/media/documents/Concepts-Biology_-_WEB.pdf) · [Official catalog](https://openstax.org/apps/cms/api/v2/pages/?type=books.Book&slug=concepts-biology&fields=*) · [License](https://creativecommons.org/licenses/by-nc-sa/4.0/). Embedded physical page 4 states ©2026 Rice University and CC BY-NC-SA 4.0. Preserve attribution and applicable license/trademark notices; the original publication year and current PDF copyright year are distinct.

Original: `E:/5703/learning-assistant/artifacts/openstax/originals/concepts-biology-da0ffc8585e172f04eb0abb08949087baf85cc229ef2736ef06e5aa17094b1f6.pdf` (185,858,638 bytes). Registered storage: `E:/5703/learning-assistant/artifacts/storage/originals/da0ffc8585e172f04eb0abb08949087baf85cc229ef2736ef06e5aa17094b1f6.pdf`. SHA-256: `da0ffc8585e172f04eb0abb08949087baf85cc229ef2736ef06e5aa17094b1f6`.

Source version `35d45deb-de7f-4194-9ce2-1861ae84434d`; processing run `82fb328d-a383-43c2-a6eb-b91b61d05069`; release `4f11bd70-a486-4d16-b216-78cfe499530a`. 755 total units: 737 ready, 16 explicitly excluded, 2 originals retained with recovery linked, 0 unresolved blockers. 1406 chunks and 1406 real 384-dimensional vectors.

Exclusion reasons/counts: `{"cover_art": 1, "blank_page": 1, "furniture_only": 14}`. Recovered physical pages: 601, 603. [Full page/unit decisions](../../evidence/openstax/v5/concepts-biology-quality.json) preserve initial issues, exact reasons and source hashes; historical blocked attempts are not rewritten.

Actual query: **How does glycolysis produce ATP from glucose?** Rank 1, score 0.917252. Chapter/section: Chapter 4 How Cells Obtain Energy / 4.2 Glycolysis; physical PDF pages 116, 117; chunk `4063e1f4134e00d1c5cf11da97385b360ea4`; text hash `bc1a1a21995021168d3da4ba5cafdc75b832f3b61ee7029acc978ff316df0a07`.

Exact source excerpt:

> results in a high-energy bond. Phosphate groups are negatively charged and thus repel one another when they are arranged in series, as they are in ADP and ATP. This repulsion makes the ADP and ATP molecules inherently unstable. The release of one or two phosphate groups from ATP, a process called hydrolysis, releases energy. Glycolysis You have read that nearly all of the energy used by living things comes to them in the bonds of the sugar, glucose.
> 
> Glycolysis is the first step in the breakdown of glucose to extract energy for cell metabolism. Many living organisms carry out glycolysis as part of their metabolism. Glycolysis takes place in the cytoplasm of most prokaryotic and all eukaryoti […]

The complete unabridged hit is in the machine report and query evidence. Full-book image/equation fidelity, independent scientific review and real answer-model evaluation remain unverified.

## Remaining work and honest boundaries

- All 4,638 physical pages are accounted for, but full-book visual relationships, image equations, complete reading order and scientific fidelity have not been independently certified.
- 14 source-reviewed local OCR transcriptions and one exact publisher portrait description resolve 15 low-text source pages. Original issues and rejected alternatives remain visible; agent review is not independent human review.
- Nearest-neighbor candidates are not guaranteed relevant. All 15 scheduled queries, including three unrelated questions, are retained; live answer quality and formal relevance qrels are unverified.
- Answer generation is explicitly mock. No hosted answering model, real answer-effectiveness evaluation or independent human ratings are claimed.
- Actual full-corpus restoration and SciQ acquisition have separate proof. Current browser/API, local delivery and remaining research/device checks are governed by the 108-task and 60-check ledgers, without an overall completion percentage.
