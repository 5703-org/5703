# Case04 public schema assessment

The final joint recheck failed the documented strict schema. No demonstrable prompt/schema mismatch or deterministic implementation defect was found. This is a scoped public-source assessment, not project completion or checker scientific-accuracy certification.

Root's qualified, read-only retained-response replay records sequence 4 (joint_check) passing with zero schema errors and sequence 8 (joint_recheck) failing with exactly three: `claims[0]` / `union_tag_invalid`, `requirements[0].relevance` / `missing`, and `requirements[0].redacted_field` / `extra_forbidden`. The invalid basis value and extra key were not exported and are not inferred. No `too_long` or `too_short` occurs in the reported errors.

The current public prompt lists exactly the six basis literals declared by the V4 discriminator. It expressly requires relevance; its legal example includes all eight RequirementCheck fields with an allowed relevance value. Its three-field requirement-evidence example also matches V5. Strict validation continues to forbid extra fields. Fourteen direct structural comparisons passed; an independent reviewer reached the same source-consistency conclusion. These are public-source comparisons, not a replay of hidden response values or an authored defect-fix red/green test.

No code or prompt fix is proposed from these errors. The condition for four additional paid calls is not met: no reproducible implementation defect has been fixed. The actual case04 failure and the ledger STOP must remain unchanged. Observability improvements cannot establish a repaired checker result.

Evidence: [Root safe retained replay](case04-retained-exact-schema-replay03.json), [pinned source-consistency receipt](case04-public-source-consistency01.json). The receipt records exact source and evidence byte counts, SHA-256 values, line references, and every comparison. Root replay: 2160 bytes / SHA-256 c2a23425c2e40af91e4019d28546802634ba5745201a15145502bd59c420643c. Current prompt: 14853 bytes / SHA-256 6304fd19b2c86f4c9670aacd29628922c95fd9ce4e453697976b0a0f8aca4a32.

This assessment read only public source and sanitized evidence. It did not access raw checker responses, DB/helpers, keys, private inputs, or Gold; it made zero provider calls, zero DB writes, and zero E writes.
