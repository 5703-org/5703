"""Reconcile public terminal evidence into inputs for the nine English reports.

This utility creates JSON only. It never creates Word files or runs an artifact
marker. Missing or unfinished required evidence stops publication of report data.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "evidence/week08-enhancement/20260920"
sys.path.insert(0, str(HERE))
from build_reports import build_content, markdown, validate  # noqa: E402


INPUTS = {
    "protocol": (
        ROOT / "docs/execution/week08-enhancement-protocol-20260920.md",
        "Frozen enhancement protocol",
        "Prespecified comparisons, budgets, provenance and review methods.",
    ),
    "hints": (
        BASE / "formal-hints-analysis.json",
        "Formal hint comparison",
        "All 900 requests and task-paired model-assisted analysis; human ratings remain separate.",
    ),
    "citations": (
        BASE / "formal-citations-judge-v2-analysis.json",
        "Corrected direct-answer citation analysis",
        "Same 180 generated outcomes with corrected direct-answer judging; the original judge is retained.",
    ),
    "manifest": (
        BASE / "formal-hints-run-manifest.json",
        "Frozen formal execution",
        "Source, dataset, runtime, model, checker and call-budget identities.",
    ),
    "attribution": (
        BASE / "formal-attribution-audit.json",
        "Independent structural attribution audit",
        "Exact source relationships and published-only length measurements. Semantic fields from its original judge are excluded here.",
    ),
    "memory": (
        BASE / "memory-study-final-summary.json",
        "Memory comparison and separate judging",
        "All 36 authored conditions, state screens and 16 answer judgments; zero human ratings.",
    ),
    "memory_usage": (
        BASE / "memory-usage.json",
        "Memory attempt accounting",
        "185 unique reservations with reported usage, including extraction, summaries and separate judging.",
    ),
    "memory_humans": (
        BASE / "memory-human-review-status.json",
        "Memory independent review status",
        "Actual reviewer and rating counts with agreement left unavailable until collection.",
    ),
    "source_ui": (
        BASE / "frontend/live-source-browser-summary.json",
        "Claim source browser journey",
        "Actual approved preview, explicit expansion, keyboard and 1440/390 viewport checks.",
    ),
    "memory_ui": (
        BASE / "frontend/live-memory-browser-summary.json",
        "Memory browser journey",
        "Actual opt-in, source, edit conflict, retained draft, deletion and save Undo.",
    ),
    "teaching_ui": (
        BASE / "frontend/live-teaching-browser-summary.json",
        "Teaching browser journey",
        "Three saved hint/hint/full-answer requests and actual rendering receipts.",
    ),
    "teaching_events": (
        BASE / "backend/browser-teaching-exposures.json",
        "Teaching delivery and rendering",
        "Three published presentations with separate delivered and rendered event identities.",
    ),
    "portable": (
        BASE / "portable/source-parity-final.json",
        "Fresh CPU runtime parity",
        "Actual same-host fresh installation and explicitly enumerated deployed runtime subset.",
    ),
    "portable_app": (
        BASE / "portable/app-attempt1.json",
        "Fresh CPU application checks",
        "Actual isolated database, CPU retrieval, explicit mock/live paths and cancellation.",
    ),
    "gate": (
        BASE / "software-gate-final-attempt2/software_gate.json",
        "Final software verification",
        "Current gate stages with immutable before/after source snapshot; software behavior scope.",
    ),
    "gate_prior": (
        BASE / "software-gate-final/software_gate.json",
        "Retained first aggregate verification",
        "The old chat-input whitelist assertion failed; other stage results are retained beside the corrected verifier rerun.",
    ),
    "regression": (
        BASE / "regression/original110-attempt1.json",
        "Original live regression",
        "All 110 scheduled actual HTTP cases; structural and expected-state checks.",
    ),
    "faults": (
        BASE / "regression/isolated-fault-mapping.json",
        "Isolated failure checks",
        "Ten remaining catalogue IDs mapped to 14 controlled assertions; separate from live requests.",
    ),
    "costs": (
        BASE / "costs-summary.json",
        "Dated purpose-specific cost reconciliation",
        "Known provider usage at the dated CNY tariff, with missing usage and estimates identified.",
    ),
    "humans": (
        BASE / "human-materials.json",
        "Blinded independent review materials",
        "Actual exports for two reviewers; prepared forms do not constitute collected ratings.",
    ),
    "highlight_load": (
        BASE / "human-highlight-load.json",
        "Actual paired highlight material load",
        "148 claims and 296 paired presentations loaded in the browser; text/Unicode checks only, zero timed responses.",
    ),
    "migration": (
        BASE / "backend/main-migration-preservation.json",
        "Additive migration preservation",
        "Measured aggregates of 33 existing tables before and after the additive schema change.",
    ),
    "lifecycle": (
        BASE / "backend/live-lifecycle-attempt1-scope.json",
        "Retained live lifecycle scope",
        "Five actual requests, including the recorded memory-enabled context-limit failure.",
    ),
    "task_boundary": (
        BASE / "task-boundary/final-verification.json",
        "Post-study task boundary correction",
        "Separate HTTP task-resolution fix and verification after the frozen formal generation study.",
    ),
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def percent(value):
    return f"{100 * value:.1f}%"


def count_text(value):
    return f"{value:,}"


def metric(name, value, scope):
    return {"name": name, "value": str(value), "scope": scope}


def study(identity, label, phase, planned, outcomes, findings, metrics, limits, refs):
    accounted = sum(outcomes.values())
    return {
        "id": identity,
        "label": label,
        "phase": phase,
        "planned": planned,
        "accounted": accounted,
        "missing": planned - accounted,
        "outcomes": outcomes,
        "findings": findings,
        "metrics": metrics,
        "limitations": limits,
        "evidence_refs": refs,
    }


def ready_inputs():
    missing = [str(path.relative_to(ROOT)) for path, _, _ in INPUTS.values() if not path.is_file()]
    if missing:
        return {}, missing
    data = {key: load(path) for key, (path, _, _) in INPUTS.items() if path.suffix == ".json"}
    pending = []
    if data["regression"].get("status") in {None, "running", "pending"}:
        pending.append("original110 live regression is still running")
    if data["gate"].get("status") != "passed" or not data["gate"].get("source_files_unchanged"):
        pending.append("final software gate has not passed with unchanged source")
    return data, pending


def prepare(d):
    hints, citations, audit = d["hints"], d["citations"], d["attribution"]
    manifest, gate, regression = d["manifest"], d["gate"], d["regression"]
    memory, costs, portable = d["memory"], d["costs"], d["portable"]
    hm, cm = hints["metrics"], citations["metrics"]
    require(set(hm) == {"T0", "T1", "T2", "T3", "T4"}, "Hint conditions differ")
    require(
        set(cm) == {"paragraph", "posthoc_spans", "preselected_spans"}, "Citation strategies differ"
    )
    require(
        hints["experiment"] == "hints" and citations["experiment"] == "citations",
        "Study identities differ",
    )
    require(
        all(row["planned"] == row["completed"] == 180 for row in hm.values()),
        "All 900 hint outcomes required",
    )
    require(
        all(row["planned"] == row["completed"] == 60 for row in cm.values()),
        "All 180 citation outcomes required",
    )
    require(len(hints["items"]) == 900 and len(citations["items"]) == 180, "Study rows missing")
    require(
        len({row["id"] for row in hints["items"]}) == 900
        and len({row["id"] for row in citations["items"]}) == 180,
        "Duplicate study outcomes",
    )
    require(hints["run_manifest_sha256"] == manifest["content_sha256"], "Formal manifest mismatch")
    require(
        audit["source_files_unchanged"] and audit["planned"] == 180, "Structural audit incomplete"
    )
    require(
        citations["run_manifest_sha256"] == audit["run_manifest_sha256"],
        "Citation analysis and structural audit differ",
    )
    require(memory["planned"] == 36 and len(memory["conditions"]) == 3, "Memory schedule differs")
    require(
        d["memory_humans"]["actual_ratings"] == d["memory_humans"]["actual_reviewers"] == 0,
        "Reconcile new human memory ratings before publishing",
    )
    require(
        hints["human_evaluation"]["completed_ratings"]
        == citations["human_evaluation"]["completed_ratings"]
        == d["humans"]["human_ratings"]
        == 0,
        "Reconcile new human study ratings before publishing",
    )
    require(
        d["highlight_load"]["status"] == "passed" and d["highlight_load"]["ratings"] == 0,
        "Reconcile highlight material validation or new ratings",
    )
    require(
        portable["status"] == d["portable_app"]["status"] == "passed",
        "Actual fresh CPU proof required",
    )
    require(
        len(regression["cases"]) == len(regression["scheduled_ids"]) == 110,
        "All 110 live regression outcomes required",
    )
    require(
        {row["id"] for row in regression["cases"]} == set(regression["scheduled_ids"]),
        "Live regression identities differ",
    )
    require(
        all(
            row.get("job", {}).get("state") in {"succeeded", "failed", "cancelled"}
            for row in regression["cases"]
        ),
        "Nonterminal regression request",
    )
    require(
        d["faults"]["tests_passed"] == 14 and len(d["faults"]["fault_families"]) == 10,
        "Fault mapping differs",
    )
    require(
        all(row["status"] == "passed" for row in d["faults"]["fault_families"]),
        "Fault mapping contains failures",
    )

    pair = hints["paired_task_comparisons"]["T2_minus_T1"]
    primary = (
        f"T2 produced {hm['T2']['valid_hints_all_planned']}/180 valid hints ({percent(hm['T2']['valid_hint_rate_all_planned'])}), "
        f"compared with {hm['T1']['valid_hints_all_planned']}/180 ({percent(hm['T1']['valid_hint_rate_all_planned'])}) for T1. "
        f"The task-paired difference was {100 * pair['difference']:.2f} percentage points, with a 95% bootstrap interval "
        f"from {100 * pair['ci95'][0]:.2f} to {100 * pair['ci95'][1]:.2f} points."
    )
    reg_pass = sum(row["passed_automated_checks"] is True for row in regression["cases"])
    reg_states = Counter(row["job"]["state"] for row in regression["cases"])
    gate_checks = gate["checks"]
    require(all(row["exit_code"] == 0 for row in gate_checks), "Gate stage failure")
    xml_path = INPUTS["gate"][0].parent / "pytest.xml"
    require(xml_path.is_file(), "Final pytest count requires its actual XML")
    tests = ET.parse(xml_path).getroot().findall(".//testcase")
    py_pass = sum(
        not any(test.find(tag) is not None for tag in ("failure", "error", "skipped"))
        for test in tests
    )
    frontend_log = (INPUTS["gate"][0].parent / "frontend_tests.log").read_text(encoding="utf-8")
    frontend_log = re.sub(r"\x1b\[[0-9;]*m", "", frontend_log)
    fe_match = re.search(r"Tests\s+(\d+) passed", frontend_log)
    require(fe_match is not None, "Final frontend test count unavailable")
    fe_pass = int(fe_match.group(1))
    require(d["migration"]["status"] == "passed", "Migration preservation incomplete")
    require(
        d["task_boundary"]["status"] == "passed", "Post-study task boundary verification incomplete"
    )
    evidence = [
        {
            "id": key,
            "path": path.relative_to(ROOT).as_posix(),
            "title": title,
            "scope": scope,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for key, (path, title, scope) in INPUTS.items()
    ]
    model = manifest["model_config"]
    source = d["portable_app"]["corpus_after"]
    published_hint = sum(row["answered"] for row in hm.values())
    published_citation = sum(row["answered"] for row in cm.values())
    hint_outcomes = Counter(
        "published_answer" if row["answered"] else (row.get("generation_error") or "nonanswer")
        for row in hints["items"]
    )
    citation_outcomes = Counter(
        "published_answer" if row["answered"] else (row.get("generation_error") or "nonanswer")
        for row in citations["items"]
    )
    citation_sentences = []
    for key, name in [
        ("paragraph", "Whole passage"),
        ("posthoc_spans", "Post-generation spans"),
        ("preselected_spans", "Preselected spans"),
    ]:
        row = cm[key]
        complete = sum(
            bool(item.get("answered"))
            and bool(item.get("automatic_judgment"))
            and item["automatic_judgment"]["supported"] == 1
            and item["automatic_judgment"]["complete_answer"] == 1
            and item["automatic_judgment"]["fact_error"] == 0
            for item in citations["items"]
            if item["condition"] == key
        )
        require(
            abs(complete / 60 - row["complete_supported_answer_rate_all_planned"]) < 1e-10,
            "Citation primary denominator mismatch",
        )
        citation_sentences.append(
            f"{name}: {row['answered']}/60 published and {complete}/60 complete supported answers under the corrected automatic rubric."
        )
    lengths = {
        key: value["published_lengths"]["delivered_source_characters"]["mean"]
        for key, value in audit["strategies"].items()
    }
    local_marker_gaps = sum(
        row["published_checks"].get("linked_answer_text_claims_without_inline_ids", 0)
        for row in audit["strategies"].values()
    )
    structural = (
        f"Published source previews averaged {lengths['paragraph']:,.1f}, {lengths['posthoc_spans']:,.1f} and {lengths['preselected_spans']:,.1f} characters for whole passages, post-generation spans and preselected spans. "
        "These lengths describe each method's successful outputs; the methods published different subsets. Exact slicing and source identity passed for the published projections."
    )
    memory_sentences = []
    for row in memory["conditions"]:
        score = row["automatic_scores_equal_one"]["memory_used_appropriately"]
        memory_sentences.append(
            f"{row['condition'].replace('_', ' ')}: {row['published_answers']}/12 published answers; appropriate-use ratings {score}/{row['published_answers']} among those answers; state screens {row['state_screen_passed']}/{row['state_screen_total']}."
        )
    published_dimensions = []
    for condition in ["T0", "T1", "T2", "T3", "T4"]:
        dimensions = []
        for field, label in [
            ("supported", "supported"),
            ("specific_help", "concrete useful help"),
            ("within_scope", "within permitted scope"),
            ("fact_error", "factual error"),
        ]:
            row = hm[condition][field]
            dimensions.append(f"{label} {row['positive']}/{row['judged_denominator']}")
        published_dimensions.append(condition + ": " + ", ".join(dimensions))
    task_types = []
    for kind in ["comparison", "process", "calculation"]:
        strata = hints["strata"]["task_type"][kind]
        task_types.append(
            kind.capitalize()
            + ": "
            + ", ".join(
                f"{key} {strata[key]['valid_hints']}/{strata[key]['planned']}"
                for key in ["T0", "T1", "T2", "T3", "T4"]
            )
        )
    studies = [
        study(
            "formal_hints",
            "Formal teaching comparison",
            "formal",
            900,
            dict(hint_outcomes),
            [
                primary,
                "The added joint controls did not improve the prespecified primary outcome in this run. Strict rejection reduced answer availability. Successful-answer support scores alone would hide this tradeoff.",
                "By task type, valid hints among planned requests were as follows. "
                + ". ".join(task_types)
                + ". Each cell includes unavailable answers in its denominator; these secondary strata are descriptive.",
                "The separate judge rated published answers on four dimensions. "
                + "; ".join(published_dimensions)
                + ". Each fraction uses that condition's judged published answers, so it excludes failed generation. The factual-error numerator counts observed automatic flags, with independent scientific review pending.",
            ],
            [
                metric(
                    key,
                    f"{hm[key]['valid_hints_all_planned']}/180",
                    "Valid supported useful within-scope hints among all planned requests",
                )
                for key in ["T0", "T1", "T2", "T3", "T4"]
            ],
            [
                "The same DeepSeek family generated and judged outputs. Three turns share each task; the interval resamples 60 tasks with 10,000 fixed-seed repetitions. Independent human ratings remain 0."
            ],
            ["hints", "manifest"],
        ),
        study(
            "formal_citations",
            "Direct answers and attribution",
            "formal",
            180,
            dict(citation_outcomes),
            [" ".join(citation_sentences), structural],
            [
                metric(
                    "Published answers",
                    f"{published_citation}/180",
                    "All three strategies combined; compare each 60-item condition separately",
                )
            ],
            [
                "The first direct-answer judge incorrectly received hint restrictions. Version 2 rejudged the same saved outputs; generation results and failures stayed unchanged. Shorter previews alone establish no verification-speed benefit."
            ],
            ["citations", "attribution"],
        ),
        study(
            "memory_comparison",
            "Learning memory comparison",
            "memory",
            36,
            {
                "published_answer": sum(row["published_answers"] for row in memory["conditions"]),
                "generation_error": sum(row["no_published_answer"] for row in memory["conditions"]),
            },
            [
                " ".join(memory_sentences),
                "Correction retained an earlier preference in the structured condition; extraction and question-scope screens also failed in retained cases. Expiry, global-off, turn-profile-off and deletion fencing have separate state evidence.",
            ],
            [
                metric(
                    "Separate memory judgments",
                    "16 answers",
                    "20 generation errors remain ungraded in the 36-condition denominator",
                )
            ],
            [
                "Literal state screens differ from model-rated appropriate use. The small published subsets and shared-family judge support no ranking of learning benefit."
            ],
            ["memory", "memory_usage"],
        ),
        study(
            "original_regression",
            "Existing live reliability catalogue",
            "regression",
            110,
            {"expected_checks_passed": reg_pass, "expected_checks_failed": 110 - reg_pass},
            [
                f"All 110 original non-fault questions ran through actual HTTP and the durable worker. {reg_pass} met their recorded structural and expected-response checks; {110 - reg_pass} retained deviations. Terminal job counts: "
                + ", ".join(f"{key} {value}" for key, value in sorted(reg_states.items()))
                + "."
            ],
            [
                metric(
                    "Remaining fault catalogue",
                    "10 IDs /14 assertions",
                    "Current isolated tests cover provider errors, permissions, revocation, cancellation and timeout",
                )
            ],
            [
                "This reuses an existing development/regression catalogue. It measures software behavior and provenance; independent scientific correctness remains separate."
            ],
            ["regression", "faults"],
        ),
        study(
            "software_gate",
            "Final software verification",
            "regression",
            len(gate_checks),
            {"passed_stage": len(gate_checks)},
            [
                f"The final gate completed at {gate['executed_at']} with unchanged captured source. Its actual test artifacts record {py_pass} Python passes and {fe_pass} frontend passes; these counts are reported by suite, while the table denominator is gate stages."
            ],
            [
                metric("Python tests", py_pass, "Passed cases in the final pytest XML"),
                metric("Frontend tests", fe_pass, "Passed cases in the final frontend log"),
            ],
            [
                "Unit, integration and browser scenarios overlap in behavior. Their counts are never summed into a scientific accuracy denominator."
            ],
            ["gate"],
        ),
        study(
            "browser_controls",
            "Actual learner control journeys",
            "interface",
            3,
            {"source_journey_passed": 1, "memory_journey_passed": 1, "teaching_journey_passed": 1},
            [
                "Desktop 1440 and narrow 390 views exercised claim-specific highlights, explicit full-source disclosure, source keyboard focus, saved-memory Undo, a real 409 edit conflict with draft retention, deletion and task controls. Three new teaching requests produced hint 1, hint 2 and a full explanation on the same task."
            ],
            [
                metric(
                    "Delivered and rendered",
                    "3 and 3",
                    "Separate persisted events for the teaching journey; rendering establishes visible DOM",
                )
            ],
            [
                "Physical keyboards, native IME, assistive technology, reading and comprehension require separate observation."
            ],
            ["source_ui", "memory_ui", "teaching_ui", "teaching_events"],
        ),
    ]
    cost_rows = []
    for purpose, row in sorted(costs["by_purpose"].items()):
        cost_rows.append(
            {
                "purpose": purpose.replace("_", " "),
                "calls": row["attempts"],
                "input_tokens": row["input_tokens_known"],
                "output_tokens": row["output_tokens_known"],
                "missing_usage_calls": row["missing_usage_calls"],
                "amount": None
                if row["unknown_cost_calls"] == row["attempts"]
                else round(row["estimated_cny_known"], 6),
                "basis": (
                    "Monetary estimate unavailable; required usage or matching tariff data is missing. "
                    if row["unknown_cost_calls"] == row["attempts"]
                    else "Known-usage subtotal estimated in CNY. "
                    if row["unknown_cost_calls"]
                    else "Known-usage tariff estimate in CNY. "
                )
                + f"Monetary estimates are unavailable for {row['unknown_cost_calls']} of these calls. Tariff date {costs['tariff']['retrieved_date']}; cache-hit, cache-miss and output rates are applied separately.",
                "evidence_refs": ["costs"],
            }
        )
    data = {
        "schema": "week08_enhancement_report_data_v1",
        "as_of": "2026-09-20",
        "checkpoint": "week08_enhancement_20260920",
        "actual_executor": "Codex performed the shared implementation, scripted execution and document preparation. Named members remain the accountable module owners. Independent reviewers have supplied 0 ratings.",
        "summary": [
            "The Personalised AI Learning Assistant now integrates claim-specific source highlights, opt-in learning memory and explicit direct or hint teaching controls. The implementation joins saved answers, source permissions, memory versions and actual display events. Ordinary textbook questions still request a complete direct explanation, while the learner can deliberately enter or leave a hint sequence.",
            f"The research checkpoint retains 900 formal hint requests, 180 direct-answer citation requests and 36 memory conditions. {primary} The measured result gives the team a concrete reliability problem to investigate: increased rejection can outweigh the intended control benefit. Independent scientific and pedagogical ratings are the next evidence requirement.",
        ],
        "version_notes": [
            f"Formal execution used protocol {manifest['protocol']}, source manifest {manifest['source_manifest_sha256']} and the frozen runtime hashes listed in its public manifest. The active corpus remains {source['release_id']}, with {source['vectors']:,} vectors of dimension {source['min_dimension']}. The original four-book processing and earlier research artifacts remain preserved.",
            f"The external model was {model['model']} through {model['provider']}, configuration {model['configuration_id']}. This is a provider alias. The local tokenizer revision is {model['tokenizer_revision']}. Generation reserved {model['max_tokens']} output tokens and the checker reserved {manifest['checker_config']['max_tokens']}; each checked request shared a four-call, 180-second maximum. Separate judges used their recorded budgets.",
            "After the original live regression reached a terminal state, a separate HTTP task-resolution correction introduced learning_task_v2. It restricts implicit navigation to commands without a new named subject and removes an unserialisable regular-expression match from persisted state. Its isolated and portable verification is recorded separately. The frozen formal GenerationService outputs, prompts and comparison results remain unchanged.",
        ],
        "method_notes": [
            "Twelve development tasks informed the frozen implementation before the 60-task formal source set. Formal tasks span biology and chemistry, with comparison, process reasoning and calculation. Each task supplies the same three hint turns to T0 through T4. T0 uses prompt-only teaching; T1 checks the answer body; T2 additionally controls current source display and cumulative exposure. T3 and T4 remove those two components separately.",
            "Generation receives the actual question and frozen textbook evidence. Private reference answers and per-turn help allowances are evaluator inputs. The formal runner calls the same generation service and preserves delivered projections; independent HTTP journeys verify durable product state. Source panels are opened on every formal hint turn, making ordinary source exposure part of the tested policy.",
            "A separate direct-answer comparison keeps the question and initial source candidates fixed across full passages, post-generation spans and bounded preselected spans. Its corrected judge evaluates complete supported answers and citation coverage. The retained initial judge mixed in a hint allowance; its semantic scores are superseded by version 2 without replacing any generated result.",
        ],
        "checkpoint_evidence": [
            "gate",
            "hints",
            "citations",
            "memory",
            "portable",
            "regression",
            "costs",
        ],
        "studies": studies,
        "costs": {
            "currency": "CNY",
            "rows": cost_rows,
            "limitations": [
                f"The reconciled known-usage estimate is CNY {costs['totals']['estimated_cny_known']:.6f} across {costs['totals']['attempts']:,} recorded attempts. Usage is missing for {costs['totals']['missing_usage_calls']} of these attempts; monetary estimates are unavailable for {costs['totals']['unknown_cost_calls']}. These are dated tariff estimates; the provider invoice is a separate record.",
                *costs["limits"],
            ],
        },
        "failures": [
            {
                "label": "Rejected checked outputs",
                "observed": f"Only {published_hint}/900 formal hints and {published_citation}/180 direct citation requests published answers. Errors and nonanswers remain in every planned denominator.",
                "disposition": "The frozen outputs stay available for false-rejection and support review. A revised policy requires a new dated development and evaluation record.",
                "evidence_refs": ["hints", "citations"],
            },
            {
                "label": "Source association limits",
                "observed": f"The structural audit found {local_marker_gaps} published answer-text claims linked to source fragments without their own inline marker, and selected incomplete blocks in some whole-passage and post-generation outputs.",
                "disposition": "Exact identity and public projection checks remain valid; independent reviewers must examine local citation usability, atomic context and scientific support.",
                "evidence_refs": ["attribution"],
            },
            {
                "label": "Memory and request failures",
                "observed": "The memory comparison retained 20 generation errors, a superseded preference after correction and extraction/scope failures. The early five-request lifecycle smoke retained one memory-enabled context-limit error.",
                "disposition": "These cases remain visible beside successful UI control and deletion checks. No failed answer was counted as a completed learning interaction.",
                "evidence_refs": ["memory", "lifecycle"],
            },
            {
                "label": "Task boundary correction after the study",
                "observed": "An isolated reproduction found that a new named topic could inherit the old hint task, and a navigation predicate could place a regular-expression match into JSON state.",
                "disposition": "The separately verified learning_task_v2 correction narrows implicit continuation and preserves explicit task commands and historical frozen requests. The original live failures remain retained.",
                "evidence_refs": ["task_boundary", "regression"],
            },
            {
                "label": "Updated command verifier",
                "observed": "The first aggregate run retained a chat-scope verifier failure because its input whitelist still expected the earlier three fields. The authorized teaching controls extend that contract to six fields.",
                "disposition": "The verifier now checks the exact six fields and their defaults while retaining evaluator separation. The current second aggregate run records the complete rerun; the original failure remains available.",
                "evidence_refs": ["gate_prior", "gate"],
            },
        ],
        "human_review": {
            "completed_ratings": 0,
            "independent_reviewers": 0,
            "findings": [
                "Blinded forms are prepared for all formal outputs and 36 memory conditions. The timed highlight tool presents identical answer and evidence content as paragraph or marked fragments, with counterbalanced seeded ordering and actual interaction timing. Participant responses remain uncollected.",
                f"The final highlight material contains {d['highlight_load']['claims']} actual claim items and {d['highlight_load']['scheduledPresentations']} paired presentations. Browser loading verified {d['highlight_load']['sourceDisplays']} source displays and exact Unicode ranges, including {d['highlight_load']['unicodeAnswerClaims']} non-ASCII answer claims. Timed Start was unused; completed ratings and imported observations remain zero.",
            ],
            "instructions": [
                "Assign the two reviewers different identities and provide their separate randomized material and blank CSV. Keep the coordinator condition key and automatic ratings separate.",
                "Each reviewer records support, useful help, permitted scope or the relevant citation/memory dimensions with a concrete reason. Preserve failed and missing outputs in the planned schedule.",
                "Run the supplied review importer with the actual reviewer identity. It validates item IDs, rubric versions, complete score sets and timestamps; retain original submissions and report paired agreement and disagreements.",
                "Record any adjudication separately from the two original ratings. Compare automatic and human judgments only on actually paired rated items. The highlight tool downloads observed judgment and elapsed-time data; analyse order effects and correctness alongside time.",
            ],
            "evidence_refs": ["humans", "memory_humans", "highlight_load"],
        },
        "operations": [
            {
                "label": "Fresh CPU installation",
                "instruction": "Use the documented locked installation and source-import workflow, apply migrations, and configure the local model through the administrator page. Start the API, durable worker and frontend using the packaged startup instructions.",
                "verification_scope": f"A fresh Windows environment with Python {d['portable_app']['python']} and Torch {d['portable_app']['torch']} completed actual CPU retrieval and separate mock/live checks. {portable['deployed_runtime_files_exact']} deployed runtime files and {portable['verified_resources']} resources matched recorded hashes.",
                "evidence_refs": ["portable", "portable_app"],
            },
            {
                "label": "Learner controls",
                "instruction": "Open a claim citation to inspect its approved highlight. Request complete source explicitly. Enable memory before saving a durable preference, inspect its source, then edit or delete it. Another hint preserves the current task; full explanation and new problem are deliberate controls.",
                "verification_scope": "Actual saved API/browser flows include permitted projection, conflict handling, reload and event persistence.",
                "evidence_refs": ["source_ui", "memory_ui", "teaching_ui"],
            },
        ],
        "delivery": {
            "findings": [
                f"The portable proof verifies a fresh same-host CPU environment, an isolated new database, {source['vectors']:,} preserved vectors and {portable['verified_resources']} original resources. Its explicitly enumerated runtime subset is version-bound; subsequent research/report files are reconciled separately.",
                "The complete archive contains the application, verified runtime resources, research archive and nine English reports. Eight member packages contain disjoint changes against the preserved 16 September release. The accompanying PACKAGE_VERIFICATION.json records final archive hashes and membership checks.",
            ],
            "evidence_refs": ["portable", "portable_app", "migration"],
        },
        "limitations": [
            "The tasks are authored scientific cases, and the generator and automatic judge share a model family. The negative primary contrast and wide interval require scrutiny of false rejection, leakage and annotation consistency. Successful-only source lengths and model scores have a narrower scope than the planned-request outcomes.",
            "The fresh installation runs on the same Windows host. Physical-device accessibility, independent review time, transfer learning and delayed retention still need measured data. Formal outputs remain frozen so the team can compare those observations with the current automatic conclusions.",
        ],
        "week9_actions": [
            "Collect two independent reviews of the frozen outputs, prioritising all disputed and rejected cases plus a prespecified random sample; report completion, agreement and adjudication counts.",
            "Investigate the negative T2-versus-T1 result and memory correction failures on development cases, then register any changed policy before another formal run.",
            "Collect paired highlight timing and correctness using actual participants and recorded order, and extend the verified installation and keyboard/accessibility checks to another available physical device.",
        ],
        "evidence": evidence,
        "members": {},
    }
    data["members"] = member_records(
        primary,
        citation_sentences,
        structural,
        memory_sentences,
        reg_pass,
        py_pass,
        fe_pass,
        portable,
        costs,
    )
    return data


def member_records(
    primary,
    citation_sentences,
    structural,
    memory_sentences,
    reg_pass,
    py_pass,
    fe_pass,
    portable,
    costs,
):
    def member(findings, remaining, refs, studies):
        return {
            "findings": findings,
            "remaining": remaining,
            "evidence_refs": refs,
            "study_ids": studies,
        }

    return {
        "Xianshu_Zhang": member(
            [
                f"The final integration evidence joins the 900-request teaching comparison,180 direct citation requests, 36 memory conditions and actual learner controls. {primary} This result sets the next integration priority: maintain explicit source and task boundaries while investigating the availability cost of the joint checker. The report retains the unsuccessful requests so a clean interface cannot obscure a failed response.",
                f"The current software gate records {py_pass} Python and {fe_pass} frontend passes. The reused 110-question live catalogue has {reg_pass} expected-state passes, with every deviation retained. A separate fresh CPU installation verifies {portable['deployed_runtime_files_exact']} deployed runtime files and {portable['verified_resources']} source/model resources. The implementation therefore has concrete runtime evidence, while the final archive's own verification is produced only after report assembly.",
                "The delivery structure keeps the original accountable domains and shared execution attribution. Each contribution contains its assigned source changes and module report; shared corpus resources and curated research materials belong in the complete delivery. Reviewers can trace a reported number to a public evidence hash, then inspect the corresponding original failure or frozen input without assuming a personal commit history.",
                "A later HTTP task-boundary fix is recorded separately from the formal generation study. This chronology keeps the final product correction visible while preserving the experiment's original runtime and outcomes.",
            ],
            [
                "Week 9 integration decisions need actual independent ratings and a recorded response to the negative primary contrast. Keep the completed formal record fixed and treat any checker or memory update as a new version with explicit acceptance cases."
            ],
            ["hints", "gate", "portable", "task_boundary"],
            ["formal_hints", "software_gate", "original_regression"],
        ),
        "Hongle_Yang": member(
            [
                structural,
                "The attribution audit reads the exact source units used by the frozen 180-request comparison. Published projections passed the structural checks, while rejected outcomes preserve source and citation mismatches for inspection. The audit also found 64 source-linked answer-text claims lacking a marker local to that claim, and incomplete selected blocks in some paragraph and post-generation results. These observations separate correct byte identity from the completeness of a scientific explanation.",
                "The source investigation keeps five deterministic excerpts with book, chapter and physical PDF page identifiers, plus three concrete problem examples. The preserved corpus remains the reference for both full context and highlighted slices. In the user interface, a hint's ordinary source preview stays restricted until an explicit expansion event rechecks permission; this makes source preparation part of the teaching contract. Week 9 review can return directly to those positions to judge lost conditions, table structure or misleading local context.",
            ],
            [
                "Prioritise the incomplete-block examples and formula/table context for two independent reviewers. Record whether each span supports its linked claim and whether necessary conditions remain visible. Preserve the current processing identities while any later parser revision is evaluated separately."
            ],
            ["attribution", "citations", "source_ui"],
            ["formal_citations"],
        ),
        "Chengzhou_Liu": member(
            [
                " ".join(citation_sentences),
                structural,
                "The three strategies begin from matched real textbook candidates. Preselection uses bounded local evidence selection, so a shorter submitted context has a clear operational explanation. The measured publication rates and corrected direct-answer judgments show why context reduction and answer usefulness need separate denominators. Retrieval success alone cannot explain a downstream rejection; the retained stage and repair records identify where the final answer became unavailable.",
                "The fresh CPU installation exercises the actual local retrieval stack against the preserved 384-dimensional corpus. This supplies deployment evidence alongside the research comparison. Existing R0–R3 retrieval and fixed-versus-structure chunking studies remain prior records. The next retrieval experiment should examine the current rejected and incomplete cases before allocating a new held-out set, especially where a short span loses a condition or exposes the answer that a hint should leave to the learner.",
            ],
            [
                "Week 9 work will compare independent support and completeness judgments on the frozen strategy outputs, including unavailable answers. A subsequent selection rule needs a new source-bound development record and the same explicit accounting of source length, model calls and failures."
            ],
            ["citations", "attribution", "portable"],
            ["formal_citations"],
        ),
        "Sijin_Lu": member(
            [
                primary,
                "The controlled study makes checker rejection a measurable product outcome. T2 adds current evidence-display and cumulative-exposure checking, yet its all-planned valid-hint result is lower than T1. The successful responses receive strong same-family support ratings, while many requests exhaust the bounded generate/check/repair/recheck flow. These findings make false rejection, task-help interpretation and the checker reference the next review priorities.",
                "The direct-answer comparison received a corrected offline rubric after the first judge was found to apply hint restrictions. The generated answers, online checks and failures stay unchanged. This preserves the distinction between a product policy change and a measurement correction. The actual browser sequence separately confirms that first hint, next hint and explicit complete explanation persist with the correct task and help level; those state results complement the semantic evaluation.",
            ],
            [
                "Use two independent reviewers to inspect all major false-rejection and over-help disagreements, including cumulative ordinary source exposure. Freeze any revised prompt or checker as a later policy version, and report its availability, support and cost together with the existing baseline."
            ],
            ["hints", "citations", "teaching_ui"],
            ["formal_hints", "formal_citations"],
        ),
        "Pengyuan_Xia": member(
            [
                " ".join(memory_sentences),
                "The 36 authored conditions expose different memory failures: structured extraction and question-scope screens miss expected context, and correction can retain an earlier preference. The study uses the same two real textbook questions and frozen initial evidence across conditions, so retrieval variation is removed from this small comparison. Sixteen published answers receive separate model judgments; 20 generation errors remain ungraded. Appropriate-use scores differ from literal state checks and give no robust ranking of educational benefit.",
                "The actual learner workflow supports opt-in settings, versioned correction, visible source context, deletion and Undo of a save. Browser testing created a real stale revision, received 409 and preserved the learner's draft before a refreshed save. Expiry, global-off, profile-off and stale-job deletion fencing have their own state evidence. Three live teaching requests also preserve a single problem through two hints and an explicit full explanation, establishing the operational route for later pedagogy review.",
            ],
            [
                "Week 9 review should judge when a preference genuinely improves the answer and when stale context causes a material mismatch. Collect two independent memory ratings and analyse the correction failures before changing extraction rules. Transfer and delayed-learning outcomes require actual participants."
            ],
            ["memory", "memory_ui", "teaching_ui"],
            ["memory_comparison", "browser_controls"],
        ),
        "Zeping_Liao": member(
            [
                "The additive migration preserved the measured aggregates of 33 pre-existing tables. New task, memory, projection and exposure records extend that state without replacing old answers or source versions. The real teaching journey joins three request IDs to three published presentations, three delivery events and three browser-render acknowledgements. Distinct identities let an audit identify what was generated privately, released to the learner and actually displayed.",
                "The first five-request live lifecycle check retained four successful generations and one memory-enabled context-limit failure. Its permission, redaction, memory snapshot and erasure assertions remain useful, while the failed request remains a failure. Actual browser memory edits exercised compare-and-swap behavior through a 409 conflict, draft retention and a later successful correction; deletion finished with both verification entries removed and memory disabled.",
                f"The final software evidence records {py_pass} Python passes, including lifecycle coverage, and the isolated fault mapping covers 10 catalogue IDs with 14 assertions. Fresh CPU installation verifies {portable['deployed_runtime_files_exact']} exact deployed runtime files in a separate database. These records support the specific transaction and execution paths exercised, with independent scientific and large-concurrency review remaining distinct work.",
                "After the original live regression ended, learning_task_v2 corrected a reproduced task-boundary issue: new named subjects now avoid implicit hint continuation, and navigation predicates remain serialisable. Its dedicated verification is separate from the earlier fixed formal generation study. Explicit full-explanation commands and historical frozen requests retain their intended behavior.",
            ],
            [
                "Prioritise simultaneous new-topic and full-explanation transitions, memory edits and delayed worker completion in Week 9 concurrency review. Keep request, task and exposure versions visible in each reproduction, and preserve unsuccessful attempts when recovery behavior changes."
            ],
            ["migration", "lifecycle", "teaching_events", "gate", "task_boundary"],
            ["software_gate", "original_regression", "browser_controls"],
        ),
        "Baiqing_Huang": member(
            [
                "Actual desktop 1440 and narrow 390 journeys exercised the new source and memory controls with the same retained interface style. Opening a claim showed 304 approved source codepoints and one associated highlight; the deliberate full-source action exposed 1,480 codepoints and its original link. Reload returned the approved restricted preview. Keyboard Escape restored focus, and the full-source render referenced the corresponding expansion receipt.",
                "The memory journey used real extracted entries, source inspection, saved-notice Undo, editing and deletion. A concurrent server edit produced 409 and left the typed draft intact; refreshing the version allowed a subsequent save. The final state has the verification entries deleted and memory off. These transitions rely on actual successful responses and retain earlier verifier failures separately.",
                "Three new browser requests progressed from hint level 1 to level 2 and then an explicit direct explanation on the same task. All three generated presentations have separate delivered and rendered events. Starting a new problem reset the next composer action to direct. The timed paragraph/highlight comparison is also ready with counterbalanced seeded order and downloadable judgments. Actual reviewers can now measure verification time and correctness on the paired displays.",
            ],
            [
                "Week 9 collection should pair verification correctness with actual completion time and keep order effects visible. Extend keyboard and disclosure checks to physical mobile devices, native IME and assistive technology. Rendering receipts describe displayed DOM; reading and comprehension remain separate observations."
            ],
            ["source_ui", "memory_ui", "teaching_ui", "highlight_load"],
            ["browser_controls"],
        ),
        "Chong_Zhang": member(
            [
                primary,
                "All 900 formal hint requests and 180 citation requests remain in their original schedules. The analysis resamples whole tasks to preserve the correlation between three hint turns. The corrected citation judge addresses the direct-answer measurement error on unchanged generated outputs. The 36-condition memory study separately records automatic state screens, 16 model judgments and 20 answer errors, preventing a successful-output subset from becoming an overall method score.",
                f"The current 110-question HTTP regression has {reg_pass} expected-state passes and {110 - reg_pass} deviations. Ten additional fault IDs map to 14 isolated assertions. The final gate separately records {py_pass} Python and {fe_pass} frontend passes. These are different scopes, and their overlapping checks are reported without treating the sum as independent scientific cases.",
                "Two-reviewer forms and the timed highlight tool are prepared from the actual frozen outputs. Item identity, rubric, reviewer identity and completion fields are checked on import; original independent scores remain distinct from adjudication. The purpose-level usage ledger includes retained failed attempts and separates online generation/checking from offline assessment. The remaining research task is to collect independent judgments and compare their disagreements with the automatic conclusions.",
            ],
            [
                "Week 9 reporting should publish actual review completion and missingness, task-paired human results, agreement and separately attributed adjudication. Register any second-model or learning-effect extension before its first outcome, with the original formal records retained as a fixed comparison."
            ],
            ["hints", "citations", "memory", "humans"],
            ["formal_hints", "formal_citations", "memory_comparison", "original_regression"],
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE / "report-data.json")
    parser.add_argument("--check-ready", action="store_true")
    args = parser.parse_args()
    inputs, pending = ready_inputs()
    if pending:
        print(
            json.dumps(
                {"status": "awaiting_terminal_evidence", "missing_or_pending": pending}, indent=2
            )
        )
        return 2
    data = prepare(inputs)
    date.fromisoformat(data["as_of"])
    owners = load(HERE / "ownership.json")
    evidence = validate(data, owners, ROOT)
    reports = build_content(data, owners, evidence)
    counts = {report["filename"]: len(markdown(report).split()) for report in reports}
    output = args.output.resolve()
    require(
        output.is_relative_to((ROOT / "evidence").resolve()),
        "Report input belongs under public evidence",
    )
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if not args.check_ready:
        if output.exists():
            require(
                output.read_bytes() == payload,
                "Existing report data differs; preserve it and choose a new --output",
            )
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(payload)
    print(
        json.dumps(
            {
                "status": "validated",
                "documents_created": 0,
                "data_written": not args.check_ready,
                "output": str(output),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "word_counts": counts,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
