"""Consolidated actual GenerationService replay of UI prompts and authored scenarios."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from generation import GenerationRequest, GenerationService
from personalisation import compile_profile
from scripts.verify.replay_openstax_mock_generation import request_evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    sources = json.loads(
        (ROOT / "evaluation/conversations/source_requirements.json").read_text(encoding="utf-8")
    )
    scenarios = json.loads(
        (ROOT / "evaluation/conversations/scenarios.json").read_text(encoding="utf-8")
    )
    hits = [
        {
            "chunk_id": f"authored-{item['topic']}",
            "asset_id": "authored-software-source",
            "processing_id": "authored-software-processing",
            "source_title": item["title"],
            "section": item["section"],
            "pages": [index],
            "locator": f"Authored fixture, page {index}",
            "text": item["text"],
            "text_hash": hashlib.sha256(item["text"].encode()).hexdigest(),
            "topic": item["topic"],
        }
        for index, item in enumerate(sources["passages"], 1)
    ]
    engine = GenerationService()
    records = []
    history_seed = [{"id": "prior-user", "role": "user", "content": "What is photosynthesis?"}]
    # Every distinct submitted learner prompt in the existing e2e TS files and
    # clean-install script; repeated resize/stop/retry prompts share one entry.
    ui_cases = [
        (
            "What is photosynthesis?",
            [],
            True,
            "answer",
            "chat.spec.ts; lifecycle.spec.ts; verify-clean-install.mjs",
        ),
        (
            "Why does it need light?",
            history_seed,
            True,
            "answer",
            "chat.spec.ts; verify-clean-install.mjs",
        ),
        ("Explain it more simply.", history_seed, False, "answer", "chat.spec.ts profile-off turn"),
        ("Why does it do that?", [], True, "clarification", "chat.spec.ts ambiguity"),
        (
            "I mean photosynthesis.",
            [{"id": "ambiguous", "role": "user", "content": "Why does it do that?"}],
            True,
            "answer",
            "chat.spec.ts ambiguity completion",
        ),
        ("Hello", [], True, "social", "chat.spec.ts greeting"),
        (
            "Why does photosynthesis need light?",
            history_seed,
            True,
            "answer",
            "lifecycle.spec.ts repeated arrivals",
        ),
        (
            "Explain photosynthesis with more detail.",
            history_seed,
            True,
            "answer",
            "lifecycle.spec.ts completion while reading",
        ),
        ("Make it simpler", history_seed, False, "answer", "verify-openstax-release.mjs"),
        ("Give an example", history_seed, False, "answer", "verify-openstax-release.mjs"),
        (
            "What are your sources?",
            history_seed,
            True,
            "answer",
            "source-request contract; evidence reuse",
        ),
        (
            "Give an example of photosynthesis",
            [],
            True,
            "answer",
            "explicit-topic example contract",
        ),
        ("I meant photosynthesis.", history_seed, True, "answer", "correction-family regression"),
    ]

    def run(
        group,
        question,
        history,
        selected,
        profile,
        expected=None,
        origin=None,
        mode="interactive_chat",
        condition="E1",
    ):
        outcome = engine.generate(
            GenerationRequest(
                request_id=f"ui-prompt-replay-{len(records) + 1}",
                mode=mode,
                condition=condition,
                question=question,
                evidence=request_evidence(selected),
                history=history,
                profile=profile,
            )
        )
        actual = (outcome.response or {}).get("response_type")
        record = {
            "group": group,
            "origin": origin,
            "question": question,
            "expected_software_response_type": expected,
            "actual_response_type": actual,
            "software_assertion_passed": None
            if expected is None
            else outcome.succeeded and actual == expected,
            "history": list(history),
            "outcome": outcome.to_dict(),
        }
        records.append(record)
        return outcome

    for question, history, use_profile, expected, origin in ui_cases:
        run(
            "frontend_submitted_prompt",
            question,
            history,
            hits[:1],
            compile_profile(None, use_profile, question),
            expected,
            origin,
        )
    run(
        "administrator_authored_control",
        "What is photosynthesis?",
        [],
        [],
        None,
        "answer",
        "admin.spec.ts authored E0 evaluation",
        "benchmark_openqa",
        "E0",
    )

    # Also replay the unchanged complete twelve-family workload. It defines no
    # gold/category expectations; valid schemas are not scientific successes.
    for scenario in scenarios["scenarios"]:
        history = []
        for turn in scenario["turns"]:
            if turn.get("before") == "new_session":
                history = []
            question = turn["content"]
            setup = scenario.get("setup", {})
            if turn.get("use_long_prefix"):
                question = (
                    setup["long_message_prefix"] * setup["long_message_prefix_repetitions"]
                    + question
                )
            selected = [item for item in hits if item["topic"] in scenario["source_topics"]]
            outcome = run(
                "authored_scenario_" + scenario["scenario_id"],
                question,
                history,
                selected,
                compile_profile(setup.get("profile"), turn.get("use_profile", True), question),
                origin="evaluation/conversations/scenarios.json",
            )
            history = history + [
                {"id": f"user-{len(records)}", "role": "user", "content": question}
            ]
            if outcome.response:
                history.append(
                    {
                        "id": f"assistant-{len(records)}",
                        "role": "assistant",
                        "content": outcome.response["answer_text"],
                    }
                )

    # New real-release browser prompts are checked with their exact recorded
    # official candidates separately from the authored fixture above.
    real = json.loads(
        (ROOT / "evidence/openstax/retrieval-before-fix.json").read_text(encoding="utf-8")
    )
    for question, expected in (
        ("How does glycolysis produce ATP from glucose?", "answer"),
        ("Who won the 2026 Formula One world championship?", "refusal"),
    ):
        case = next(item for item in real["questions"] if item["question"] == question)
        run(
            "real_release_browser_prompt",
            question,
            history_seed,
            case["hits"],
            compile_profile(None, False, question),
            expected,
            "verify-openstax-release.mjs; exact real E5 candidates",
        )

    tracked = [
        ROOT / "generation/adapters.py",
        ROOT / "conversation/query.py",
        ROOT / "evaluation/conversations/source_requirements.json",
        ROOT / "evaluation/conversations/scenarios.json",
        *sorted((ROOT / "frontend/tests/e2e").glob("*.ts")),
        ROOT / "frontend/scripts/verify-clean-install.mjs",
        ROOT / "frontend/scripts/verify-openstax-release.mjs",
    ]
    failures = [
        record["question"]
        for record in records
        if record["software_assertion_passed"] is False or record["outcome"]["error"]
    ]
    data = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Actual offline GenerationService replay, explicit mock provider, no database writes. Required UI response categories are software expectations only. All unchanged authored workload turns are additionally recorded without inventing gold expectations or semantic pass labels. Draft-only text, uploaded documents, account fields and persisted stress-fixture prose are not submitted prompts and are excluded.",
        "input_file_hashes": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in tracked
        },
        "required_category_checks": sum(
            record["expected_software_response_type"] is not None for record in records
        ),
        "record_count": len(records),
        "failures": failures,
        "records": records,
    }
    with (ROOT / args.output).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "record_count": len(records),
                "required_category_checks": data["required_category_checks"],
                "failures": failures,
                "authored_scenarios": [
                    {
                        "group": record["group"],
                        "question_tail": record["question"][-120:],
                        "type": record["actual_response_type"],
                    }
                    for record in records
                    if record["expected_software_response_type"] is None
                ],
            },
            indent=2,
        )
    )
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
