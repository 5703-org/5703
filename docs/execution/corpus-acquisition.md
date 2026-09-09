# Official OpenStax acquisition and real embedding plan

Observed 2026-09-08. The user authorized official public downloads and local processing; answer LLM calls remain mock-only. Existing referenced raw assets, releases and answer snapshots must remain intact. Website notices are recorded as source metadata; no external message, permission form or account enrollment is part of this plan.

## Exact source-supported scope

The v5 English master (extracted line275) requires inspection of actual approved book/edition records, prohibits guessing missing titles and forbids calling a single book a four-book release. The source owner's `development_inputs/sources/COMP5703/tut5/HongleYang/WEEK4_SUMMARY_AND_WEEK5_PLAN.md`, dated2026-08-29, lines12–14, explicitly freezes **Biology 2e, Chemistry 2e, Anatomy & Physiology 2e, Concepts of Biology** for dataset `cs30_openstax_v0.2`. It explicitly excludes retired **College Physics**. The older general research recommendation containing College Physics does not override this later scope decision.

The summary references a 13-entry download manifest and a decision JSON, but those two complete files were not present in the supplied source tree. Consequently the titles/editions are supported by the actual owner summary; the other books' historical raw-byte hashes cannot be invented. The supplied Concepts pilot `input_manifest_snapshot.json` preserves its exact source URL,185858638 bytes and SHA-256 `da0ffc8585e172f04eb0abb08949087baf85cc229ef2736ef06e5aa17094b1f6`.

## Official catalogue observations

The current OpenStax CMS API was queried directly for each exact slug; all four returned one matching `book_state=live` record. URLs, ISBNs, publication dates, catalogue license fields and HTTP HEAD observations are frozen in `evidence/corpus/official_catalog.json`. The API is public at `https://openstax.org/apps/cms/api/v2/pages/?type=books.Book&slug=BOOK_SLUG&fields=*`. Only the textbook PDF is in scope; instructor answer guides/locked resources are excluded.

| Book and edition | Official PDF | Current HTTP size | Official publication / digital ISBN |
| --- | --- | ---: | --- |
| Biology 2e | [Official Biology PDF](https://assets.openstax.org/oscms-prodcms/media/documents/Biology-2e_-_WEB.pdf) | 401,298,122 bytes | 2018-03-28 / 978-1-947172-52-4 |
| Chemistry 2e | [Official Chemistry PDF](https://assets.openstax.org/oscms-prodcms/media/documents/chemistry-2e_-_WEB.pdf) | 217,794,376 bytes | 2019-02-14 / 978-1-947172-61-6 |
| Anatomy and Physiology 2e | [Official Anatomy PDF](https://assets.openstax.org/oscms-prodcms/media/documents/anatomy-and-physiology-2e_-_WEB.pdf) | 476,335,014 bytes | 2022-04-20 / 978-1-951693-42-8 |
| Concepts of Biology | [Official Concepts PDF](https://assets.openstax.org/oscms-prodcms/media/documents/Concepts-Biology_-_WEB.pdf) | 185,858,638 bytes | 2013-04-25 / 978-1-947172-03-6 |

These are current **HEAD observations**, not completed downloads or verified file hashes. The Concepts length matches the historical snapshot, but only a downloaded SHA-256 can establish the same bytes. Total advertised size is1,281,286,150 bytes. The existing250MB upload maximum cannot accept Biology/Anatomy; use a deliberately bounded512MiB configuration and retain upload validation.

Current catalogue metadata identifies CC BY-NC-SA4.0 for all four books. The [current Concepts preface](https://openstax.org/books/concepts-biology/pages/preface) also carries an AI-ingestion permission notice. Each acquired PDF's actual copyright/license/edition pages must be inspected and recorded independently; neither the older owner's CC BY4.0 report nor today's web footer is a substitute for that file-specific observation. Keep source title, free-book link, edition, actual license wording reference and provenance available for citation/attribution. Do not label the locally authorized engineering work as publisher approval.

## Pinned E5 execution

Use `intfloat/e5-small-v2` revision **ffb93f3bd4047442299a41ebb6fa998a38507c52**, verified through the [official model commit](https://huggingface.co/intfloat/e5-small-v2/commit/ffb93f3bd4047442299a41ebb6fa998a38507c52) and model API. The [model card](https://huggingface.co/intfloat/e5-small-v2) identifies an MIT-licensed English model with384-dimensional embeddings and a512-token window. Its safetensors metadata has33,360,512 parameters (33,360,000 float32 and512 int64); the main weight file is approximately133MB. Download only the necessary model/tokenizer/pooling files, not all ONNX/OpenVINO/TensorFlow duplicate exports.

The adapter must add `query: ` and `passage: `, use the pinned checkpoint's actual tokenizer, include heading/prefix/special tokens, reject over-window inputs before encoding, and normalize finite nonzero vectors. Chunk settings remain320 target,448 cap,48 overlap. Batch32 is the initial bounded inference setting. Build a separate E5 release; hashed mock vectors cannot be renamed E5 or used as its compatible cache.

Observed capacity:32 logical CPUs, approximately61.6GiB physical RAM (36.5GiB free at observation), approximately47.4GiB available on E:. Root independently observed an RTX5070Ti with16GB VRAM and NVIDIA driver591.86. The pinned CUDA12.8 PyTorch2.8.0 build is installed; the [official previous-version commands](https://pytorch.org/get-started/previous-versions/) publish that Windows build and the [PyTorch2.7 announcement](https://pytorch.org/blog/pytorch-2-7/) documents Blackwell/CUDA12.8 support. Actual CUDA tensor execution and the pinned E5 semantic/tokenizer smoke passed, recorded in `evidence/corpus/cuda_verification.json` and `e5_verification.json`. The complete 134,478,697-byte snapshot and individual SHA-256 values are recorded in `e5_download.json`. Reproduction instructions and exact optional dependency versions are in `docs/real_embeddings.md` and `requirements-embeddings.lock`. CPU use must be explicit if CUDA cannot execute.

## Execution and review sequence

1. Download each exact official URL to a separate acquisition directory with a temporary partial filename. Record start/end, final URL, response metadata, size and SHA-256; never overwrite original supplied evidence. A changed Concepts hash is a new version and cannot close the old page1/2 issue.
2. Inspect PDF metadata, copyright/license pages and physical page count. Render and review first/empty/suspicious pages before deciding whether content is legitimate blank/front matter or an extraction defect. Persist the decision and original issue counts; never casually exclude failures to force a ready state.
3. Parse every page, preserve real headings/raw and cleaned text/hashes, and export reconciled QA/quarantine reports. Review representative equations, captions, tables and two-column reading order. Unsupported non-text figures remain an explicit limitation; do not invent their content.
4. Load the exact E5 checkpoint on CUDA, record actual dependency versions/device/window/dimensions and a known text/query smoke result. Chunk against its actual tokenizer and retain complete source spans.
5. Build a new release from actually ready processing runs, validate all source/vector hashes and membership, and inspect a deterministic random50-chunk sample back to original pages. Partial corpus coverage must be named explicitly if any book remains quarantined.
6. Activate only the completed verified release. Run retrieval/source resolution against the real text and retain source-specific citations. Answer LLM remains marked mock; real textbook retrieval does not become evidence of real generative answer quality.

This plan is evidence preparation. Download, review, embedding and activation status must be updated from actual execution artifacts; none of the planned steps is marked complete by this document.
