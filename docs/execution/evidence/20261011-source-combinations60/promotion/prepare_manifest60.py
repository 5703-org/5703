"""Freeze exact reviewed candidates before the Main-only local promotion."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = HERE.parent / "5703-proof60-tests"
specifications = [
    (HERE / "checked.py", "generation/checked.py", "88509d22466095e5761bd247269a4dd03432fcb4dd2511ed02739e29da2e5d30", "b4e0cfddbac5ccc96e15aa217f3e26f649782d7bf545bb8dedc6d667b8b5e770"),
    (HERE / "source_evidence_combinations_v1.py", "generation/source_evidence_combinations_v1.py", "ab69de76304a08370acd9483866fbc84ea364e77caab36c723796f1e40bc4f8a", None),
    (HERE / "source_relation_repair_v2.txt", "generation/prompts/source_relation_repair_v2.txt", "03c8fa82094f1d2c9e4e7fee95bfd6ec2f555cef72220bdf761a13679779b92c", "deeeccc16c30f726c52771fa64e174ac4078860040cc16f78a8e69c7c14fbda5"),
    (TESTS / "test_source_evidence_combinations_v1.py", "tests/unit/test_source_evidence_combinations_v1.py", "1d9bb48e8d3257e65dadd9546f7a7877b4dc28ea1045617dabe8652827762b0e", None),
    (TESTS / "test_source_evidence_combinations_runtime.py", "tests/integration/test_source_evidence_combinations_runtime.py", "f81a6d8169e8ede946a83acb23c7291276ec071c0b3b7d82ab516983eed60e48", None),
]
files = []
for source, target, expected, predecessor in specifications:
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected, str(source)
    if source.suffix == ".py":
        ast.parse(data.decode("utf-8"), filename=str(source))
    files.append(dict(source=str(source), target=target, bytes=len(data), sha256=expected,
                      predecessor_sha256=predecessor))
review = dict(status="REVIEWED_LOCAL_ONLY", files=files,
              purpose="Generic bounded source combinations for validated negative units; preserve partial and original finite repair/recheck contracts",
              external_model_calls=0, new_provider_stages=0, budget_changes=False,
              acceptance_threshold_changes=False, database_access=False, git_actions=False)
with (HERE / "promotion60-review.json").open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(review, indent=2) + "\n")
print(json.dumps(review, indent=2))
