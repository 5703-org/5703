# Week 9 bounded original hash verification

At the 30 September successor source checkpoint, `execute_processing` checked each saved original by loading the entire file with `Path.read_bytes()` before parsing. An accepted original may be as large as 512 MiB. Processing now calls the existing `_file_sha256` helper, which reads 65,536-byte blocks, and still compares the result with the immutable `DocumentVersion.raw_hash`. The storage-root containment, existence check, `SOURCE_UNAVAILABLE` failure and subsequent parser dispatch are unchanged.

The new unit regression instruments file reads on a source larger than three blocks and requires every hash read to request exactly 65,536 bytes. A separate behavior regression uses a same-size, one-byte-corrupted original, forbids any `Path.read_bytes()` call and any parser call, and checks the failed processing state. The PostgreSQL integration regression uploads an authored text source, changes one byte without changing its length, queues the normal processing job and verifies `SOURCE_UNAVAILABLE`, zero parser calls and no source-unit or chunk publication.

The focused run included both new unit checks, the existing corpus-runtime module and both streamed-upload modules: **26 passed, 0 failed**, with two dependency deprecation warnings. Ruff check and Ruff formatting check passed without cache on the three edited Python files. The redacted [test log](../../evidence/week09-continuation/20260930/processing-hash-focused-20260930.log) has SHA-256 `608c714593a1746069fcf8c3d7b2813d369faec1f7c03a01caa00c1b3ddc6b25`.

| File | SHA-256 after the focused run |
| --- | --- |
| `backend/app/modules/knowledge/service.py` | `3c2e980b908f8d8b2f893eef5f39e15aee777bd575612f3f895147bb378cfd19` |
| `tests/integration/test_corpus_runtime.py` | `fa777ddcb408e74aba27e2c4e83c449e5fef44354f061f550b4d72f285666e7d` |
| `tests/unit/test_processing_original_hash.py` | `abf3c336149f073b5cc972c8e5d0b8bcee28d42b0c489078e40ea5fbfb5b2806` |

The default test database port did not respond. An isolated portable database rejected the host through its access policy. The first reachable test-capable PostgreSQL run was stopped by the default Windows pytest temporary-directory ACL. The successful focused run used a fresh temporary directory under `E:/5703/` and a randomly named database created and dropped by the integration fixture; these setup failures are not processing-test failures. The run used local fixtures and made no paid model calls.

This change removes the additional whole-file copy made during integrity validation. At this initial checkpoint, the TXT parser still read its source text as a whole and the PDF parser ran in the background worker process. The later [isolated source-parser checkpoint](week09-isolated-source-parser-20260930.md) records the subsequent execution boundary, its limits, and updated tests. The previous V12 release archive is unchanged.
