# Visual V5 full source processing and current unit verification

The integrated V5 producer and consumer processed all four retained official
OpenStax PDFs and prepared a separate, validated candidate bundle. This version
adds bounded native formula context for source review. The current Main unit
suite passed 2,703 cases and two subtests on 879 unchanged gate inputs. Database
integration, real-model grading and teaching trials, scientific content approval
and final delivery retain their separate outstanding checks.

## Current implementation

Seven reviewed files were applied with exact candidate bytes: three replacements
and four additions. Before copies preserve the three replaced files. The previous
905-source/contract cohort retained 902 unaffected inputs. The current source-only
freeze contains 879 gate inputs, 893 public code/contract inputs and 909 unique
inputs. It records source identity and supplies no unified software-gate result.

The native-context module retains the existing formula candidate text and region,
then adds up to two adjacent whole lines on either side from the same native PDF
text block, within a 4,096-glyph limit. It keeps each line's original order,
rounded and raw coordinates, direction, font properties and every native glyph's
character, original box, origin and order. It joins no blocks, columns or pages.
Native characters receive no correction. Zero-width or zero-height native glyph
boxes remain represented with their original coordinates and an explicit count.

Formula context retains its exact V4 anchor identity and source hash. V5 candidate
identities retain V4 and V3 sidecars and original V2 region lineage. Canonical
JSON checks distinguish booleans, integers and floats. Source locators, manifest
counts, fixed configuration, hashes and source-file pins are validated before a
new bundle is written. Context is recomputed against the original PDF during
preparation and again by the database staging consumer before persistence.

Default catalog extraction remains V2. V3 and V4 history retains its original
bytes. V5 is explicitly selected with pymupdf_visual_regions_v5. The existing
catalog detail DTO preserves the complete raw payload; administrator extraction
details can display the added context alongside the original PDF image. Existing
source visibility, independent human review, compare-and-swap and publication
controls remain in effect. V5 requires no database schema migration.

## Actual full-original results

The scan ran from 2026-10-02 22:48:59 UTC to 22:53:55 UTC. Preparation completed
after 33.500 seconds, including original-source checks and the actual Main bundle
consumer. Every physical page was inspected. All 5,543 historical region lineages
were retained; failed pages and unresolved native formula anchors were zero.

| Official book | Physical pages | Candidates | Figures | Table records | Formula contexts | Formula-context glyph records | Zero-extent glyph records |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Anatomy and Physiology 2e | 1,347 | 1,101 | 736 | 153 | 212 | 75,476 | 112 |
| Biology 2e | 1,475 | 1,425 | 1,167 | 78 | 180 | 50,678 | 31 |
| Chemistry 2e | 1,203 | 2,442 | 1,152 | 93 | 1,197 | 209,606 | 297 |
| Concepts of Biology | 613 | 575 | 481 | 15 | 79 | 17,951 | 17 |
| Total | 4,638 | 5,543 | 3,536 | 339 | 1,668 | 353,711 | 457 |

The 339 table records retain 325 rectangular bodies, fourteen linked native
references and 140,420 native table glyph records. Table body contents remain
identical to V4. Across formula contexts, replacement characters, C0/C1 control
characters and corrected characters each total zero. The 457 zero-extent glyph
records occur in 295 contexts. These are recorded native geometry, retained for
review. Adjacent contexts can repeat the same physical glyph; these counts
describe records, not unique PDF characters. Multi-line context occurs in 1,183
candidates. Full native blocks were retained in 682 candidates.

Each book uses its existing official acquisition URL, acquisition date, original
file hash and BY-NC-SA 4.0 license URL. The scan manifest records the original
476,335,014-byte, 401,298,122-byte, 217,794,376-byte and 185,858,638-byte PDFs,
respectively. The [scan manifest](../../artifacts/visual-catalog-staging/current_full_visual_v5_20261003_01/manifest.json)
contains every original path, URL, hash, physical scope and output catalog hash.

The prepared bundle is
artifacts/visual-catalog-staging/native_formula_context_v5_20261003_01.
Its [source manifest](../../artifacts/visual-catalog-staging/native_formula_context_v5_20261003_01/SOURCE_MANIFEST.json)
has SHA-256 8c221742571ae0c3c40fd902da21b70a31e79c0438d891930402472a1feaa47b.
The scan manifest has SHA-256
f8295b835dec2e5d3ed16a0b11d8cfadc6a8807185271dc4c5cc20ff4843c9cb.
The eleven-file implementation freeze has SHA-256
77e41237054fd1279257148fa419966f843fe728d8d42c8eddfa0963e0ad8fad.

## Current verification and remaining acceptance

| Component | Actual result | Acceptance boundary |
| --- | --- | --- |
| Main V5 and retained native-parser tests | 75 passed, zero failures or skips | Included within the full unit population below |
| Current Main unit suite | 2,703 passed and two subtests passed, zero failures or skips | Unit and scripted contracts; database integration remains outstanding |
| Current Python quality | All eight checks passed | Correctness lint, formatting and configured contract typing, including negative controls |
| Independent applied-file audit | All seven hashes, three before copies, ten protected function ASTs and four DTO payloads verified | Application, gate-code and serialization checks |
| Actual four-book scan and preparation | Complete originals, exact parent lineages and source-bound context validated | Mechanical source processing and bundle validation |
| V5 database staging and live API/UI | Waiting for local database recovery | Zero V5 database imports at this checkpoint |
| Scientific, notation and downstream answer quality | Awaiting content assessment and actual independent human review | Zero V5 semantic approvals, answer publications or human scores |
| Current installed release and final packages | Waiting for unified regression and runtime checks | Retained 2 October delivery remains dated to its verified source |

The standalone 75-case result overlaps the full unit suite and is not added to it.
The preceding 875-input checkpoint retains its 196 frontend cases and failed
unified gate after the database outage. The current 879-input source has no new
unified-gate pass. The configured type check covers canonical contracts and typed
consumers; it does not establish strict typing of the entire backend.

The four original pilot pages independently replayed all 1,879 native glyph
records. That developer sample verifies source correspondence. The
[eight-pilot content review](week09-eight-pilot-visual-source-review-20261003.md)
continues to record four missing diagram representations, two incidental prose
glosses, one truncated genuine expression and one complete narrow numerical
example. Added context and pattern flags carry semantic_completeness null,
notation_verified false and answer_evidence_eligible false. They supply review
material; formula classification and scientific completeness need content labels.
The two earlier table transcription proposals and all original human-review
fields retain their pending status.

No new chunk, vector, answer or citation was written by these operations. Original
catalogs, PDFs, saved records and running processes were preserved. Current live
database integrity was not observed during the outage. The latest bounded
read-only check, at 2026-10-02 22:51:07 UTC, timed out after 5.085 and 5.077 seconds
on the two local database targets. An earlier elevated Docker diagnostic returned
HTTP 500; a later explicit API-version diagnostic reached its fifteen-second
limit. The root cause remains undetermined.

The measured source-only delta against the retained 864-source installation is
31 replacements and fifteen additions. No source installation or restart was
performed. Earlier forty-file and forty-two-file execution preparations require
reviewed successors bound to the current source. Real grading and teaching trials
retain zero executions on this candidate.

The first source-freeze artifact write and initial Python-quality attempt hit
local write restrictions. Their failure evidence remains preserved. A reviewed
new-file continuation saved the freeze, and the quality retry passed all eight
checks. The [aggregate current evidence](../../evidence/week09-continuation/20261003/visual-v5-full-source-current-01.json)
binds the exact actual results, source counts, hashes, installation delta and
remaining conditions.

Continue with database recovery, a fresh unified gate, isolated V5 staging and
source-preservation checks, the bounded real grading and QA/A/B/C/D trials,
independent content decisions and current-source installation. Final nine-report
authoring and complete/eight-owner package parity follow those actual results.
