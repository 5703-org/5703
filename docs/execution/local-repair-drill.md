# Local repair and restored-source inspection

AC-33 now has actual evidence for each local clause. The cleanup tests use
real PostgreSQL and storage with a deliberately aged orphan, preserve referenced
originals, and reject changed bytes and root escapes. The process drill adds
actual stuck-job inspection, explicit interruption recovery and eligible retry.
A separate actual restored-copy API check verifies unavailable historical source
behavior while preserving the usable current corpus.

| Clause | Actual evidence |
| --- | --- |
| Orphan dry-run/apply, referenced files preserved | `tests/integration/test_operations.py::test_cleanup_dry_run_and_apply_preserve_referenced_bytes` in the [saved passing JUnit](../../evidence/acceptance/observation-20260908-0825/pytest.xml) |
| Changed-file/root-escape rejection | `tests/integration/test_operations.py::test_cleanup_rejects_changed_file_and_root_escape` in the same JUnit |
| Actual worker interruption, operator inspection, explicit recovery/retry | [Process drill](worker-interruption.md) and [actual results](../../evidence/operations/worker-interruption/20260908T085003Z/verification.json) |
| Historical evidence unavailable after local restore | [Restored-copy verification](../../evidence/operations/restored-source-visibility/20260908T085613Z/verification.json) and [API observations](../../evidence/operations/restored-source-visibility/20260908T085613Z/api-observations.json) |

The restored-copy check used `cs30_restore_openstax_portable_20260908` and its
matching restored source directory. Read-only inspection found no previously
revoked document. The drill therefore revoked one old **authored** source through
the restored app's administrator API. That document was absent from the active
four-book release. The mutation was restricted to that restored copy; no main
database, worker, model, original backup or physical source file was changed.

Historical evidence returned HTTP 200 before revocation and HTTP 410 with
`EVIDENCE_UNAVAILABLE` afterward. The answer remained available with the same
response and conversation snapshot, while its revoked evidence disappeared from
the public answer envelope. Stored messages, answers, requests, evidence,
snapshots, citations, jobs and attempts retained exactly matching table hashes.
The active release, its four source memberships and every other document row were
unchanged. Both database readiness and `chat_ready` remained true. The affected
physical original hash and the original backup manifest hash were unchanged.

The named restored database now retains the intentionally revoked authored source.
Its earlier restore and E5-container reports remain historical snapshots from
before this drill. The immutable original backup was preserved. No cross-backup
erasure or independent human/scientific validation is claimed.

The [verification utility](../../scripts/verify/restored_source_visibility.py)
requires an actual successful restore-proof file, a matching `cs30_restore_*`
database and repository-local restored storage, an explicit document ID and
`--apply-revoke`. It refuses an already-revoked source and sources belonging to
the active release. A new complete replay therefore requires a fresh disposable
restore; it does not reset this evidence copy silently.
