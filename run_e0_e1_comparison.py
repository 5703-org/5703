"""Run controlled E0 Pure LLM versus E1 Dense-RAG + LLM answer generation.

The script uses an OpenAI-compatible endpoint, so it can be configured for a
provider such as DeepSeek.  It never uses an API key from a source file.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from urllib import request, error

from rag_prompt_builder import build_prompt


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def call_model(base_url: str, api_key: str, model: str, messages: list[dict], temperature: float) -> tuple[str, dict]:
    payload = json.dumps(
        {"model": model, "messages": messages, "temperature": temperature}, ensure_ascii=False
    ).encode("utf-8")
    http_request = request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise RuntimeError(f"LLM endpoint returned HTTP {exc.code}") from exc
    return data["choices"][0]["message"]["content"], data.get("usage", {})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True, type=Path, help="JSONL: question_id, question")
    parser.add_argument("--retrieval-results", required=True, type=Path, help="JSONL: question_id, evidence")
    parser.add_argument("--output-dir", default="results/week8", type=Path)
    parser.add_argument("--base-url", required=True, help="OpenAI-compatible provider base URL")
    parser.add_argument("--model", required=True)
    parser.add_argument("--top-k", choices=(3, 5, 10), type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--api-key-env", default="LLM_API_KEY")
    args = parser.parse_args()
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise RuntimeError(f"Set {args.api_key_env}; do not put API keys in code or result files")

    evidence_by_question = {row["question_id"]: row.get("evidence", row.get("hits", [])) for row in read_jsonl(args.retrieval_results)}
    questions = read_jsonl(args.questions)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {"E0": [], "E1": []}
    for question_row in questions:
        question_id, question = question_row["question_id"], question_row["question"]
        for condition in ("E0", "E1"):
            evidence = [] if condition == "E0" else evidence_by_question.get(question_id, [])[: args.top_k]
            if condition == "E1" and not evidence:
                raise ValueError(f"E1 requires retrieved evidence for {question_id}")
            messages = build_prompt(question, evidence)
            started = time.perf_counter()
            try:
                answer, usage = call_model(args.base_url, api_key, args.model, messages, args.temperature)
                status, failure = "succeeded", None
            except RuntimeError as exc:
                answer, usage, status, failure = "", {}, "error", str(exc)
            outputs[condition].append(
                {
                    "run_at": datetime.now(timezone.utc).isoformat(),
                    "condition": condition,
                    "question_id": question_id,
                    "question": question,
                    "model": args.model,
                    "temperature": args.temperature,
                    "top_k": args.top_k if condition == "E1" else 0,
                    "evidence": evidence,
                    "answer": answer,
                    "usage": usage,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                    "status": status,
                    "error": failure,
                }
            )
    for condition, rows in outputs.items():
        path = args.output_dir / ("e0_pure_llm.jsonl" if condition == "E0" else "e1_dense_rag.jsonl")
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    (args.output_dir / "experiment_config.json").write_text(
        json.dumps(
            {
                "model": args.model,
                "temperature": args.temperature,
                "top_k": args.top_k,
                "control": "E0 and E1 use identical questions, model, system prompt and temperature; only E1 receives retrieved evidence.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"status": "completed", "questions": len(questions), "output_dir": str(args.output_dir)}))


if __name__ == "__main__":
    main()
