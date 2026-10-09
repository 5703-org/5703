# Local highlighted-source comparison

Open `highlight_review.html` in a current browser. Select an investigator-prepared JSON file and enter an anonymous participant code. No account, model call, server, external script or network connection is used. All ratings begin blank. Results remain in the browser until the participant downloads them.

The companion compares **the same question, answer, selected claim and source text** in two presentations. One uses plain source paragraphs; the other marks the supplied claim-specific fragments. Source titles, locators, source order and complete text stay identical. The participant sees neutral A/B labels. The visible presence of highlighting makes the physical intervention recognizable; condition names and the analysis mapping are kept in a separate key download.

`highlight_review_input.template.json` is an explicitly authored format example. It contains no measured participant result and must be replaced by real frozen citation-run data. Export one item per selected claim, with the exact delivered answer field and real source/fragment identities. Do not add evaluator answers, support grades or condition names to the participant input.

## Input contract

Top-level fields are `version: highlight_review_input_v1`, `review_version`, frozen unsigned integer `seed`, and `items` (1–1,000). Each item has:

- Unique `id`, `question`, and exact `answer_text`.
- `claim: {claim_id, start, end, text}`. Offsets count Unicode code points in `answer_text`; the exact slice must equal `text`.
- `evidence: [{evidence_id, source_title, locator, text, text_sha256, segments}]` in fixed display order.
- `segments: [{text, highlight, fragment_ids}]`. Their concatenation must equal the full source `text` byte-for-byte after UTF-8 encoding. The source SHA-256 must match. Highlighted segments carry actual selected fragment IDs; every item needs at least one highlight.

The exporter remains responsible for binding these fragments to their immutable ProcessingRun/DocumentVersion/SourceUnit positions and the selected claim. The local interface verifies exact text identity, hashes, Unicode claim ranges, duplicate IDs and format bounds; it does not invent or independently establish scientific support. Formula/table/caption blocks should remain intact in the exported text.

## Counterbalancing and recorded measurements

Order is deterministic from tool version, review version, frozen seed and participant code. Each item appears twice. First-presentation assignment alternates across a seeded item shuffle, balancing paragraph-first/highlight-first within one item when the count is odd. A second seeded block presents the opposite condition. An immediate same-item repeat at the block boundary is avoided when there is more than one item. A/B-to-condition mapping also varies deterministically by participant. The exported dataset byte hash and schedule hash bind each record to the exact input and order.

Start reveals the item and begins timing. Done requires a participant-selected judgment: supported, partially supported, unsupported or cannot judge. Wall elapsed time includes pauses and hidden-tab time; active visible time excludes them. Pause hides the item. Visibility/pause/resume events are recorded. These observations do not measure reading, attention or comprehension directly.

Reopen last completed item creates a new separately numbered attempt with blank ratings. It preserves the earlier attempt and does not consume another scheduled item. Primary analysis should use the prespecified first completed attempt; reopened attempts can be reported separately. Both presentations involve repeated exposure to the same item, so order/carryover should be examined in the analysis. Unfinished items remain in the planned denominator and are not scored automatically.

Download judgments exports metadata, actual entered ratings/comments, actual elapsed times and observed events. It excludes source/answer text and condition decoding. After all scheduled presentations, Download analysis key exports the separate participant-specific mapping and schedule. Keep the key with the investigator's study materials until rating collection is complete. The result records the review/tool versions, dataset hash and initial document-DOM hash; package manifests separately bind the exact HTML file bytes.

Use keyboard Tab/Shift+Tab, native radio controls, visible Start/Pause/Done buttons and ordinary browser zoom. Narrow layouts preserve the same content with wrapping. Before collecting human data, run the local functional fixture and visually inspect representative desktop/narrow pages. Automated fixture interactions are software checks and are excluded from human results. Human counts remain zero until actual participants submit their files.

Closing or reloading discards unexported browser state. Download before leaving. This tool does not import previous judgments, manufacture timings, infer a missing grade or aggregate scientific/learning results; the separate study importer and analysis code perform those steps on actual submissions.
