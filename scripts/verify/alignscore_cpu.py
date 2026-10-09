"""Offline optional AlignScore CPU diagnostic using an isolated installation.

Requires a protected authored contrast file and pinned official assets. It never
loads the application's answer provider, corpus writer or online request path.
"""

import argparse
from importlib.metadata import version
import json
import hashlib
from pathlib import Path
import statistics
import time


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            value.update(block)
    return value.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def percentiles(values):
    values = sorted(values)
    position = (len(values) - 1) * 0.95
    low = int(position)
    return {
        "n": len(values),
        "p50_ms": statistics.median(values),
        "p95_ms": values[low]
        + (values[min(low + 1, len(values) - 1)] - values[low]) * (position - low),
    }


def execute(args):
    if args.output.exists():
        raise ValueError("Preserve previous optional-model observations")
    args.output.mkdir(parents=True)
    root = args.environment_root
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    assert len(cases["pairs"]) == 8
    checkpoint = root / "AlignScore-base.ckpt"
    assert sha(checkpoint) == "6aedb637f0596ab29baef91e94466a57f032e02feea654978518919fe0981607"
    assets = json.loads((root / "roberta-base/ASSET_MANIFEST.json").read_text())
    assert assets["revision"] == "e2da8e2f811d1448a5b465c236feacd80ffbac7b"
    assert all(
        sha(root / "roberta-base" / item["path"]) == item["sha256"] for item in assets["files"]
    )
    import torch
    import alignscore  # type: ignore[import-not-found]

    torch.set_num_threads(2)
    assert torch.version.cuda is None and not torch.cuda.is_available()
    module = Path(alignscore.__file__).parent
    source_root = root / "source/yuh-zha-AlignScore-a0936d5/src/alignscore"
    code_hashes = {p.name: sha(p) for p in source_root.glob("*.py")}
    assert all(sha(module / name) == value for name, value in code_hashes.items())
    freeze = {
        "cases_sha256": sha(args.cases),
        "runner_sha256": sha(Path(__file__)),
        "checkpoint_sha256": sha(checkpoint),
        "checkpoint_bytes": checkpoint.stat().st_size,
        "code_commit": "a0936d5afee642a46b22f6c02a163478447aa493",
        "code_files": code_hashes,
        "backbone": assets,
        "model": "AlignScore-base",
        "mode": "nli_sp",
        "batch_size": 1,
        "device": "cpu",
        "threads": torch.get_num_threads(),
        "warm_repeats": 3,
        "versions": {
            name: version(name)
            for name in [
                "alignscore",
                "torch",
                "transformers",
                "pytorch-lightning",
                "spacy",
                "nltk",
                "numpy",
            ]
        },
        "interpretation": "Authored diagnostic contrasts; scores are uncalibrated and are not human labels or system accuracy.",
    }
    write(args.output / "frozen-study.json", freeze)
    write(args.output / "cases.json", cases)
    started = time.perf_counter()
    try:
        scorer = alignscore.AlignScore(
            model="roberta-base",
            batch_size=1,
            device="cpu",
            ckpt_path=str(checkpoint),
            evaluation_mode="nli_sp",
            verbose=False,
        )
    except Exception as exc:
        write(
            args.output / "initialization-failure.json",
            {"error_type": type(exc).__name__, "message": str(exc)[:1000]},
        )
        raise
    load_ms = (time.perf_counter() - started) * 1000
    rows = []
    for repeat in range(4):
        for pair in cases["pairs"]:
            for label in (
                ("supported", "contrast") if repeat % 2 == 0 else ("contrast", "supported")
            ):
                start = time.perf_counter()
                try:
                    score = scorer.score(contexts=[pair["context"]], claims=[pair[label]])[0]
                    error = None
                except Exception as exc:
                    score, error = None, type(exc).__name__
                row = {
                    "pair_id": pair["id"],
                    "kind": pair["kind"],
                    "variant": label,
                    "repeat": repeat,
                    "score": score,
                    "error": error,
                    "elapsed_ms": (time.perf_counter() - start) * 1000,
                }
                rows.append(row)
                write(args.output / "observations.json", rows)
    contrasts = []
    for pair in cases["pairs"]:
        supported = [
            r["score"]
            for r in rows
            if r["pair_id"] == pair["id"]
            and r["variant"] == "supported"
            and r["repeat"] > 0
            and r["score"] is not None
        ]
        contradicted = [
            r["score"]
            for r in rows
            if r["pair_id"] == pair["id"]
            and r["variant"] == "contrast"
            and r["repeat"] > 0
            and r["score"] is not None
        ]
        contrasts.append(
            {
                "pair_id": pair["id"],
                "kind": pair["kind"],
                "supported_mean": statistics.mean(supported) if supported else None,
                "contrast_mean": statistics.mean(contradicted) if contradicted else None,
                "ordered_as_authored": statistics.mean(supported) > statistics.mean(contradicted)
                if supported and contradicted
                else None,
            }
        )
    summary = {
        "cold_load_ms": load_ms,
        "first_pass": percentiles([r["elapsed_ms"] for r in rows if r["repeat"] == 0]),
        "warm_all": percentiles([r["elapsed_ms"] for r in rows if r["repeat"] > 0]),
        "observations": len(rows),
        "failed": sum(r["error"] is not None for r in rows),
        "contrasts": contrasts,
        "human_ratings": 0,
        "online_enabled": False,
        "frozen_study_sha256": sha(args.output / "frozen-study.json"),
        "source_unchanged": sha(Path(__file__)) == freeze["runner_sha256"],
    }
    write(args.output / "summary.json", summary)
    print(
        json.dumps(
            {
                k: summary[k]
                for k in ["cold_load_ms", "warm_all", "observations", "failed", "online_enabled"]
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    execute(parser.parse_args())


if __name__ == "__main__":
    main()
