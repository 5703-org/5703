"""Independent authored public fixtures for software tests.

These records are created here from the public test source passages and synthetic
protocol shapes. They do not load, reproduce or sample the private study catalogue
or SciQ dataset. Answers and labels below exercise software boundaries only.
"""

import json
from pathlib import Path


def write_sciq_fixture(path: Path) -> Path:
    rows = [
        {
            "question_id": "public-energy-fixture",
            "question": "What energy is stored in sugars?",
            "correct_answer": "chemical energy",
            "distractor1": "sound energy",
            "distractor2": "gravitational energy",
            "distractor3": "nuclear energy",
            "support": "Authored test reference: sugars store chemical energy.",
        },
        {
            "question_id": "public-plant-fixture",
            "question": "Where does photosynthesis occur in plants?",
            "correct_answer": "chloroplasts",
            "distractor1": "ribosomes",
            "distractor2": "nuclei",
            "distractor3": "lysosomes",
            "support": "Authored test reference: plant photosynthesis occurs in chloroplasts.",
        },
        {
            "question_id": "public-diffusion-fixture",
            "question": "How does concentration change during diffusion?",
            "correct_answer": "particles move from higher to lower concentration",
            "distractor1": "particles always move to higher concentration",
            "distractor2": "particles stop all movement",
            "distractor3": "all particles become light",
            "support": "Authored test reference: diffusion proceeds down a concentration gradient.",
        },
        {
            "question_id": "public-respiration-fixture",
            "question": "Which sugar supplies energy during cellular respiration?",
            "correct_answer": "glucose",
            "distractor1": "sodium chloride",
            "distractor2": "oxygen gas",
            "distractor3": "water",
            "support": "Authored test reference: cellular respiration releases energy from glucose.",
        },
    ]
    content = (json.dumps(rows, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError("Refusing to replace a different authored test fixture")
    else:
        path.write_bytes(content)
    return path


def question_cases():
    return [
        {
            "id": f"public-question-{i:02d}",
            "family": f"public-family-{i:02d}",
            "source_requirement": {"book": f"authored-book-{i // 6}"},
            "teaching_task": i < 12,
            "question": f"What is the labelled value in authored example {i}?",
            "critical_answer": f"The authored example {i} has value {i + 1}.",
            "turns": ["Give a clue.", "Give another clue.", "Explain the value."],
            "help_allowances": [
                "Point to the relevant label without giving its value.",
                "Explain how to identify the value without stating it.",
                "Explain the labelled value and the reasoning.",
            ],
        }
        for i in range(24)
    ]


def memory_trajectories():
    return [
        {
            "id": f"public-memory-{i:02d}",
            "family": f"public-memory-family-{i:02d}",
            "profile": {"level": "beginner", "style": "concise", "language": "en", "topics": []},
            "statements": [
                f"For authored course {i}, please use a labelled diagram.",
                f"For authored course {i}, please replace diagrams with a numbered list.",
            ],
            "probes": [
                {
                    "question_id": f"public-question-{i:02d}",
                    "events": [{"kind": "statement", "index": turn - 1}] if turn < 3 else [],
                    "use_profile": turn < 3,
                    "prefix": "" if turn < 3 else "Use this current instruction only. ",
                    "expected": {
                        "selected_fields": ["presentation_preference"] if turn < 3 else [],
                        "expected_values": {
                            "presentation_preference": "diagram" if turn == 1 else "list"
                        }
                        if turn < 3
                        else {},
                    },
                }
                for turn in range(1, 4)
            ],
        }
        for i in range(12)
    ]
