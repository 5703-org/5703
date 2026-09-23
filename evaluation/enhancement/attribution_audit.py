"""Independent, read-only verification of frozen citation-study source mappings.

No generation, retrieval, database, model or private reference-answer imports.
Character offsets are Python Unicode codepoints in cleaned SourceUnit text.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics

STRATEGIES = ("paragraph", "posthoc_spans", "preselected_spans")


def sha(value: str | bytes) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def digest(value) -> str:
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def check(condition, message):
    if not condition:
        raise ValueError(message)


def index(values, key):
    result = {v[key]: v for v in values}
    check(len(result) == len(values), "Duplicate " + key)
    return result


def slice_exact(text, start, end, expected):
    check(type(start) is int and type(end) is int, "Noninteger offsets")
    check(0 <= start < end <= len(text), "Out-of-bounds offsets")
    check(text[start:end] == expected, "Exact substring differs")


def verify_mapping(mapping):
    """Independently verify full frozen chunk construction, without runtime mapper."""
    text = mapping["chunk_text"]
    check(sha(text) == mapping["chunk_hash"], "Chunk hash differs")
    units = index(mapping["units"], "id")
    for unit in units.values():
        check(sha(unit["cleaned_text"]) == unit["text_hash"], "Cleaned unit hash differs")
        if "raw_text" in unit:
            check(sha(unit["raw_text"]) == unit["raw_text_hash"], "Raw unit hash differs")
    previous = 0
    for span in sorted(mapping["spans"], key=lambda s: s["chunk_start"]):
        unit = units[span["unit_id"]]
        text_piece = text[span["chunk_start"] : span["chunk_end"]]
        slice_exact(text, span["chunk_start"], span["chunk_end"], text_piece)
        slice_exact(unit["cleaned_text"], span["start"], span["end"], text_piece)
        check(span["page"] == unit["page"], "Span physical page differs")
        check(span["chunk_start"] >= previous, "Overlapping chunk spans")
        check(not text[previous : span["chunk_start"]].strip(), "Unmapped nonwhite chunk text")
        previous = span["chunk_end"]
    check(not text[previous:].strip(), "Unmapped chunk tail")
    return units


def verify_fragment(fragment, evidence, mapping, units):
    for key in ("asset_id", "processing_id", "document_version_id"):
        check(fragment[key] == mapping[key], "Fragment " + key + " differs")
    for key in ("chunk_id", "evidence_id"):
        check(fragment[key] == evidence[key], "Fragment evidence identity differs")
    unit = units[fragment["source_unit_id"]]
    exact = fragment["exact_text"]
    check(fragment["text_hash"] == sha(exact), "Fragment hash differs")
    check(fragment["offset_basis"] == "cleaned_source_unit_unicode", "Unknown offset basis")
    check(fragment["page"] == unit["page"], "Fragment physical page differs")
    slice_exact(unit["cleaned_text"], fragment["start"], fragment["end"], exact)
    slice_exact(mapping["chunk_text"], fragment["chunk_start"], fragment["chunk_end"], exact)
    check(
        any(
            s["unit_id"] == unit["id"]
            and s["start"] <= fragment["start"] < fragment["end"] <= s["end"]
            and fragment["chunk_start"] == s["chunk_start"] + fragment["start"] - s["start"]
            for s in mapping["spans"]
        ),
        "Fragment does not belong to an exact chunk span",
    )
    identity = [
        "cleaned_unit_offsets_v1",
        mapping["document_version_id"],
        mapping["processing_id"],
        fragment["chunk_id"],
        unit["id"],
        fragment["start"],
        fragment["end"],
        sha(exact),
    ]
    expected = "span_" + sha(json.dumps(identity, separators=(",", ":")))[:32]
    check(fragment["fragment_id"] == expected, "Fragment deterministic identity differs")


def union_length(fragments):
    groups = defaultdict(list)
    for f in fragments:
        groups[(f["processing_id"], f["source_unit_id"])].append((f["start"], f["end"]))
    total = 0
    for intervals in groups.values():
        end = -1
        for left, right in sorted(intervals):
            total += max(0, right - max(left, end))
            end = max(end, right)
    return total


def inspect_outcome(outcome, retrieval):
    """Return public metadata only; rejected draft text is never exported."""
    issues = []
    counts = Counter()

    def attempt(scope, fn):
        try:
            fn()
            counts[scope + "_passed"] += 1
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            issues.append({"scope": scope, "reason": str(exc)[:160]})

    evidence = index(outcome.get("evidence") or [], "evidence_id")
    attribution = outcome.get("attribution") or {}
    fragments = index(attribution.get("fragments") or [], "fragment_id")
    claims = index(attribution.get("claims") or [], "claim_id")
    ranges = index(attribution.get("evidence_ranges") or [], "evidence_id")
    source_map = retrieval["source_map"]
    original_evidence = {e["chunk_id"]: e for e in retrieval.get("evidence", [])}
    all_units = {}
    for chunk_id, mapping in source_map.items():
        attempt("full_chunk", lambda m=mapping: verify_mapping(m))
        all_units.update({(mapping["processing_id"], u["id"]): u for u in mapping["units"]})
    for e in evidence.values():

        def verify_evidence(e=e):
            mapping = source_map[e["chunk_id"]]
            check(e["text_hash"] == sha(e["text"]), "Submitted evidence hash differs")
            for key in ("processing_id", "asset_id"):
                check(e[key] == mapping[key], "Submitted evidence " + key + " differs")
            if original_evidence:
                original = original_evidence[e["chunk_id"]]
                for key in ("source_title", "section", "pages", "source_url", "license"):
                    check(
                        e.get(key) == original.get(key), "Frozen source locator " + key + " differs"
                    )
            if e["evidence_id"] in ranges:
                r = ranges[e["evidence_id"]]
                check(r["chunk_id"] == e["chunk_id"], "Selected range chunk differs")
                check(r["chunk_text_hash"] == mapping["chunk_hash"], "Selected range hash differs")
                slice_exact(mapping["chunk_text"], r["chunk_start"], r["chunk_end"], e["text"])
            else:
                check(e["text"] == mapping["chunk_text"], "Unrecorded evidence subrange")

        attempt("submitted_evidence", verify_evidence)
    for fragment in fragments.values():

        def verify(f=fragment):
            e = evidence[f["evidence_id"]]
            mapping = source_map[f["chunk_id"]]
            verify_fragment(f, e, mapping, index(mapping["units"], "id"))
            r = ranges.get(e["evidence_id"])
            if r:
                check(
                    r["chunk_start"] <= f["chunk_start"] < f["chunk_end"] <= r["chunk_end"],
                    "Fragment is outside submitted range",
                )

        attempt("fragment", verify)
    response = outcome.get("response")
    published = bool(
        response and not outcome.get("error") and response.get("response_type") == "answer"
    )
    drafts = outcome.get("drafts") or []
    draft = None
    draft_revision = None
    for retained in reversed(drafts):
        candidate = retained.get("response") or {}
        if all(
            (candidate.get(c["answer_field"]) or "")[c["start"] : c["end"]] == c["text"]
            for c in claims.values()
        ):
            draft = candidate
            draft_revision = retained.get("revision")
            break
    claim_response = response or draft
    for claim in claims.values():

        def verify(c=claim):
            check(claim_response is not None, "Claim has no response or retained draft")
            slice_exact(claim_response[c["answer_field"]], c["start"], c["end"], c["text"])
            inline = set(re.findall(r"\[(ev_\d+)\]", c["text"]))
            check(inline == set(c["evidence_ids"]), "Claim inline citation IDs differ")
            for fid in c["fragment_ids"]:
                f = fragments[fid]
                if inline:
                    check(f["evidence_id"] in inline, "Claim fragment cites another evidence ID")

        attempt("claim", verify)
        if claim["fragment_ids"] and not claim["evidence_ids"]:
            counts["linked_claims_without_inline_ids"] += 1
            counts["linked_" + claim["answer_field"] + "_claims_without_inline_ids"] += 1
    projection = outcome.get("delivered_projection")
    if published:

        def verify_projection():
            check(projection is not None, "Published answer has no projection")
            body = {k: v for k, v in projection.items() if k != "content_hash"}
            check(
                sha(json.dumps(body, sort_keys=True, ensure_ascii=False))
                == projection["content_hash"],
                "Delivered projection hash differs",
            )
            check(projection["response"] == response, "Projection response differs")
            inline = set(re.findall(r"\[(ev_\d+)\]", response["answer_text"]))
            check(inline == set(response["citations"]), "Response inline/list citations differ")
            check(set(response["citations"]) <= set(evidence), "Unsubmitted citation")
            for view in projection["citation_views"]:
                e = evidence[view["evidence_id"]]
                check(
                    view["preview"] == "".join(s["text"] for s in view["segments"]),
                    "Preview differs",
                )
                check(
                    view["source_title"] == e["source_title"]
                    and view["section"] == e["section"]
                    and view["pages"] == e["pages"],
                    "Source locator differs",
                )
                for segment in view["segments"]:
                    if segment["text"] == "\n…\n" and not segment["fragment_ids"]:
                        continue
                    check(segment["text"] in e["text"], "Visible text is not submitted source text")
                    for fid in segment["fragment_ids"]:
                        f = fragments[fid]
                        check(
                            f["evidence_id"] == e["evidence_id"],
                            "Visible fragment evidence differs",
                        )
                        check(f["exact_text"] in segment["text"], "Visible fragment text differs")
            accepted = [c for c in outcome.get("checks", []) if c.get("accepted")]
            check(bool(accepted), "Published live answer has no accepted check")
            check(
                accepted[-1].get("delivered_projection_hash", accepted[-1]["projection_hash"])
                == projection["content_hash"],
                "Recorded delivered projection differs",
            )

        attempt("published_projection", verify_projection)
    selected_ids = {fid for c in claims.values() for fid in c["fragment_ids"]}
    selected = [fragments[fid] for fid in selected_ids if fid in fragments]
    selected_units = {(f["processing_id"], f["source_unit_id"]) for f in selected}
    lengths = {
        "submitted_evidence_characters": sum(len(e["text"]) for e in evidence.values()),
        "mapped_candidate_fragment_characters": sum(
            len(f["exact_text"]) for f in fragments.values()
        ),
        "claim_selected_fragment_characters": sum(len(f["exact_text"]) for f in selected),
        "claim_selected_unique_source_characters": union_length(selected),
        "full_cleaned_selected_source_unit_characters": sum(
            len(all_units[k]["cleaned_text"]) for k in selected_units
        )
        if selected_units <= all_units.keys()
        else None,
        "delivered_source_characters": sum(
            len(v["preview"]) for v in (projection or {}).get("citation_views", [])
        )
        if published
        else None,
    }
    return {
        "published_answer": published,
        "claim_text_scope": "published_response"
        if response
        else "retained_private_draft"
        if draft
        else "unavailable",
        "matched_private_draft_revision": draft_revision if not response else None,
        "checks": dict(counts),
        "structural_issues": issues,
        "attribution_available": bool(attribution),
        "mapped_fragments": len(fragments),
        "claims": len(claims),
        "selected_fragments": len(selected),
        "mapping_quality": dict(Counter(f["mapping_quality"] for f in fragments.values())),
        "selected_block_kinds": dict(Counter(f["block_kind"] for f in selected)),
        "selected_incomplete_blocks": sum(not f["complete_block"] for f in selected),
        "lengths": lengths,
    }


def direct_primary(response, error, judgment):
    return bool(
        response
        and response.get("response_type") == "answer"
        and not error
        and judgment
        and judgment["supported"] == 1
        and judgment["complete_answer"] == 1
        and judgment["fact_error"] == 0
    )


def audit(run: Path, *, expected_tasks=60):
    reads = {}

    def load(path):
        data = path.read_bytes()
        reads[str(path)] = sha(data)
        value = json.loads(data)
        if "content_sha256" in value:
            check(
                value["content_sha256"]
                == digest({k: v for k, v in value.items() if k != "content_sha256"}),
                "Frozen content hash differs: " + path.name,
            )
            value = {k: v for k, v in value.items() if k != "content_sha256"}
        return value

    manifest = load(run / "run-manifest.json")
    planned = manifest["planned"]
    index(planned, "id")
    check(manifest["experiment"] == "citations", "Citation experiment required")
    check(
        len(planned) == manifest["planned_count"] == expected_tasks * 3,
        "Planned denominator differs",
    )
    groups = defaultdict(set)
    for item in planned:
        groups[item["task_id"]].add(item["condition"])
    check(
        len(groups) == expected_tasks and all(v == set(STRATEGIES) for v in groups.values()),
        "Each task requires all three strategies",
    )
    source = Path(manifest["source_directory"])
    if not source.is_dir():
        source = run.parent / source.name
    source_manifest = load(source / "manifest.json")
    check(digest(source_manifest) == manifest["source_manifest_sha256"], "Source manifest differs")
    # Private reference content is hashed for identity only; no task labels are read/exported.
    dataset = load(source / "private-tasks.json")
    check(
        digest(dataset) == manifest["dataset_sha256"] == source_manifest["dataset_sha256"],
        "Dataset differs",
    )
    del dataset
    analysis = load(run / "analysis.json")
    check(analysis["run_manifest_sha256"] == digest(manifest), "Analysis run differs")
    judge_manifest = load(run / "judge-manifest.json")
    check(judge_manifest["run_manifest_sha256"] == digest(manifest), "Judge run differs")
    rows, examples, problems = [], [], []
    seen_books, seen_strategies = set(), set()
    for item in planned:
        row = {
            **item,
            "result_present": False,
            "published_answer": False,
            "judged": False,
            "direct_primary_positive": False,
            "structural_issues": [],
            "error_code": None,
        }
        path = run / "results" / (item["id"] + ".json")
        if not path.exists():
            rows.append(row)
            continue
        result = load(path)
        check(
            all(result[k] == item[k] for k in ("id", "task_id", "condition", "turn")),
            "Result schedule differs",
        )
        retrieval = load(source / "retrieval" / (item["task_id"] + ".json"))
        check(
            digest(retrieval)
            == result["retrieval_sha256"]
            == manifest["retrieval_hashes"][item["task_id"]],
            "Retrieval identity differs",
        )
        outcome = result["outcome"]
        row.update(inspect_outcome(outcome, retrieval))
        row["result_present"] = True
        row["error_code"] = (outcome.get("error") or {}).get("code")
        row["response_type"] = (outcome.get("response") or {}).get("response_type")
        judgment_path = run / "judgments" / (item["id"] + ".json")
        verdict = None
        if judgment_path.exists():
            judged = load(judgment_path)
            check(judged["id"] == item["id"], "Judge identity differs")
            row["judge_state"] = judged["state"]
            verdict = judged.get("judgment") if judged["state"] == "judged" else None
            row["judged"] = verdict is not None
            row["automatic_scores"] = {k: v for k, v in (verdict or {}).items() if type(v) is int}
        row["direct_primary_positive"] = direct_primary(
            outcome.get("response"), outcome.get("error"), verdict
        )
        rows.append(row)
        if row["error_code"] and not any(p["kind"] == "generation_failure" for p in problems):
            problems.append(
                {
                    "kind": "generation_failure",
                    "id": item["id"],
                    "error": outcome["error"],
                    "claim_text_scope": row["claim_text_scope"],
                    "structural_issues": row["structural_issues"],
                }
            )
        if (
            verdict
            and verdict["within_scope"] == 0
            and not any(p["kind"] == "direct_hint_allowance_conflict" for p in problems)
        ):
            # Do not export private evaluation labels embedded in the judge explanation.
            problems.append(
                {
                    "kind": "direct_hint_allowance_conflict",
                    "id": item["id"],
                    "scores": row["automatic_scores"],
                    "finding": "Direct answer received within_scope=0 while complete_answer=1; judge input also supplies hint-only permitted_help. Raw explanation retained privately.",
                }
            )
        if row["published_answer"]:
            attrs = outcome["attribution"]
            fragments = index(attrs["fragments"], "fragment_id")
            evidence = index(outcome["evidence"], "evidence_id")
            for claim in attrs["claims"]:
                if (
                    claim["fragment_ids"]
                    and not claim["evidence_ids"]
                    and claim["answer_field"] == "answer_text"
                    and not any(p["kind"] == "body_claim_without_inline_marker" for p in problems)
                ):
                    problems.append(
                        {
                            "kind": "body_claim_without_inline_marker",
                            "id": item["id"],
                            "claim_id": claim["claim_id"],
                            "claim_text": claim["text"],
                            "finding": "Claim is linked privately to exact source fragments, but its own delivered body text contains no inline citation marker. This is a presentation/coverage concern, not a failed offset check.",
                        }
                    )
                for fid in claim["fragment_ids"]:
                    f = fragments[fid]
                    e = evidence[f["evidence_id"]]
                    if len(examples) < 5 and (
                        item["condition"] not in seen_strategies
                        or e["source_title"] not in seen_books
                    ):
                        excerpt = f["exact_text"][:300]
                        examples.append(
                            {
                                "id": item["id"],
                                "strategy": item["condition"],
                                "book": e["source_title"],
                                "section": e["section"],
                                "pdf_physical_page": f["page"],
                                "source_unit_id": f["source_unit_id"],
                                "processing_id": f["processing_id"],
                                "chunk_id": f["chunk_id"],
                                "fragment_id": fid,
                                "fragment_start": f["start"],
                                "fragment_end": f["end"],
                                "fragment_text_sha256": f["text_hash"],
                                "excerpt": excerpt,
                                "excerpt_end": f["start"] + len(excerpt),
                                "excerpt_is_complete_fragment": excerpt == f["exact_text"],
                                "mapping_quality": f["mapping_quality"],
                                "block_kind": f["block_kind"],
                                "structural_issues_in_outcome": row["structural_issues"],
                            }
                        )
                        seen_strategies.add(item["condition"])
                        seen_books.add(e["source_title"])
    summaries = {}
    for strategy in STRATEGIES:
        subset = [r for r in rows if r["condition"] == strategy]
        published = [r for r in subset if r["published_answer"]]
        lengths = {}
        for field in published[0]["lengths"] if published else []:
            values = [r["lengths"][field] for r in published if r["lengths"][field] is not None]
            lengths[field] = {
                "denominator_published_answers": len(values),
                "sum": sum(values),
                "mean": statistics.mean(values) if values else None,
                "median": statistics.median(values) if values else None,
            }
        summary = {
            "planned": len(subset),
            "terminal_results": sum(r["result_present"] for r in subset),
            "published_answers": len(published),
            "judged_answers": sum(r["judged"] for r in subset),
            "missing_results": sum(not r["result_present"] for r in subset),
            "errors": dict(Counter(r["error_code"] for r in subset if r["error_code"])),
            "nonerror_nonanswer": sum(
                r["result_present"] and not r["published_answer"] and not r["error_code"]
                for r in subset
            ),
            "outcomes_with_structural_issues": sum(bool(r["structural_issues"]) for r in subset),
            "published_with_structural_issues": sum(
                bool(r["structural_issues"]) for r in published
            ),
            "mapping_quality_all_retained_fragments": dict(
                sum((Counter(r.get("mapping_quality", {})) for r in subset), Counter())
            ),
            "checks": dict(sum((Counter(r.get("checks", {})) for r in subset), Counter())),
            "published_checks": dict(sum((Counter(r["checks"]) for r in published), Counter())),
            "published_selected_incomplete_blocks": sum(
                r["selected_incomplete_blocks"] for r in published
            ),
            "direct_primary_positive": sum(r["direct_primary_positive"] for r in subset),
            "direct_within_scope_zero": sum(
                r.get("automatic_scores", {}).get("within_scope") == 0 for r in subset
            ),
            "published_lengths": lengths,
        }
        expected = analysis["metrics"][strategy]
        summary["primary_matches_existing_analysis"] = (
            summary["direct_primary_positive"] / len(subset)
            == expected["complete_supported_answer_rate_all_planned"]
        )
        summaries[strategy] = summary
    unchanged = all(sha(Path(path).read_bytes()) == value for path, value in reads.items())
    return {
        "version": "independent_attribution_audit_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run": str(run),
        "run_manifest_sha256": digest(manifest),
        "planned": len(planned),
        "source_files_unchanged": unchanged,
        "read_files_sha256": reads,
        "automatic_source_audit": True,
        "independent_human_reviews": 0,
        "methods": [
            "Independent exact Unicode substring/hash/span/identity checks; no runtime mapper, models, DB or rejudging.",
            "All scheduled results retained, including errors/refusals and private-draft attribution; no failure text published.",
            "Lengths aggregate published answers only. Full cleaned units are reference context, not necessarily text displayed to learners.",
            "Selected fragment sums count each fragment ID once per answer; unique source lengths merge overlapping source-unit offsets. Requests repeat source text.",
            "Examples are the first scheduled linked sources introducing a strategy or book, capped at five; not semantic exemplars.",
        ],
        "strategies": summaries,
        "items": rows,
        "source_examples": examples,
        "problem_examples": problems[:3],
        "judge_protocol": {
            "direct_primary_excludes_within_scope_and_specific_help": True,
            "direct_input_contains_hint_only_permitted_help": True,
            "scope_zero_judgments": sum(s["direct_within_scope_zero"] for s in summaries.values()),
            "impact": "Direct scope ratings are contaminated and must not measure direct-answer success. Existing primary arithmetic excludes them and is independently reproduced. Other model ratings may still be influenced by conflicting input; not independent scientific acceptance. No ratings or frozen records changed.",
        },
        "limitations": [
            "Exact source mapping is not entailment, atomic semantic completeness, scientific correctness, relevance or visual/PDF fidelity.",
            "Raw text hashes are validated where present; offsets address cleaned source units, never raw PDF bytes.",
            "Source fragments and rejected drafts can be structurally valid despite a failed model support check.",
            "Full source-unit length is not actual UI exposure, reading time or evidence efficiency; successful-only lengths do not establish overall method quality.",
            "Same-family automatic judges and online checks are not independent human ratings.",
        ],
    }


def markdown(report):
    lines = [
        "# Formal citation source-attribution audit",
        "",
        f"All {report['planned']} planned citation outcomes are accounted for. This is a read-only structural audit; independent human reviews: 0.",
        "",
        "| Strategy | Planned | Published | Errors | Non-answer | Published mapping issues |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, row in report["strategies"].items():
        lines.append(
            f"| {name} | {row['planned']} | {row['published_answers']} | {sum(row['errors'].values())} | {row['nonerror_nonanswer']} | {row['published_with_structural_issues']} |"
        )
    lines += [
        "",
        "Lengths below refer only to published answers. Full units are reference context, not the ordinary source preview. Counts repeat a source when different requests use it.",
        "",
        "| Strategy | Mean submitted chars | Mean selected unique chars | Mean visible source chars | Mean full selected units |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, row in report["strategies"].items():
        values = row["published_lengths"]
        fields = (
            "submitted_evidence_characters",
            "claim_selected_unique_source_characters",
            "delivered_source_characters",
            "full_cleaned_selected_source_unit_characters",
        )
        cells = [f"{values[f]['mean']:.1f}" if f in values else "unavailable" for f in fields]
        lines.append("| " + name + " | " + " | ".join(cells) + " |")
    lines += [
        "",
        f"The offline direct-answer judge received a hint-only allowance despite its complete-answer instruction. {report['judge_protocol']['scope_zero_judgments']} judged answers received within_scope=0. "
        + report["judge_protocol"]["impact"],
        "",
        "## Exact source examples",
        "",
    ]
    for example in report["source_examples"]:
        lines += [
            f"- **{example['id']}**: {example['book']}, {example['section']}, PDF physical page {example['pdf_physical_page']}; cleaned unit `{example['source_unit_id']}`, excerpt offsets {example['fragment_start']}–{example['excerpt_end']}. {example['mapping_quality']}; {example['block_kind']}.",
            f"  > {example['excerpt']}",
            "",
        ]
    lines += ["## Retained problematic examples", ""]
    for problem in report["problem_examples"]:
        detail = problem.get("finding") or (
            "Generation failed with "
            + problem["error"]["code"]
            + "; no answer was published. Retained private drafts remain in the original record."
        )
        lines.append(f"- **{problem['id']} — {problem['kind']}**: {detail}")
    lines += ["", "## Limits", ""] + ["- " + line for line in report["limitations"]]
    lines += [
        "",
        "The JSON companion contains every planned item, all structural findings, exact input-file hashes and separately scoped length denominators. Source records and judgments were not changed.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(
        not args.output.exists() and not args.output.with_suffix(".md").exists(),
        "Audit output already exists",
    )
    report = audit(args.run)
    report["audit_script_sha256"] = sha(Path(__file__).read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    with args.output.with_suffix(".md").open("x", encoding="utf-8") as stream:
        stream.write(markdown(report))
    print(
        json.dumps(
            {
                "planned": report["planned"],
                "strategies": report["strategies"],
                "source_files_unchanged": report["source_files_unchanged"],
            }
        )
    )


if __name__ == "__main__":
    main()
