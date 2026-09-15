# Reproduce local source-image recovery

The four-book native-text scan found 13 low-text pages containing substantive diagrams, tables or illustrations. The user authorized necessary local recovery. OCR is a targeted source-processing step; no page image is sent to a hosted OCR service and no answer LLM is involved.

The actual run used RapidOCR 3.9.2, ONNX Runtime 1.29.0, PyMuPDF 1.28.2 and Python 3.13.2 on Windows x64. CPU execution was selected explicitly with eight intra-operation threads and one inter-operation thread. The [official RapidOCR installation guide](https://rapidai.github.io/RapidOCRDocs/main/en/install_usage/rapidocr/install/) documents the `rapidocr` plus `onnxruntime` installation. Exact optional package versions are in `requirements-ocr.lock`; the base and embedding locks remain separate.

```text
python -m pip install -r requirements.lock
python -m pip install -r requirements-embeddings.lock
python -m pip install -r requirements-ocr.lock
python -m pip check
python -m scripts.verify.render_ocr_pages
python -m scripts.verify.ocr_pages
```

Run from the repository root after the official acquisitions and page-decision records exist. Rendering selects only `substantive_visual_unextracted` pages from `evidence/openstax/pdf-low-text-decisions.json`, rechecks each original PDF hash and produces 2550×3300 PNGs at 300 DPI. `render-manifest.json` records original PDF identity, physical page, renderer, exact PNG hash and dimensions. Lower-resolution initial review images remain untouched.

OCR configuration is `configs/corpus/ocr_cpu.json`. Detection runs up to 3300 pixels and preprocessing permits 4000 pixels, avoiding the default downsampling of the periodic tables. The recognition score threshold is zero so low-confidence detected fragments remain available for review. OCR records do not infer missing symbols or relationships. Actual ONNX sessions reported `CPUExecutionProvider`.

| Model | Bytes | SHA-256 |
| --- | ---: | --- |
| PP-OCRv5 mobile detection | 4,819,576 | `4d97c44a20d30a81aad087d6a396b08f786c4635742afc391f6621f5c6ae78ae` |
| Mobile text orientation | 585,532 | `e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c` |
| PP-OCRv5 mobile English recognition | 7,872,351 | `c3461add59bb4323ecba96a492ab75e06dda42467c9e3d0c18db5d1d21924be8` |

The official release-specific model URLs, expected/actual hashes and actual execution providers are in `evidence/openstax/ocr/models.lock.json`. Model files are cached under `artifacts/ocr`. `runtime.json` retains the full effective configuration and runtime/model identities. The first run downloads these public models; it only reads the PDF page images locally.

The completed initial run in `evidence/openstax/ocr/run.json` produced 2,051 unedited detected fragments across all 13 pages. V4's whitespace-independent threshold subsequently identified Anatomy physical page470; `render-manifest-additional-1.json` and `run-additional-1.json` add that page and its165 fragments. The second addendum adds Chemistry physical1195 and its3 fragments. These three run records preserve15 processed pages and2,219 raw fragments without overwriting the initial record. Each `physical-NNNN-300dpi.ocr.json` retains text, confidence and four-corner coordinates in the original PNG. The adjacent `.ocr.txt` is a convenience view, not a reviewed transcription. `execution-retry.log` records the successful execution; the earlier configuration-type failure remains in `execution.log` as a failed attempt. Package install reports remain under `evidence/corpus`.

Additional diagnosed pages can be processed with `render_ocr_pages --page BOOK_SLUG:PHYSICAL_PAGE --output NEW_RENDER_MANIFEST.json`, then `ocr_pages --manifest NEW_RENDER_MANIFEST.json --run NEW_OCR_RUN.json`. Retain the earlier manifests and use a distinct output record. Threshold differences may discover further content; never loosen the threshold merely to clear a quality gate.

Reviewers must compare output to the original page and save corrections separately. Element names/values differ between books; source-specific differences are preserved even when another edition looks more familiar. Table-cell associations, superscripts, formulas, plot coordinates, arrows and reading order need explicit verification. A portrait can contain no useful OCR text; OCR does not establish the depicted person's identity or reconstruct an illustration.

`pipelines.image_transcriptions.apply_image_transcriptions` only accepts a separate source-verified artifact pinned to the PDF hash, physical page, PNG hash, raw OCR hash, reviewed text hash and normalized native-text hash. It retains the original PDF unit and its issues, adds an attributed image-text unit, and keeps visual limitations visible. Agent source verification is not independent human scientific evaluation. A recovered description or label set does not prove complete mathematical or diagram coverage across all 4,638 source pages.
