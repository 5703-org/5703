"""Assemble the closed local Phase90 result and reviewable append-only publication."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

W = Path(__file__).resolve().parent
R = W / "5703-repair90-runtime"
P = W / "5703-repair90-preparation"
Q = W / "5703-repair90-quality"
D = W / "5703-repair90-diagnosis"
M = Path(r"E:\5703\learning-assistant")
sys.dont_write_bytecode = True
sys.path.insert(0, str(R))
import budget88

def read(path):
    return json.loads(Path(path).read_bytes())

def pin(path):
    raw = Path(path).read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

def create(path, value):
    raw = ((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
           if not isinstance(value, str) else value.encode())
    with Path(path).open("xb") as stream:
        stream.write(raw)
    return pin(path)

protocol = read(R / "protocol88.json")
for source in protocol["source_pins"]:
    assert pin(Path(source["path"])) == source
finance = budget88.snapshot(R / "cohort-ledger")
assert finance["claimed_physical_posts"] == finance["settled_posts"] == 9
assert finance["known_cost_USD"] == "0.108428272"
assert finance["unknown_full_hold_USD"] == "0" and finance["terminal_exposures"] == 0
assert not finance["cohort_stopped"]
comparison_path = Q / "component-model-comparison90.json"
assert comparison_path.is_file()
comparison = read(comparison_path)
reviews = [read(Q / (case + "-review90.json")) for case in ("case01", "case08", "case06")]
assert all(row["independent_answer_QA"] == "FAIL" for row in reviews)
cases = []
for case, review in zip(("case01", "case08", "case06"), reviews):
    journey = read(R / case / "journey-receipt88.json")
    closure = read(R / case / "api-closure77.json")
    final = read(R / case / "native-provider70/final-receipt.json")
    assert closure["owned_threads_closed"] and all(closure["old_metadata_unchanged"].values())
    assert final["closure_status"] == "CLOSED_NUMERIC_NO_UNKNOWN"
    cases.append({"case_id": case, "question_sha256": journey["question_sha256"],
        "API_status": journey["status"], "independent_full_answer_QA": "FAIL",
        "API_send_to_terminal_ms": journey["api_send_to_terminal_ms"],
        "valid_DOM_latency_sample": False, "actual_posts": final["actual_posts"],
        "known_cost_USD": final["native_settled_known_cost_USD"],
        "QA_receipt": pin(Q / (case + "-review90.json"))})
components = []
for instance, base in (("component01qwen", "case01"), ("component08qwen", "case08")):
    descriptor = read(R / (instance + "-descriptor90.json"))
    final = read(R / instance / "final-receipt.json")
    financial = read(R / instance / "financial.json")
    outcome = read(R / instance / "normal-outcome.json")
    result = read(R / instance / "diagnostic-result.json")
    primary = read(R / base / "native-provider70/slot-02-normal-outcome.json")
    assert final["physical_posts"] == 1 and final["stop_code"] is None
    assert not final["publication_exercised"]
    components.append({"instance_id": instance, "base_case_id": base,
        "descriptor": pin(R / (instance + "-descriptor90.json")),
        "same_input_context_sha256": descriptor["context_sha256"],
        "original_wire_sha256": descriptor["original_wire_sha256"],
        "contrast_wire_sha256": descriptor["contrast_wire_sha256"],
        "wire_delta_keys": ["model", "provider", "reasoning"],
        "normal_status": result["status"], "normal_schema_valid": result["schema_valid"],
        "primary_normal_diagnostic_latency_ms": primary["diagnostic"]["latency_ms"],
        "Qwen_normal_diagnostic_latency_ms": outcome["diagnostic"]["latency_ms"],
        "primary_checker_cost_USD": str(primary["usage"]["cost"]),
        "Qwen_checker_cost_USD": financial["numeric_gateway_cost_USD"],
        "publication_exercised": False, "quality_PASS_claimed": False,
        "independent_comparison_receipt": pin(comparison_path)})
result = {"schema": "repair90_closed_root_results_v1", "finished_UTC": datetime.now(timezone.utc).isoformat(),
    "authorization": budget88.AUTHORIZATION, "protocol": pin(R / "protocol88.json"),
    "source_version_sha256": protocol["source_version_sha256"], "source_pins": protocol["source_pins"],
    "production_code_changes_this_phase": 0, "baseline_denominator": 3,
    "independent_full_answer_QA_passes": 0, "technical_API_published_answers": 1,
    "qualified_new_DOM_samples": 0, "new_cases_or_sampling": False,
    "initial_BASE_financial": {"POST": 7, "USD": "0.0996846"},
    "checker_only_diagnostic_denominator": 2, "cohort_financial": finance,
    "cases": cases, "components": components,
    "old_DEV89": {"full_answer_QA": "2/8", "POST": 28, "USD": "0.4056684", "records_mutated": False},
    "same_input_attribution_limits": "Two n=1 sequential pairs; route, reasoning profile, prices and cache differ. No pure-model causal, quality-superiority or speedup claim.",
    "source_availability": "Full submitted evidence for all requested qualitative facts; no demonstrated RAG miss or missing numerical input in these three questions.",
    "observed_failures": ["Gemini01 output truncation", "Gemini06 required parent reason fields missing",
        "uncited or incompletely selected teacher units", "Qwen01 required parent reasons and actual citation scopes violated",
        "Gemini08 and Qwen08 both certify the same incomplete C005 species-role proof"],
    "additional_production_fix_or_default_model_switch": "Not justified by current diagnostic evidence; no repeated prompt tuning",
    "retained_B_software_evidence": pin(W / "software-verification89.json"),
    "full_4532_suite_rerun_this_phase": False,
    "local_controller_next_step": "Before a future Main/controller version change, separate historical closed-record verification from prospective live source/controller pin admission. Preserve old descriptors, claims, code and settlements; no retagging.",
    "completion_status": "Current requested retest/diagnosis closed; complete learning-assistant and quality-qualified latency acceptance remain open.",
    "no_auth_sealed_rubric_or_real_database_payload_published": True,
    "remote_push_upload_deployment_or_course_submission": False}
root_result_pin = create(W / "phase90-unified-results-root.json", result)

report = """The current B evidence-index repair did not achieve an independently qualified full answer on this three-question retest. The normal API published one answer, but full assertion and selected-unit evidence review passed **0/3**. Both same-input Qwen diagnostics also failed to establish a usable replacement checker. The default model and production source remain unchanged.

This independent batch used **9 physical requests, $0.108428272**, against the authorized shared 24-request/$1 limit. All nine requests have numeric settlements, UNKNOWN exposure is zero, and no shared stop is active. There is no page/nonpage quota reservation. The unused allowance is not a blocker; testing stopped after the requested diagnostic comparison rather than repeating prompt changes without evidence.

| Current B normal API case | Requests / cost | API send to terminal | Published | Independent full-answer QA |
|---|---:|---:|---|---|
| Allosteric inhibition/activation (01) | 2 / $0.0307024 | 27.2143 s | No | Fail |
| H2/I2/HI equilibrium (08) | 2 / $0.0208563 | 19.0102 s | Yes | Fail |
| Red-cell osmosis (06), previous positive control | 3 / $0.0481259 | 37.6024 s | No | Fail |

All three drafts contained scientifically correct qualitative content covering the requested facets, and the complete submitted source packets contained sufficient evidence. This is not a demonstrated retrieval miss or a missing numerical-input problem. Qualification nevertheless requires each factual unit's actual citation scope and its own selected fragments to prove its assertion. Other claims, sibling units or unselected textbook fragments do not automatically supply that proof. Necessary scientific inference from the actual selected evidence and question givens remains valid: for example, lower reverse flux after removing HI implies temporary net forward reaction at the initial equilibrium. The reviewer accepted this bounded inference rather than requiring a particular keyword.

Case01's Gemini checker reached its output limit: 8188 output tokens, including 7865 reasoning tokens, with no valid complete judgment. The teacher also included an uncited scientific opener and incomplete own-parent evidence. Case06's first checker omitted the required parent `r` field in all seven textbook claims. Original-code offline replay identified the first missing field and reproduced strict rejection. Its bounded format repair produced a valid negative judgment; genuine uncited statements remained, and one remaining provider call could not perform both semantic repair and recheck. These are model contract/content failures and expected finite-call behavior; the replay did not demonstrate an application validator exception.

Case08 published scientifically correct prose, but C005/U01 and U02 selected only ev001/F002, a generic rule about removing a product. They did not select the needed identity that HI is this reaction's product. F004 was available in the parent's evidence domain but not selected for C005; F014 was in another source/parent binding. The checker nevertheless certified the two units. The other thirteen units had adequate selected support. This is a false certification of incomplete proof, not missing source availability.

The alternate was the currently configured Qwen3.8 Flash record, independently read from the original synthetic database. Its stored 2048-token/json_schema configuration was aligned to the existing 8192-token/json_object comparison contract. The actual full messages, source packet, question, canonical schema and immutable context were preserved. Descriptors bind the original compiled wire digest, all six closed public artifacts, current B16 and the prospective controller. Wire differences are model, provider routing and reasoning: Gemini/Vertex HIGH versus Qwen/Alibaba with reasoning disabled. Prices and cache conditions also differ. There was no teacher replay, database publication, automatic request retry or page run.

| Same-input checker pair | Gemini call / cost | Qwen call / cost | Qwen result |
|---|---:|---:|---|
| Case01 slot02, 69 fragments / 9 claims / 21 units | 19.467 s / $0.028816 | 23.894 s / $0.00498033 | Complete JSON, strict transport rejected |
| Case08 slot02, 50 fragments / 8 claims / 15 units | 10.627 s / $0.0189825 | 30.316 s / $0.003763342 | Structurally valid, same C005 proof gap falsely certified |

Qwen01 omitted parent reasons for eight textbook claims and proposed citations outside actual parent bindings, including adding a citation to an originally uncited claim. Its raw `body_ok` cannot confer typed or scientific acceptance. Qwen08 passed structural and packet assessors but still selected only F002 for both C005 units. Neither comparison justifies switching the default checker. The costs were lower; these two sequential n=1 calls provide no stable speed or quality improvement evidence, and the second Qwen request used 6912 cached input tokens.

The offline codec replay establishes the decoder failure, not wire equivalence. One exploratory replay boolean lacked a persisted comparison expression and operand paths; its wire-mismatch interpretation was withdrawn without rewriting the original receipt. The clarification records the expected difference between precompile and compiled SYSTEM instructions. Actual same-input proof uses pinned compiled wires, both explicit descriptors and the independent comparison review.

The three literal questions, rubric and public-source release are unchanged from exposed DEV89 development cases; the fresh teacher drafts differ, so the old-versus-new normal API comparison is not a same-answer causal test. The original DEV89 2/8 quality denominator, 28 requests/$0.4056684 and earlier records remain separate and unchanged. The exact saved-input checker pairs are the controlled input comparison here. They are still exposed AI-reviewed diagnostics, not HumanGold, blinded sampling or a learner-effect study.

Current production B16 is `369bba3c1ba0e0007b346142988ccc3a242e13505e22513a1a13166a2fe4b2fc`; its codec SHA is `8c830694093b41e9f6250939de2cf9f72b24726bddbc1cba0141a6b8cb9efa56`. No production code was changed in this phase. The retained prior-phase B software receipt contains the 4532-test/215-subtest result; that full suite was not rerun. New verification comprises the eight initial runtime guard groups, eleven complete-public-input prospective controls, ten additional pure financial controls, independent peer review, current B16 readback, original-code codec replay and actual closed request receipts. The 18 original batch financial records were preserved across the prospective component-controller extension.

These clocks are API send-to-terminal or complete normal-adapter call clocks. There is **no new qualified full-DOM latency sample**, TTFT or p95. A 19.01-second published API answer with failed unit evidence QA cannot establish a quality-qualified latency target. The earlier historical 20.437-second qualified DOM sample remains a separate n=1 result. Stable full-answer speed, the full learning journey, learner outcomes and canonical course completion remain open.

The next production step needs evidence that a checker both preserves the mandatory output contract and catches these incomplete selected-unit proofs while retaining valid necessary inferences. This batch does not justify another prompt change or automatic citation/field filling. Before a future Main/controller version change, the local experiment controller also needs a prospective change separating historical closed-record verification from live pin admission; the current historical scan rechecks live B/controller pins. This is a local controller limitation to repair while preserving old records, not an authorization or budget blocker.

All owned API threads closed and all five old fixture metadata groups remained unchanged. Credentials stayed in memory. Only public synthetic questions, answers and textbook content were sent. This local delivery excludes credential/binder payloads and the sealed rubric; it preserves all databases, experiment inputs/results, old deliveries and the protected Week09 staging directories. No other project, remote push/upload, deployment or course submission was performed.

Reviewable evidence: [root results](20261012-repair90-evidence/root-results90.json), [three case reviews and model comparison](20261012-repair90-evidence/quality/component-model-comparison90.json), [original-code diagnosis](20261012-repair90-evidence/diagnosis/diagnosis90.json), and [independent runtime review](20261012-repair90-evidence/preparation/peer-review90.json). The readback manifest records every delivered file digest and the preserved append-only ledger prefixes.
"""
report_pin = create(W / "phase90-final-report.md", report)
progress_pin = create(W / "phase90-progress-append.md", "\n\nRepair90 checkpoint (2026-10-12 UTC): current B16 actual retest closed, independent full-answer QA 0/3, technical API publication 1/3; two saved-input Qwen checker diagnostics did not establish a usable replacement. New shared batch: 9 physical POSTs / $0.108428272, 9 numeric settlements, UNKNOWN 0; no page quota reservation and no new DOM-qualified sample. No production source/default-model change or 4532-suite rerun. DEV89 denominator and records preserved. See `20261012-repair90-checker-retest.md` and its readback evidence. Remaining acceptance is checker contract/selected-unit proof reliability and quality-qualified full-answer latency; future experiment controller version changes need historical/live-pin separation, not new user fee permission. No other project, real database, protected staging data or remote delivery changed.\n")
handover_pin = create(W / "phase90-handover-append.md", "\n\nRepair90 source-to-target handover (2026-10-12 UTC): the existing production B16 index repair was actually retested on three exposed DEV89 questions in a new independent 24-POST/$1 cohort. Outcomes: QA 0/3, technical publication 1/3; exact-input Qwen/Alibaba disabled-reasoning contrasts versus Gemini/Vertex HIGH preserved context/schema/evidence and did not justify default adoption. Actual total 9 POSTs/$0.108428272, settled9/UNKNOWN0. No further production code edit or prompt loop; prior B 4532-test evidence retained without rerun. Local candidate controllers were prospectively frozen and old 18 ledger records preserved; before future Main/controller changes, revise historical scan live-pin coupling without retagging historical evidence. Append-only report/evidence delivery is `docs/execution/20261012-repair90-checker-retest.md` and `20261012-repair90-evidence`. Previous DEV89 2/8 and 28/$0.4056684 remain separate. Full learning-assistant/course and qualified latency acceptance remain open.\n")

selected = []
def select(path, destination):
    path = Path(path)
    assert path.is_file() and path.is_relative_to(W) and not path.is_symlink()
    assert not any(row["destination"] == destination for row in selected)
    selected.append({**pin(path), "destination": destination})

select(W / "phase90-unified-results-root.json", "root-results90.json")
select(W / "software-verification89.json", "retained-software-verification89.json")
for name in ("run_case90_root.py", "run_client90_root.py", "run_component90_root.py", "freeze_components90_root.py", "finalize90_root.py", "publish90_root.py"):
    select(W / name, "root-tools/" + name)
for path in sorted(R.iterdir()):
    if path.is_file() and path.suffix in {".json", ".py"}:
        select(path, "runtime/" + path.name)
for case in ("case01", "case08", "case06"):
    for path in sorted((R / case).glob("*.json")):
        select(path, "runtime/" + case + "/" + path.name)
    for path in sorted((R / case / "native-provider70").glob("*.json")):
        select(path, "runtime/" + case + "/native-provider70/" + path.name)
for name in ("cohort-ledger", "component01qwen", "component08qwen"):
    for path in sorted((R / name).glob("*.json")):
        select(path, "runtime/" + name + "/" + path.name)
for directory, target in ((Q, "quality"), (D, "diagnosis")):
    for path in sorted(directory.glob("*.json")):
        select(path, target + "/" + path.name)
for path in sorted(P.glob("*.json")):
    select(path, "preparation/" + path.name)
for folder in ("runtime-candidate", "component-candidate", "budget-forward-candidate"):
    for path in sorted((P / folder).iterdir()):
        if path.is_file() and path.suffix in {".json", ".py", ".diff", ".txt"}:
            select(path, "preparation/" + folder + "/" + path.name)
assert sum(row["bytes"] for row in selected) < 8 * 1024 * 1024
assert not any("private-rubric" in row["path"] or "BINDER" in row["path"] for row in selected)
selection_pin = create(W / "phase90-evidence-selection.json", selected)
old_report = M / "docs/execution/20261012-dev89-quality-latency.md"
assert pin(old_report)["sha256"] == "2ad8d9e9e96abae9d7e0daf63b579a352a84ac36f42988e2c3a56c0c2d72f53b"
ready = {"schema": "repair90_reviewable_publication_v1", "status": "READY_FOR_READ_ONLY_REVIEW",
    "publication_authorized_in_session": True, "report": report_pin, "results": root_result_pin,
    "selection": selection_pin, "selected_payload_count": len(selected),
    "selected_payload_bytes": sum(row["bytes"] for row in selected),
    "current_source_pins": protocol["source_pins"], "old_report_preserved_pin": pin(old_report),
    "append_preimages": [pin(M / "docs/execution/progress.md"), pin(M / "docs/foundation/handover_migration.md")],
    "progress_append": progress_pin, "handover_append": handover_pin,
    "Main_target_report": str(M / "docs/execution/20261012-repair90-checker-retest.md"),
    "Main_target_evidence": str(M / "docs/execution/20261012-repair90-evidence"),
    "private_payload_copied": False, "credentials_in_memory_only": True,
    "new_qualified_DOM_n": 0, "old_dev89_denominator_unchanged": True,
    "local_writer": pin(W / "publish90_root.py")}
create(W / "phase90-publication-ready.json", ready)
assert budget88.snapshot(R / "cohort-ledger") == finance
print(json.dumps({"status": ready["status"], "payload_files": len(selected),
    "payload_bytes": ready["selected_payload_bytes"], "report_sha256": report_pin["sha256"],
    "batch_POST": 9, "known_USD": finance["known_cost_USD"], "UNKNOWN_USD": "0",
    "Main_writes": 0, "model_calls": 0}), flush=True)
