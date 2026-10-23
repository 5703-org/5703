"""Evaluator-only freeze, quote and denominator checks for exposed draft packets."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from evaluation.week09_continuation import adjudication as audit


PACKET = """# Draft Answer Review RD-001

## Original question

How do canaliculi help osteocytes receive nutrients?

## Draft answer

The sources do not mention nutrient receipt [ev_001].

## Textbook passages cited by the draft

### [ev_001] Anatomy and Physiology 2e

Section: Chapter 6 Bone Tissue / 6.3 Bone Structure. PDF page(s): 223.

[Official PDF](https://assets.openstax.org/oscms-prodcms/media/documents/anatomy-and-physiology-2e_-_WEB.pdf)

```text
Osteocytes can communicate with each other and receive nutrients via long cytoplasmic processes that extend through canaliculi.
```

Textbook excerpts: © Rice University; CC BY-NC-SA 4.0.
"""


def _case():
    return {
        "case_id": "AJ-001",
        "question": "How do canaliculi help osteocytes receive nutrients?",
        "draft": "The sources do not mention nutrient receipt [ev_001].",
        "sources": audit.parse_packet(PACKET)["sources"],
        "source_scope": audit.SOURCE_SCOPE,
    }


def _rating():
    return {
        "case_id": "AJ-001",
        "requested_help_sufficiency": "sufficient",
        "full_answer_sufficiency": "sufficient",
        "source_quotes": [
            {
                "source_id": "ev_001",
                "quote": "receive nutrients via long cytoplasmic processes",
            }
        ],
        "factual_correct": False,
        "citations_support_claims": False,
        "requested_help_complete": False,
        "within_help_level": True,
        "publishable_as_written": False,
        "issue_types": ["misstated_source_limit", "citation_mismatch"],
        "reason": "The actual cited source explicitly says osteocytes receive nutrients via canaliculi.",
    }


def test_packet_parsing_binds_official_source_and_actual_marker():
    parsed = audit.parse_packet(PACKET)
    assert parsed["original_packet_id"] == "RD-001"
    assert parsed["sources"][0]["pages"] == [223]
    assert parsed["sources"][0]["text_sha256"] == audit.sha256(
        parsed["sources"][0]["text"].encode("utf-8")
    )
    with pytest.raises(ValueError, match="markers differ"):
        audit.parse_packet(PACKET.replace("[ev_001].", "[ev_999].", 1))
    with pytest.raises(ValueError, match="official OpenStax"):
        audit.parse_packet(PACKET.replace("assets.openstax.org", "example.org"))


def test_rating_requires_exact_quote_and_consistent_release_gate():
    assert audit.validate_rating(_rating(), _case())["publishable_as_written"] is False
    wrong = _rating()
    wrong["source_quotes"] = [{"source_id": "ev_001", "quote": "imagined quotation"}]
    with pytest.raises(ValueError, match="exact substring"):
        audit.validate_rating(wrong, _case())
    wrong = _rating()
    wrong["publishable_as_written"] = True
    with pytest.raises(ValueError, match="known defect"):
        audit.validate_rating(wrong, _case())


def test_freeze_rejects_changed_packet_and_keeps_verdict_hidden(tmp_path: Path):
    root = tmp_path / "reviewer"
    relative = "draft_reviews/RD-001/packet.md"
    packet = root / relative
    packet.parent.mkdir(parents=True)
    packet.write_text(PACKET, encoding="utf-8")
    (root / "MANIFEST.json").write_bytes(
        audit.canonical(
            {"files": [{"path": relative, "sha256": audit.sha256(packet.read_bytes())}]}
        )
    )
    private = tmp_path / "private"
    public = tmp_path / "public.json"
    receipt = audit.freeze(root, [relative], private, public)
    assert receipt["scheduled"] == 1
    assert receipt["online_checker_verdicts_available"] is False
    offline = audit.preflight(private, public, tmp_path / "preflight.json")
    assert offline["mechanically_valid_cited_excerpt_cases"] == 1
    assert offline["semantic_labels"] == 0
    assert offline["provider_calls"] == 0
    assert (private / "reviewer-1-blank.csv").is_file()
    frozen = audit.load_json(private / "freeze.json")
    assert "original_packet_id" not in json.dumps(frozen)
    assert (
        audit.load_json(private / "coordinator.json")["rows"][0]["original_packet_id"] == "RD-001"
    )
    with pytest.raises(FileExistsError):
        audit.freeze(root, [relative], private, public)
    packet.write_text(PACKET + "\nChanged later.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="bytes differ"):
        audit.freeze(root, [relative], tmp_path / "private2", tmp_path / "public2.json")


def test_mocked_judge_run_keeps_raw_private_and_reports_exact_denominator(
    tmp_path: Path, monkeypatch
):
    root = tmp_path / "reviewer"
    relative = "draft_reviews/RD-001/packet.md"
    packet = root / relative
    packet.parent.mkdir(parents=True)
    packet.write_text(PACKET, encoding="utf-8")
    (root / "MANIFEST.json").write_bytes(
        audit.canonical(
            {"files": [{"path": relative, "sha256": audit.sha256(packet.read_bytes())}]}
        )
    )
    private, selection, result = (
        tmp_path / "private",
        tmp_path / "selection.json",
        tmp_path / "result.json",
    )
    audit.freeze(root, [relative], private, selection)
    frozen = audit.load_json(private / "freeze.json")
    identity = frozen["cases"][0]["case_id"]
    rating = {**_rating(), "case_id": identity}

    class Adapter:
        def __init__(self, _config, *, api_key, retain_invalid_output):
            assert api_key == "test-only"
            assert retain_invalid_output is True

        def generate(self, _messages, **_kwargs):
            return SimpleNamespace(
                request_submitted=True,
                model="deepseek-flash",
                provider="openai_compatible",
                provider_request_id="test-only-id",
                raw_text=json.dumps(rating),
                error=None,
                usage={"input_tokens": 100, "output_tokens": 40, "cache_hit_input_tokens": 0},
            )

    monkeypatch.setenv("LLM_API_KEY", "test-only")
    receipt = audit.run(
        private,
        selection,
        result,
        tmp_path / "absent.env",
        price_period="off_peak",
        adapter_factory=Adapter,
    )
    assert receipt["terminal"] == 1
    assert receipt["states"] == {"rated": 1}
    assert receipt["potential_false_block_ai_only"] == 0
    assert receipt["submitted_provider_calls_known"] == 1
    assert receipt["price_period"] == "off_peak"
    assert receipt["human_ratings"] == 0
    assert "receive nutrients" not in result.read_text(encoding="utf-8")
    assert "receive nutrients" in (private / "outcomes" / f"{identity}.json").read_text(
        encoding="utf-8"
    )
