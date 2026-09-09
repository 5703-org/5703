# Official OpenStax PDF source inspection

Inspection date: 8 September 2026. This is an agent review of source identity, embedded terms, page layout and extraction risks. It is not an independent human scientific review or a claim that every equation and diagram in the books has been transcribed correctly.

All four original files were independently hashed again after inspection and match their acquisition records. No original PDF was edited. This review did not process, exclude, publish or change database content. The authoritative machine report is [pdf-source-inspection.json](../../evidence/openstax/pdf-source-inspection.json); exact low-text page decisions are in [pdf-low-text-decisions.json](../../evidence/openstax/pdf-low-text-decisions.json).

## Source identity and embedded terms

| Book | Original publication year printed in PDF | Physical PDF pages | Printed Preface 1 occurs at physical page | Digital ISBN |
| --- | ---: | ---: | ---: | --- |
| Anatomy and Physiology 2e | 2022 | 1,347 | 17 | 978-1-951693-42-8 |
| Biology 2e | 2018 | 1,475 | 21 | 978-1-947172-52-4 |
| Chemistry 2e | 2019 | 1,203 | 15 | 978-1-947172-61-6 |
| Concepts of Biology | 2013 | 613 | 15 | 978-1-947172-03-6 |

Each book has its title/edition page at physical page 3 and its copyright/license page at physical page 4. All four acquired editions state ©2026 Rice University and identify the content license as **CC BY-NC-SA 4.0**. The short embedded excerpt is: “Attribution Non-Commercial ShareAlike 4.0 International License (CC BY-NC-SA 4.0).” The requested attribution is “Access for free at openstax.org.” The page describes noncommercial use, the same type of license for adaptations, attribution on distributed page views/printed pages, and exceptions for listed trademarks, logos and covers. These are observations of the supplied source wording, not a new legal interpretation. The original publication year must not be confused with the current copyright or acquisition date.

| Official source | Acquisition record | License-page rendering |
| --- | --- | --- |
| [Anatomy and Physiology 2e](https://assets.openstax.org/oscms-prodcms/media/documents/anatomy-and-physiology-2e_-_WEB.pdf) | [Acquisition](../../evidence/openstax/anatomy-and-physiology-2e-acquisition.json) | [Physical 4](../../evidence/openstax/inspection/anatomy-and-physiology-2e/physical-0004.png) |
| [Biology 2e](https://assets.openstax.org/oscms-prodcms/media/documents/Biology-2e_-_WEB.pdf) | [Acquisition](../../evidence/openstax/biology-2e-acquisition.json) | [Physical 4](../../evidence/openstax/inspection/biology-2e/physical-0004.png) |
| [Chemistry 2e](https://assets.openstax.org/oscms-prodcms/media/documents/chemistry-2e_-_WEB.pdf) | [Acquisition](../../evidence/openstax/chemistry-2e-acquisition.json) | [Physical 4](../../evidence/openstax/inspection/chemistry-2e/physical-0004.png) |
| [Concepts of Biology](https://assets.openstax.org/oscms-prodcms/media/documents/Concepts-Biology_-_WEB.pdf) | [Acquisition](../../evidence/openstax/concepts-biology-acquisition.json) | [Physical 4](../../evidence/openstax/inspection/concepts-biology/physical-0004.png) |

Concepts of Biology independently rehashed to `da0ffc8585e172f04eb0abb08949087baf85cc229ef2736ef06e5aa17094b1f6`, the same identity recorded for the historical pilot. Its original quarantined physical pages 1 and 2 are now visually accounted for: page 1 is the designed cover; page 2 is white and blank. The same cover/blank distinction was observed for pages 1 and 2 of the other three books. Each recommendation has its own PNG and reason; no blanket rule excludes all low-text pages.

## Physical and printed page numbers

All references in the decisions use **one-based physical PDF pages**. Inspected numbered body pages have offsets of 16 (Anatomy), 20 (Biology), and 14 (Chemistry and Concepts). Thus Chemistry physical 189 visibly bears printed 175. An offset must not fabricate a printed label on an unnumbered cover, frontmatter page or chapter opener. For example, Concepts physical 131 is the photosynthesis opener; printed 117 is inferred from the TOC/offset, while the opener itself has no visible page number.

Native frontmatter text identifies TOC ranges as Anatomy physical 7–16, Biology 7–20, Chemistry 7–13 and Concepts 7–13. The first TOC page of each was viewed; selected continuation pages were also inspected. Target numbers in the TOC are printed page references, not physical positions or evidence that a body section has begun.

Anatomy [physical 13](../../evidence/openstax/inspection/anatomy-and-physiology-2e/physical-0013.png) visibly lists chapters 20–22 with targets 833, 917 and 973. The initial parser's carried section `19.5 Development of the Heart 821` on this page is therefore invalid body metadata. Actual Anatomy [physical 23](../../evidence/openstax/inspection/anatomy-and-physiology-2e/physical-0023.png) is a chapter opener with a title, photograph, objectives and introduction. Concepts [physical 131](../../evidence/openstax/inspection/concepts-biology/physical-0131.png) contains Chapter Outline entries before the actual section heading; outlines must not advance body section state prematurely.

## Exhaustive low-text screening

Native `pypdf.extract_text()` was run on every one of the **4,638 physical pages**. Pages with fewer than 100 stripped characters were flagged. No extraction exceptions occurred in that scan. All **91 flagged pages** were rendered with Poppler and visually screened; **83** are beyond cover/blank pages 1 and 2. Counts establish text availability, not scientific accuracy or whole-book completeness.

| Classification | Pages | Decision |
| --- | ---: | --- |
| Designed covers | 4 | Eligible for explicit source-preserving exclusion |
| Completely blank physical page 2 | 4 | Eligible for explicit exclusion |
| Blank body with running furniture only | 65 | Eligible for explicit page-specific exclusion |
| Substantive visual material with little native text | 13 | Retain; flag missing visual text and relationships |
| Short genuine text or index entries | 5 | Retain native text |

The JSON enumerates all 91 physical pages, their exact native text/count, category, reason, printed label, PDF hash and review PNG. Its `exclusion_applied` value is false: these are reviewed recommendations for the processing owner. Contact sheets and individual rendered pages remain under [inspection](../../evidence/openstax/inspection/).

The substantive visual pages are:

| Book | Physical pages | Observed material |
| --- | --- | --- |
| Anatomy and Physiology 2e | 604, 756, 935 | Historical portrait; blood-cell comparison table; labeled lymphatic-system diagram |
| Biology 2e | 1453, 1455 | Periodic table; geological time clock |
| Chemistry 2e | 17, 475, 1008, 1071, 1079, 1160 | Science illustration panels; six gas plots; functional-group table; periodic table; quadratic graph/table; carbon phase diagrams |
| Concepts of Biology | 601, 603 | Periodic table; geological time clock |

The five short but valid text pages are Anatomy 1347 (index), Biology 201 and 616 (continuations), and Chemistry 319 and 971 (exercise text). They are not blank-page exclusions.

## Difficult layouts and demonstrated losses

Chemistry [physical 17](../../evidence/openstax/inspection/chemistry-2e/physical-0017.png), printed Preface 3, contains Rutherford scattering labels, HCl/water molecular panels and five labeled d orbitals. Native extraction returns only nine characters, `Preface 3`. The page must never be described as empty or excluded as blank.

Chemistry [physical 189](../../evidence/openstax/inspection/chemistry-2e/physical-0189.png), printed 175, visibly contains displayed redox equations and a worked-exercise answer. Both the PDFium inspection text and the [initial pypdf pipeline text](../../evidence/openstax/inspection/chemistry-2e/physical-0189-pipeline-native.txt) omit those displayed equations, leaving `Answer:` without its formula while nearby prose and a charge/atom table survive. This page exceeds the low-text threshold. It demonstrates why a successful text extraction or large character count cannot certify formula completeness.

Biology [physical 229](../../evidence/openstax/inspection/biology-2e/physical-0229.png), printed 209, contains a glycolysis pathway with molecular labels and arrows beyond the caption/prose. Anatomy [physical 1210](../../evidence/openstax/inspection/anatomy-and-physiology-2e/physical-1210.png), printed 1194, contains a thirst-regulation flowchart whose causal arrows and internal boxes are not reproduced by native body text. Concepts [physical 141](../../evidence/openstax/inspection/concepts-biology/physical-0141.png), printed 127, has the same general problem for a Calvin-cycle diagram. Those are observed samples, not an enumeration of all missing illustrations.

Anatomy [physical 17](../../evidence/openstax/inspection/anatomy-and-physiology-2e/physical-0017.png) establishes a two-column preface layout. Anatomy physical 861 and 1012 and Biology physical 225 each contain a section transition partway through a page. Running headers may name the later section before earlier-section text has finished. A parser must distinguish running furniture, TOC/outline entries, captions, callouts and actual heading blocks, while preserving physical locators and reading order. This report does not claim a demonstrated column-order failure from the preface sample alone.

## Publisher alternatives and remaining work

The requested Chemistry web pages were acquired as immutable HTML with URL, timestamps, byte size and hashes. [chemistry-additional-supplements.json](../../evidence/openstax/chemistry-additional-supplements.json) keeps exact alternatives, image resource IDs, source-file hashes, PDF page/hash linkage, matching PNGs and rejected observations. Source bytes are also copied by content hash to the configured local storage supplements directory. No supplement was attached to a processing run by this inspection task.

Only the graph alternative for physical 1079 was accepted as a bounded match: it agrees with the visible title, axis extents and four plotted points. The five rejected candidate descriptions cover four pages: physical 475 calls the PDF's Z axes “Moles” and adds an absent condition; physical 1008 names the ether example “ethanal” instead of the visible “diethyl ether”; physical 1071 gives only a generic layout summary and differs on legend color; physical 1160 calls carbon phases water and describes the near-vertical boundary with the wrong slope direction. The functional-group table is an image in HTML, not a native HTML table. Rejected source text was not silently repaired or admitted as exact extraction.

Separate reviewed PDF OCR was prepared for the initial 13 substantive low-text pages. Its raw output, rendering, model/runtime identity, exact corrections, reviewed transcription and hashes remain separately attributable. OCR is not considered complete merely because it produces words. Dense element tables, superscripts, charges, orbitals, arrows and graph relationships require visual checks. Chemistry physical 189 and other high-text scientific pages remain outside that initial 13-page OCR scope; no all-book equation/diagram fidelity claim is supported by this bounded review.

## Follow-up OCR review and detector scope

The later parser check examines residual body text after furniture handling and flagged two additional substantive pages: Anatomy physical 470 and Chemistry physical 1195. Their original native character counts were 104 and 125, respectively, so they were outside the first `<100` whole-page scan. This expands the pipeline's targeted supplement review from 13 to 15 pages without changing the earlier measurement of 91 flagged pages. Anatomy 470 is reviewed separately by the processing owner. The source audit's original counts remain traceable instead of being retroactively recast.

Seven Chemistry source transcriptions are now saved under [transcriptions](../../evidence/openstax/transcriptions/), for physical pages 17, 475, 1008, 1071, 1079, 1160 and 1195. All raw OCR remains unchanged. Each reviewed JSON states `agent_source_verified` only for its included text, records precise repairs and cites the original 300-DPI rendering. Page 1071 includes 118 individually checked atomic-number, symbol, printed-mass and name rows; all source brackets and displayed precision are retained. Page 1008 records the ten functional-group rows and visible electron-dot notation. Source 1195 preserves the visible continuation sentence and answer 61, including both multiplication signs and superscript exponents: `7.64 × 10⁹ Bq` and `2.06 × 10⁻² Ci`.

Editorial grouping, linear bond notation and table separators are marked explicitly. These transcriptions do not invent curve coordinates, hidden values, scientific interpretations or missing prior-page context. Colored cells, molecular geometry, shading and other graphical semantics remain available in the original PNG/PDF. No independent human scientific review is claimed. Final attachment, source completeness gates and release state are recorded by the processing owner's pipeline evidence, separately from this inspection.

A second agent reviewed all seven Chemistry transcriptions against the source renderings, including the 118 periodic cells and ten functional-group rows, and reported no concrete mismatch in the included content. The [second-agent review](../../evidence/openstax/transcriptions/chemistry-independent-review.json) preserves transcript/source hashes and its scope limits. This is additional agent verification, not human scientific approval.

The reusable inspection helpers only read original PDFs and save derived audit evidence. Their outputs distinguish complete page accounting from incomplete scientific extraction. The frontend and browser acceptance retake remains separate from this source audit and is waiting on the validated real-corpus baseline.
