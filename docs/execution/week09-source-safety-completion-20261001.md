# Week 9 source processing, mutation boundaries and migration safety

This 1 October 2026 checkpoint closes the successful full-book isolated-parse gap for the stored official Concepts of Biology PDF and adds current write-authorization and additive-schema safety evidence. The original PDF, published four-book corpus and existing saved answers remain unchanged. The parser implementation needed no further adjustment during this checkpoint.

## Official full-book parse

The stored original is `artifacts/storage/originals/da0ffc8585e172f04eb0abb08949087baf85cc229ef2736ef06e5aa17094b1f6.pdf`, 185,858,638 bytes, with SHA-256 `da0ffc8585e172f04eb0abb08949087baf85cc229ef2736ef06e5aa17094b1f6`. Its existing official source and acquisition record remain in the corpus manifest. The diagnostic read this file directly, using the current `pypdf_bookmarks_v5` parser under `isolated_parse_v1` in an empty writable private scratch directory. Settings selected 536,870,912 input bytes, 268,435,456 output bytes and a 900-second wall limit.

| Actual observation | Result |
| --- | ---: |
| Successful complete child execution | 10.527 seconds |
| Physical pages represented, with no gap | 613 / 613 |
| Parsed source units | 753 |
| Ready / blocked units | 749 / 4 |
| Serialized child result | 3,698,319 bytes |
| Source hash unchanged / temporary files remaining | Yes / 0 |
| Database connections / database writes / provider calls | 0 / 0 / 0 |

The [public receipt](../../evidence/week09-continuation/20261001/parser-official-full-book-20261001.json) records the four blocked units' physical pages and issue codes, counts every retained issue, and pins the parser code hashes. Extracted unit text remains in the private diagnostic record under `E:/5703/week09-private-db/official-full-parse-20261001/`; it is excluded from delivery evidence. No units or vectors were inserted or republished. The earlier ACL failure and ten-second timeout remain in the [isolation checkpoint](week09-isolated-source-parser-20260930.md).

There are 725 `UNEXTRACTED_VISUAL_CONTENT` warnings, three `LOW_TEXT_IMAGE_PAGE` issues and two `EMPTY_UNIT` issues in the parsed-unit record; codes may co-occur in one unit. The result demonstrates complete execution and locator retention. Figure, table and formula meaning still requires content review. The child remains a separate process sharing the worker's filesystem permissions, with no operating-system resident-memory or CPU cap.

## Mutating route and private-rubric regressions

The [focused receipt](../../evidence/week09-continuation/20261001/learning-write-migration-focused-20261001.json) and [log](../../evidence/week09-continuation/20261001/learning-write-migration-focused-20261001.log) record four integration tests passing in 4.77 seconds with two dependency deprecation warnings. Tests use authored, explicitly labelled fixtures and randomly named disposable PostgreSQL databases on the local test server. No paid model was called.

Nine other-owner writes returned HTTP 404: goal update, unit-read mark, note update, note deletion, note-to-card conversion, review rescheduling, card self-rating, creating a note against another owner's goal and submitting practice against another owner's goal. The owner was a student and the other principal an administrator in the same workspace, so the test also checks that an administrator's role grants no ownership of personal learning objects. Complete snapshots of the owner goal, notes, review entry and learning-event IDs matched before and after these attempts. Five student-to-administrator writes returned HTTP 403 across practice create, validate, publish and retire, and relation review. These finite route probes cover the tested operations; they are not a complete mutating-endpoint security audit.

The same test inspects practice listing, item detail, initial progress, incorrect-attempt feedback, one authored hint, saved attempt, learning records, Markdown export and DOCX XML before explicit solution disclosure. The fixed private-solution canary and private answer-key fields were absent from these projections. API and export responses carried `Cache-Control: no-store`. An explicit learner `full_explanation` action then disclosed the authored explanation as designed. This verifies the tested response/export boundary; it does not establish absence of rubric disclosure from every prompt, internal cache or model-mediated attack. The two tests are [migration safety](../../tests/integration/test_learning_migration_safety.py) and [write safety](../../tests/integration/test_learning_write_safety.py); Ruff lint and formatting passed.

The first test invocation passed the two migration cases but could not initialize the two HTTP fixtures because Windows denied the default pytest temporary parent. The successful rerun selected a fresh writable workspace scratch directory. That setup failure remains described in the receipt and is excluded from product-failure counts.

## Latest-schema backup, restoration and rollback

An actual `pg_dump --format=custom` and `pg_restore --exit-on-error` round trip ran on two fresh fixture databases through the existing backup and restore commands. The current migration head at that moment was `f7d83ea960bf`. The fixture contained two personal notes, one personal-card queue entry, one proposed concept relation and one hash-verified original text file. It used no official corpus replacement and made no provider calls. The [restoration receipt](../../evidence/week09-continuation/20261001/learning-backup-restore-20261001.json) records the 182,089-byte dump, dump hash, original-file hash and independent before/after full-row hashes.

All columns of the three new learning-product tables matched exactly after restoration. The restored file hash and built-in backup fingerprint matched, and the source fixture database remained unchanged. A downgrade toward `f5b61c9247de` was refused because the relation table contained a record; transactional rollback also retained the starting f7 head. A second restore toward the already existing target database was refused and preserved its rows. The two disposable databases were removed after verification; the dump, manifest and receipts remain private.

The regression separately verifies f5 backfilling of a pre-existing personal card without changing its note. A populated personal-card queue blocks downgrade to f4 with its note and queue unchanged. After deliberately removing only the test queue entry, downgrade and re-upgrade succeed and recreate the queue. A populated f6 relation registry likewise blocks downgrade; an explicitly emptied test registry permits downgrade and re-upgrade while preserving its document. This records the safety behavior of the existing guards and does not authorize removal of live review or relation records.

The built-in `backup-v2` fingerprint counts every table and hashes selected corpus, answer and identity tables. It does not hash complete note, review and concept-relation row contents, so this diagnostic adds an independent complete-row comparison. The latest full official-corpus backup/restore, installed upgrade journey, real concurrency/cancellation/recovery, malicious-upload stress and fresh physical-machine acceptance still require their own run. Human figure/formula and exercise quality ratings remain pending.
