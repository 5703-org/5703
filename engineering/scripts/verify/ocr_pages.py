"""Run real local OCR and retain unedited boxes/text/confidence for source review."""

import hashlib
import importlib.metadata
import json
from pathlib import Path
from datetime import datetime, timezone
import time
from rapidocr import RapidOCR
from rapidocr.utils.typings import OCRVersion, ModelType, LangDet, LangRec
from omegaconf import OmegaConf
import rapidocr
import onnxruntime
import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="evidence/openstax/ocr/render-manifest.json")
    parser.add_argument("--run", default="evidence/openstax/ocr/run.json")
    args = parser.parse_args()
    params = json.loads(Path("configs/corpus/ocr_cpu.json").read_text(encoding="utf-8"))
    for key, kind in {
        "Det.ocr_version": OCRVersion,
        "Rec.ocr_version": OCRVersion,
        "Det.model_type": ModelType,
        "Rec.model_type": ModelType,
        "Det.lang_type": LangDet,
        "Rec.lang_type": LangRec,
    }.items():
        params[key] = kind(params[key])
    engine = RapidOCR(params=params)
    models = [
        {
            "path": p.as_posix(),
            "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
        for p in sorted(Path("artifacts/ocr").glob("*"))
        if p.is_file()
    ]
    model_index = Path(rapidocr.__file__).parent / "default_models.yaml"
    provenance = {
        "runtime": "RapidOCR",
        "version": importlib.metadata.version("rapidocr"),
        "onnxruntime_version": onnxruntime.__version__,
        "execution_provider": "CPUExecutionProvider",
        "model_index_sha256": hashlib.sha256(model_index.read_bytes()).hexdigest(),
        "configuration": OmegaConf.to_container(engine.cfg, resolve=True, enum_to_str=True),
        "models": models,
        "review_status": "raw_machine_output_requires_original_page_review",
    }
    # Path values and NumPy values are converted explicitly; no text is corrected.
    provenance = json.loads(json.dumps(provenance, default=str))
    runtime_path = Path("evidence/openstax/ocr/runtime.json")
    if runtime_path.exists():
        old = json.loads(runtime_path.read_text(encoding="utf-8"))
        if old != provenance:
            raise ValueError(
                "OCR runtime changed; preserve the original and use a separately recorded runtime revision."
            )
    else:
        runtime_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    results = []
    for item in manifest["pages"]:
        path = Path(item["image_path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["image_sha256"]:
            raise ValueError("OCR input image hash changed")
        started = time.perf_counter()
        result = engine(path)
        boxes = result.boxes.tolist() if result.boxes is not None else []
        rows = [
            {"index": i + 1, "text": text, "confidence": float(score), "box": box}
            for i, (text, score, box) in enumerate(
                zip(result.txts or (), result.scores or (), boxes)
            )
        ]
        output = path.with_suffix(".ocr.json")
        record = {
            **item,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "runtime_manifest": "evidence/openstax/ocr/runtime.json",
            "review_status": "unreviewed",
            "lines": rows,
            "raw_line_count": len(rows),
            "limitations": "OCR is unedited. Reading order, symbols, table-cell associations and graph relationships require original-page review.",
        }
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        path.with_suffix(".ocr.txt").write_text(
            "\n".join(row["text"] for row in rows) + "\n", encoding="utf-8"
        )
        status = {
            "slug": item["slug"],
            "physical_page": item["physical_page"],
            "output": output.as_posix(),
            "line_count": len(rows),
            "elapsed_seconds": record["elapsed_seconds"],
        }
        results.append(status)
        print(json.dumps(status), flush=True)
        Path(args.run).write_text(
            json.dumps(
                {"pages": results, "completed": len(results) == len(manifest["pages"])}, indent=2
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
