"""Export a pinned local MiniLM graph and separately identified dynamic INT8 graph."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path

from retrieval.cpu_backend import file_hash, torch_threads


def export(policy_path, output):
    import onnx
    from onnxruntime.quantization import QuantType, quantize_dynamic
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from huggingface_hub import snapshot_download
    from retrieval.chat import load_policy

    policy = load_policy(policy_path)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a new export directory to preserve existing artifacts")
    snapshot = Path(
        snapshot_download(
            policy["reranker_model"],
            revision=policy["reranker_revision"],
            cache_dir=policy["reranker_cache_folder"],
            local_files_only=True,
        )
    )
    configuration = json.loads((snapshot / "config.json").read_text())
    if (
        configuration.get("sbert_ce_default_activation_function")
        != "torch.nn.modules.linear.Identity"
    ):
        raise ValueError("This export supports the pinned raw-logit identity activation only")
    output.mkdir(parents=True)
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
    model = (
        AutoModelForSequenceClassification.from_pretrained(
            snapshot, local_files_only=True, attn_implementation="eager"
        )
        .eval()
        .cpu()
    )

    class Logits(torch.nn.Module):
        def __init__(self, inner):
            super().__init__()
            self.inner = inner

        def forward(self, input_ids, attention_mask, token_type_ids):
            return self.inner(
                input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids
            ).logits

    batch = tokenizer(["Export shape probe."], ["Tokenizer shape probe."], return_tensors="pt")
    names = ["input_ids", "attention_mask", "token_type_ids"]
    fp32, int8 = output / "model.fp32.onnx", output / "model.int8.onnx"
    with torch_threads(2), torch.inference_mode():
        torch.onnx.export(
            Logits(model),
            tuple(batch[name] for name in names),
            str(fp32),
            input_names=names,
            output_names=["logits"],
            dynamo=False,
            opset_version=17,
            dynamic_axes={
                **{name: {0: "batch", 1: "sequence"} for name in names},
                "logits": {0: "batch"},
            },
        )
    onnx.checker.check_model(str(fp32))
    quantize_dynamic(
        str(fp32),
        str(int8),
        weight_type=QuantType.QInt8,
        per_channel=True,
        reduce_range=True,
        op_types_to_quantize=["MatMul", "Gemm"],
    )
    onnx.checker.check_model(str(int8))
    source_names = [
        "config.json",
        "model.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "vocab.txt",
    ]
    manifest = {
        "version": "minilm_onnx_export_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": policy["reranker_model"],
        "revision": policy["reranker_revision"],
        "activation": "identity",
        "window": int(tokenizer.model_max_length),
        "opset": 17,
        "quantization": {
            "weight_type": "QInt8",
            "per_channel": True,
            "reduce_range": True,
            "op_types": ["MatMul", "Gemm"],
        },
        "source_files": {name: file_hash(snapshot / name) for name in source_names},
        "files": {p.name: file_hash(p) for p in (fp32, int8)},
        "backends": {"onnx_fp32": fp32.name, "onnx_int8": int8.name},
        "libraries": {
            name: importlib.metadata.version(name)
            for name in ("torch", "transformers", "onnx", "onnxruntime", "numpy")
        },
        "threshold_calibration": "unavailable",
        "default_activation": False,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"manifest": str(manifest_path), "sha256": file_hash(manifest_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--policy", type=Path, default=Path("configs/retrieval/chat_hybrid_minilm.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.policy, args.output), indent=2))


if __name__ == "__main__":
    main()
