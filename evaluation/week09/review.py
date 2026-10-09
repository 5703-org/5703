"""Blinded review of exact accepted and rejected drafts with strict score import."""

import csv
import hashlib
import html
import json
from pathlib import Path
import random

from generation.joint_policy import policy as teaching_policy
from .diagnostics import draft_observations

LABELS = (
    "context_sufficient",
    "draft_correct",
    "useful",
    "within_step",
    "citation_support",
    "coverage_complete",
    "cumulative_leak",
    "publication_appropriate",
)
FIELDS = ("blind_id", "reviewer_id", "reviewer_name", *LABELS, "reason", "source_location")
VALUES = {"yes", "no", "partial", "unsure", "not_applicable"}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


GUIDE = """# Independent draft review

Review the exact response, actual displayed citations and prior exposure in each packet. Use the official source anchors to check the facts and necessary conditions. The packet can contain a draft that was never shown to a learner. Publication decisions, model identities and experimental arms are hidden. Assess content independently.

Enter your name and use yes, no, partial or unsure for each applicable dimension. Use not_applicable for textbook citation support in general-knowledge mode, and for within_step and cumulative_leak in a direct full answer. Leave every semantic field blank when no draft is available. An empty model response has no draft to score. Preserve all blind IDs and rows.

- context_sufficient: the textbook evidence actually submitted to the model contains the necessary knowledge to answer the original question. Use model_input_evidence and read its scope and uncertainty. retrieved_candidates are retrieval context only and may include material removed before generation; do not count those unsubmitted passages as model input. When only request-level submitted evidence is available, its exact use in this draft revision is unverified; use unsure when that uncertainty affects your judgment. If submitted evidence is unavailable, use unsure. Use not_applicable for general knowledge.
- draft_correct: the response is accurate under the question's conditions; it contains no unsupported inference. Check signs, units, negation and assumptions.
- useful: the response supplies useful requested help or actionable feedback.
- within_step: a hint respects the stated step and help allowance.
- citation_support: the actual displayed sources jointly support the factual assertions they accompany and preserve material conditions. Pure procedural guidance can have no factual assertions; use not_applicable with an explanation.
- coverage_complete: a full answer covers the necessary question points; a hint addresses the intended current step. A supported partial answer is marked partial and its gap is described.
- cumulative_leak: this hint and its displayed sources, combined with prior exposure, reveal protected later conclusions.
- publication_appropriate: your overall independent yes/no/unsure decision on whether this exact draft should be delivered for this request. A useful, correctly qualified partial answer can be appropriate. Keep this decision separate from whether context covers the entire original question.

Write a concrete reason and source location, particularly for no, partial and unsure. Read the complete cited passage, including exceptions. Automatic checker decisions are withheld. Use one stable name per form. Two different reviewers work independently; disagreements and later adjudication are preserved separately. Names record team-attributed identity. Read current_step and allowed_disclosure from the common request contract; experimental planning identities remain hidden. These forms measure response quality and checker agreement, not delayed learning gains.
"""


def submitted_evidence_scope(record, observation):
    """Recover exact initial model evidence only from a matching transport hash.

    Request-level selected evidence is never relabelled as a later draft's
    exact input. A malformed/missing trace remains an explicit uncertainty.
    """
    outcome = record.get("outcome") or {}
    draft = observation["draft"]
    messages = outcome.get("messages") or []
    initial_hash = hashlib.sha256(
        json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    attempts = outcome.get("attempts") or []
    initial_attempt = next(
        (
            a
            for a in reversed(attempts)
            if a.get("stage") in {"generation", "generation_format_repair"}
        ),
        None,
    )
    matching = bool(
        initial_attempt
        and initial_attempt.get("prompt_hash") == initial_hash
        and initial_attempt.get("request_submitted") is True
    )
    if matching and draft.get("revision") == 0:
        for message in messages:
            content = message.get("content", "")
            if not content.startswith("CONTEXT_DATA_JSON:\n"):
                continue
            try:
                context = json.loads(content.removeprefix("CONTEXT_DATA_JSON:\n"))
            except (ValueError, TypeError):
                continue
            evidence = context.get("CURRENT_EVIDENCE")
            if isinstance(evidence, list):
                return {
                    "evidence": evidence,
                    "scope": "initial_generation_model_input",
                    "per_revision_verified": True,
                    "revision": 0,
                    "provenance": "Recorded generation messages match a submitted attempt prompt hash.",
                    "uncertainty": "The initial draft evidence is tied to the matching submitted generation input. Later revisions have separate scope records.",
                }
    if "evidence" in outcome:
        return {
            "evidence": outcome.get("evidence") or [],
            "scope": "request_level_submitted_evidence",
            "per_revision_verified": False,
            "revision": None,
            "provenance": "GenerationOutcome.evidence; submitted source inventory for the request.",
            "uncertainty": "A revision-specific matching input trace is unavailable. Do not assume this request-level inventory proves every passage was supplied to this exact revision.",
        }
    return {
        "evidence": [],
        "scope": "unavailable",
        "per_revision_verified": False,
        "revision": None,
        "provenance": "No submitted evidence receipt is available.",
        "uncertainty": "Retrieved candidates cannot establish what the model received. Rate context sufficiency unsure in textbook mode.",
    }


def review_task_boundary(request):
    """Use the common frozen request contract; never expose an arm-specific plan."""
    context = request.get("teaching_context") or {}
    common = teaching_policy(request.get("teaching_condition", "T2"), context)
    return {
        "current_step": context.get("current_step"),
        "turn_role": context.get("turn_role", "request"),
        "task_type": common["task_type"],
        "allowed_disclosure": {
            "help_level": common["help_level"],
            "constraint": common["help_constraint"],
            "complete_answer_allowed": common["teaching_mode"] == "direct",
            "preserve_conditions_and_units": True,
            "consider_answer_sources_and_prior_exposure": common["teaching_mode"] == "hint",
        },
        "boundary_source": "Frozen request context and common teaching disclosure contract",
    }


def integrity_files():
    return ["coordinator-only/mapping.json"] + [
        reviewer + "/" + name
        for reviewer in ("reviewer-1", "reviewer-2")
        for name in ("packets.json", "SCORING_GUIDE.md", "review.html")
    ]


def verify_integrity(folder):
    try:
        receipt = json.loads((folder / "review-integrity.json").read_text(encoding="utf-8"))
        files = receipt["files"]
        if receipt["schema"] != "week09_review_integrity_v1" or set(files) != set(
            integrity_files()
        ):
            raise ValueError("Invalid review integrity manifest")
        for name, expected in files.items():
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
                raise ValueError("Review evidence integrity check failed")
    except (OSError, KeyError, TypeError) as exc:
        raise ValueError("Review integrity manifest or evidence is unavailable") from exc


def export(records, cases, destination: Path, *, seed=570309):
    if destination.exists():
        raise ValueError("Use a new review directory; preserve prior forms and scores")
    case_lookup = {case["id"]: case for case in cases}
    packets, mappings = [], []
    for record in records:
        schedule = record.get("schedule") or {}
        request = record.get("request") or {}
        case = case_lookup.get(schedule.get("case_id"), {})
        observations = draft_observations(record)
        for observation in observations:
            if observation["projection_binding"] == "mismatch":
                raise ValueError(
                    "Draft/checker projection mismatch; resolve before independent review"
                )
            original_id = str(schedule.get("id") or request.get("request_id"))
            identity = (
                f"{seed}:{original_id}:{observation['revision']}:{observation['projection_hash']}"
            )
            blind_id = "R" + hashlib.sha256(identity.encode()).hexdigest()[:16]
            context = request.get("teaching_context") or {}
            projection = observation["draft"].get("projection") or {}
            packet = {
                "blind_id": blind_id,
                "question": request.get("question") or case.get("question"),
                "original_problem": context.get("current_problem") or case.get("question"),
                "answer_mode": request.get("answer_mode", schedule.get("answer_mode", "textbook")),
                "teaching_mode": context.get("teaching_mode", "direct"),
                "help_level": review_task_boundary(request)["allowed_disclosure"]["help_level"],
                **review_task_boundary(request),
                "pending_question": context.get("pending_tutor_question"),
                "prior_exposure": context.get("delivered_turns") or [],
                "response": observation["draft"].get("response"),
                "citation_views": projection.get("citation_views") or [],
                "model_input_evidence": submitted_evidence_scope(record, observation),
                "retrieved_candidates": request.get("evidence")
                or case.get("retrieval", {}).get("evidence")
                or [],
                "source_anchors": case.get("source_anchors") or [],
                "required_points": case.get("required_points") or [],
                "forbidden_inferences": case.get("forbidden_inferences") or [],
            }
            packets.append(packet)
            mappings.append(
                {
                    "blind_id": blind_id,
                    "schedule": schedule,
                    "revision": observation["revision"],
                    "projection_hash": observation["projection_hash"],
                    "checker_accepted": (observation["checker"] or {}).get("accepted"),
                    "published": observation["draft"].get("published", False),
                    "answer_mode": packet["answer_mode"],
                    "teaching_mode": packet["teaching_mode"],
                    "model_input_evidence_scope": packet["model_input_evidence"]["scope"],
                    "model_input_per_revision_verified": packet["model_input_evidence"][
                        "per_revision_verified"
                    ],
                }
            )
    if len({p["blind_id"] for p in packets}) != len(packets):
        raise ValueError("Duplicate review draft identity")
    random.Random(seed).shuffle(packets)
    destination.mkdir(parents=True)
    write(
        destination / "coordinator-only" / "mapping.json",
        {"schema": "week09_draft_review_v1", "rows": mappings},
    )
    for reviewer in ("reviewer-1", "reviewer-2"):
        folder = destination / reviewer
        write(folder / "packets.json", {"schema": "week09_blind_drafts_v1", "packets": packets})
        (folder / "SCORING_GUIDE.md").write_text(GUIDE, encoding="utf-8")
        with (folder / "ratings.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows({"blind_id": p["blind_id"], "reviewer_id": reviewer} for p in packets)
        body = "".join(
            "<details><summary>"
            + html.escape(p["blind_id"])
            + "</summary><pre>"
            + html.escape(json.dumps(p, indent=2, ensure_ascii=False))
            + "</pre></details>"
            for p in packets
        )
        (folder / "review.html").write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Week 9 independent draft review</title><style>body{font:16px/1.55 Arial,sans-serif;max-width:1000px;margin:24px auto;padding:0 16px}details{border:1px solid #aaa;padding:12px;margin:12px 0}summary{cursor:pointer;font-weight:bold}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}</style><h1>Week 9 independent draft review</h1><p>Read SCORING_GUIDE.md and record your independent ratings in ratings.csv. Expand a case to inspect its exact draft and sources.</p>'
            + body
            + "</html>",
            encoding="utf-8",
        )
    write(
        destination / "review-integrity.json",
        {
            "schema": "week09_review_integrity_v1",
            "files": {
                name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
                for name in integrity_files()
            },
            "editable_forms_excluded": True,
        },
    )
    receipt = {
        "packets": len(packets),
        "blank_rows": len(packets) * 2,
        "human_ratings": 0,
        "drafts_from_requests": len(records),
    }
    write(destination / "export-verification.json", receipt)
    return receipt


def import_reviews(folder: Path, forms: list[Path]):
    verify_integrity(folder)
    mapping = json.loads(
        (folder / "coordinator-only" / "mapping.json").read_text(encoding="utf-8")
    )["rows"]
    lookup = {row["blind_id"]: row for row in mapping}
    if len(lookup) != len(mapping):
        raise ValueError("Duplicate coordinator identity")
    all_rows = []
    reviewers: set[str] = set()
    submitted_names: set[str] = set()
    for form in forms:
        with form.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or []) != FIELDS:
                raise ValueError("Unexpected review columns")
            rows = list(reader)
        ids = [r["blind_id"] for r in rows]
        if len(set(ids)) != len(ids) or set(ids) != set(lookup):
            raise ValueError("Every expected draft must occur exactly once per reviewer")
        identities = {r["reviewer_id"] for r in rows}
        if (
            len(identities) != 1
            or not identities <= {"reviewer-1", "reviewer-2"}
            or reviewers & identities
        ):
            raise ValueError("Invalid or duplicate reviewer identity")
        reviewers.update(identities)
        names = {
            " ".join(row["reviewer_name"].split()).casefold()
            for row in rows
            if any(row[key] for key in LABELS)
        }
        if "" in names:
            raise ValueError("Actual ratings require a reviewer name and reason")
        if len(names) > 1:
            raise ValueError("Use one stable reviewer name per scored form")
        if names & submitted_names:
            raise ValueError("Independent forms require distinct reviewer names")
        submitted_names.update(names)
        for row in rows:
            for key in LABELS:
                if row[key] and row[key] not in VALUES:
                    raise ValueError(f"Invalid {key} rating")
            if row["publication_appropriate"] not in {"", "yes", "no", "unsure"}:
                raise ValueError("Publication appropriateness requires yes, no or unsure")
            scored = any(row[key] for key in LABELS)
            if scored and (not row["reviewer_name"].strip() or not row["reason"].strip()):
                raise ValueError("Actual ratings require a reviewer name and reason")
            meta = lookup[row["blind_id"]]
            publishable = {"yes": True, "no": False}.get(row["publication_appropriate"])
            all_rows.append(
                {
                    **row,
                    "scored": scored,
                    "publishable": publishable,
                    "checker_accepted": meta["checker_accepted"],
                }
            )
    comparable = [
        r for r in all_rows if r["publishable"] is not None and type(r["checker_accepted"]) is bool
    ]
    positive = [r for r in comparable if r["publishable"]]
    negative = [r for r in comparable if not r["publishable"]]
    return {
        "schema": "week09_human_review_import_v1",
        "rows": all_rows,
        "reviewers_submitted": sorted(reviewers),
        "scored_rows": sum(r["scored"] for r in all_rows),
        "comparable_ratings": len(comparable),
        "human_publishable_ratings": len(positive),
        "human_unpublishable_ratings": len(negative),
        "false_block_rate": sum(not r["checker_accepted"] for r in positive) / len(positive)
        if positive
        else None,
        "false_release_rate": sum(r["checker_accepted"] for r in negative) / len(negative)
        if negative
        else None,
        "unit": "Independent reviewer-draft ratings; reviewers are not independent learner observations.",
        "adjudicated": False,
        "reviewer_identity_scope": "Distinct normalized names are reviewer attribution, not independently verified identity.",
    }
