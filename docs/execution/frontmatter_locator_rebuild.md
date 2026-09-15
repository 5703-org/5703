# Versioned correction of frontmatter section labels

The read-only audit found 18 chunks in the original four-book release whose section string was `PDF physical page 1` although their independently stored physical pages were 3–6. The affected counts are Anatomy 5, Biology 4, Chemistry 4 and Concepts 5. All 24 prefix source units on pages 1–6 used this synthetic label; the eight cover/blank units on pages 1/2 were already explicitly excluded. Exact chunk IDs, physical pages, original source spans and actual PDF outline entries are recorded in `evidence/openstax/frontmatter-section-audit.json`.

The PDFs contain no bookmark destinations on pages 1–6. Their first actual bookmark is `Contents` on physical page 7. The label originated in `split_bookmarked_page`: its fallback for an unbookmarked page was returned as the carried section state, so it survived onto subsequent unbookmarked pages. It was not a publisher-supplied bookmark title. Native source text, raw PDFs and the separately stored physical-page arrays were unaffected.

Parser revision `pypdf_bookmarks_v5` keeps physical-page fallback labels local to each page. Only actual bookmark scope is carried forward. The current processing service passes each run's recorded parser revision into the parser; explicit v4 execution retains the prior carry behavior, enabling truthful historical reproduction. Neither historical processing rows nor release manifests are edited.

Verification includes a real authored four-page PDF with an unbookmarked prefix and a subsequent Contents bookmark, preservation of all raw/cleaned bytes, actual physical positions and v4 output. The focused parser/publisher/PostgreSQL suite passed 37 tests; 19 source-recovery guard tests also passed. Logs are `evidence/openstax/parser-v5-tests-corrected-command.log` and `parser-v5-recovery-guards.log`. The initial invocation with a nonexistent test filename remains separately recorded; it did not execute tests. A further direct comparison against the first seven physical pages of all four original PDFs verified 28 pages: corrected page-local sections, identical raw segments and identical warnings (`evidence/openstax/v5/actual-prefix-verification.json`). This prefix check is not a full-book validation claim.

`scripts/dev/reprocess_frontmatter_v5.py plan` froze a separate rebuild plan in `evidence/openstax/v5/processing-plan.json`. Its plan hash is `1044bf072dc0bcceb1b1174a50ad0a1a022228966202995a5dfdad2683c5c966`. For each of the four existing original document versions, the proposed configuration differs only in `parser_revision`; all source-specific page reviews, exclusions, publisher descriptions, OCR transcripts and embedding parameters remain pinned. The existing `evidence/openstax/processing-registry.json` is preserved.

After the worker has loaded v5, the explicit `queue` action creates new processing runs and saves their identities under the separate v5 registry. Its `status` action exports immutable per-book quality reports and actual before/after source-content and chunk-span differences. It performs no release activation. Final corpus publication requires all four runs to pass their source gates, full-page/chunk/token verification and a newly validated release; historical releases remain available with their original identities.


## Completed processing and separate release build

All four v5 processing jobs completed successfully. The separate registry contains release configuration `95f05cbe-705b-4623-84e5-ccc7567f33eb`, pinned by `configs/corpus/e5_cuda_v5.json` and its recorded SHA-256. The resulting chunk counts are Anatomy 3,281, Biology 3,534, Chemistry 2,373 and Concepts 1,406: **10,594 total**.

The actual before/after diff accounts for all 5,541 source units: no raw text, cleaned text, issue, quality or unit-membership changes; only 20 section fields on physical pages 2–6 changed. All 10,566 body chunks retain exact text and source-span identities. The 18 old frontmatter chunks become 28 page-separated chunks. There remain zero blocked units, 73 previously reviewed exclusions and 15 supplemented native units. `evidence/openstax/v5/processing-diff-summary.json` and the four complete per-book diffs retain this evidence.

The replacement release build is `4f11bd70-a486-4d16-b216-78cfe499530a`, job `f20da313-b1c8-449e-acd8-d08fb9ff38b2`. Its registration record is `evidence/openstax/v5/release-build.json`. The build utility does not activate it; final source/retrieval validation and publication are separately recorded.


The replacement build completed and validated all 10,594 vectors. `evidence/openstax/v5/release-build-completion.json` records the successful worker state, full immutable manifest and unchanged active pointer at that observation. The build reported 10,574 cache-hit chunk insertions; this count includes duplicate-input reuse within a build. A separate actual PostgreSQL comparison of every unchanged body chunk pair confirmed **10,566 exact IEEE754 float32 vector matches** across v4 and v5. New chunk IDs did not alter reused vector values.


Root completed and published the replacement after `evidence/openstax/v5/formal-source-validation.json` passed: all 4,638 physical pages and 10,594 chunks, actual maximum body/full-input tokens 320/353, and a fixed 50-item sample reconstructing original source text on 63 pages. The separate 15-query retrieval proof also passed. Publication makes v5 the current corpus while preserving all original v4 releases, snapshots and diagnostic identities.
