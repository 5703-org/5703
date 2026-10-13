"""Build one truthful DEV89 report and publication selection from closed evidence."""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import xml.etree.ElementTree as ET

W = Path(__file__).resolve().parent
M = Path(r"E:\5703\learning-assistant")
R = W / "5703-dev89-runtime"
P = W / "5703-dev89-preparation"
Q = W / "5703-dev89-quality"
N = W / "5703-dev89-new-quality"
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def read(path):
    return json.loads(Path(path).read_bytes())
def pin(path):
    path = Path(path)
    assert path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}
def create(name, value):
    path = W / name
    with path.open("xb") as out:
        out.write((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode())
    return path

raw_results = read(R / "results89.json")
totals = raw_results["cohort_financial"]
assert totals["claimed_physical_posts"] == totals["settled_posts"] == 28
assert Decimal(totals["known_cost_USD"]) == Decimal("0.4056684")
assert Decimal(totals["unknown_full_hold_USD"]) == 0 and totals["terminal_exposures"] == 0
assert not totals["cohort_stopped"] and totals["nonpage_posts_cap"] == 24
adoption = read(P / "common-repair-adoption89-root.json")
for record in adoption["source_pins_after"]:
    current = pin(record["path"])
    assert current == record
assert adoption["source_version_after_sha256"] == "369bba3c1ba0e0007b346142988ccc3a242e13505e22513a1a13166a2fe4b2fc"
new_qa = read(N / "four-base-review89.json")
assert new_qa["assigned_scientific_pass_n"] == 2 and new_qa["frozen_baseline_denominator"] == 8
new_rows = {row["case_id"]: row for row in new_qa["cases"]}
assert {key for key, value in new_rows.items() if value["status"].startswith("PASS_")} == {"case06", "case09"}
for case in ("case01", "case03", "case04", "case05"):
    assert read(Q / f"{case}-review89.json")["independent_answer_QA"] == "FAIL"
page_qa = read(N / "page-review89.json")
assert page_qa["new_page_attempt_denominator"] == 2 and page_qa["new_quality_qualified_complete_DOM_n"] == 0

full = W / "5703-unit89-full-sys"
focused = W / "5703-unit89-contracts"
failed = W / "5703-unit89-free-v1"
full_receipt, focused_receipt, crash_receipt = read(full / "receipt.json"), read(focused / "receipt.json"), read(failed / "receipt.json")
assert full_receipt["exit_code"] == focused_receipt["exit_code"] == 0
assert full_receipt["current_B_six_pins_unchanged"] and focused_receipt["current_B_six_pins_unchanged"]
assert not full_receipt["timed_out"] and not focused_receipt["timed_out"]
full_log = (full / "pytest.log").read_text(encoding="utf-8")
assert "4532 passed, 21 skipped, 40 warnings, 215 subtests passed" in full_log
assert "198 passed" in (focused / "pytest.log").read_text(encoding="utf-8")
assert crash_receipt["exit_code"] == 3221225477 and not crash_receipt["timed_out"]
suite = ET.parse(full / "pytest.xml").getroot().find("testsuite")
assert suite is not None and suite.attrib["failures"] == suite.attrib["errors"] == "0"
software = {"schema": "dev89_current_B_software_verification_v1", "status": "PASS_LOCAL_UNIT_AND_RUFF",
    "source_version_sha256": adoption["source_version_after_sha256"], "source_pins": adoption["source_pins_after"],
    "free_selection_index_control_groups": 14, "free_selection_control_receipt": pin(P / "selection-index-candidate/control-selection-index89-frozen.json"),
    "focused_test_files": 10, "focused_passed": 198, "focused_receipt": pin(focused / "receipt.json"),
    "full_unit_files": 234, "ordinary_tests_passed": 4532, "subtests_passed": 215, "skipped": 21, "warnings": 40,
    "pytest_seconds": "166.94", "parent_seconds": full_receipt["elapsed_seconds"], "junit_attributes": suite.attrib,
    "full_receipt": pin(full / "receipt.json"), "full_XML": pin(full / "pytest.xml"), "full_log": pin(full / "pytest.log"),
    "full_guard": pin(full / "tripwire.json"), "guard_summary": read(full / "tripwire.json"),
    "first_full_attempt": {"status": "NATIVE_WINDOWS_ACCESS_VIOLATION_NOT_TIMEOUT", "exit_code": 3221225477,
        "elapsed_seconds": crash_receipt["seconds"], "receipt": pin(failed / "receipt.json"), "log": pin(failed / "pytest.log"),
        "stack": pin(failed / "faulthandler.log"), "XML_present": False, "normal_final_guard_receipt_present": False,
        "cause_confirmed": False, "first_receipt_six_pin_attestation": False},
    "finite_retry": "Unchanged isolation guard; --capture=sys changes global pytest observation. Explicit capfd still uses file descriptors. Root before/after six pins include B codec; final sixteen-file readback matches B.",
    "ruff": {"exit_code": 0, "output": "All checks passed!", "command": "Main/.venv/Scripts/python.exe -B -X utf8 -m ruff check Main/generation/lossless_unit_findings_v1.py --no-cache"},
    "actual_B_model_POSTs": 0, "live_B_quality_latency_verified": False, "full_eight_stage_verification": False,
    "real_PostgreSQL_tested_by_free_unit_suite": False, "course_completion_claimed": False}
software_path = create("software-verification89.json", software)

specs = [
    ("case01", "allostery", "FULL", 3, 3, 0, 0, "FAIL: uncited facts, own-source gaps; both decodes invalid", "Not established", False),
    ("case03", "translation", "FULL", 5, 5, 0, 0, "FAIL: first claim lacks own selected stop-name provenance", "No", True),
    ("case04", "gas calculation", "FULL", 4, 4, 0, 0, "FAIL: uncited/underselected claims; transparent calculation misjudged", "Calculation rejected; other genuine proof defects coexist", False),
    ("case05", "bomb calorimetry", "PARTIAL: apparatus paragraph absent", 4, 3, 1, 0, "FAIL: contradictory solution-only balance, proof gaps", "Missing experiment C is legitimate", False),
    ("case06", "RBC osmosis", "FULL", 4, 4, 0, 0, "PASS; qualitative swelling inference/highlight wording limitation recorded", "No", True),
    ("case07", "standard Cu/Ag cell", "FULL", 4, 2, 1, 1, "FAIL: E3 missing, E4 partial despite sufficient actual sources", "Yes: wire direction/carrier withholding", True),
    ("case08", "H2/I2/HI equilibrium", "FULL", 4, 4, 0, 0, "FAIL: both checker outputs invalid; scientifically correct draft", "No semantic refusal established", False),
    ("case09", "bacterial DNA", "FULL", 4, 4, 0, 0, "PASS; overall assembly direction/context clarity limitation recorded", "No", True),
]
matrix = []
for case, topic, suff, facets, complete, partial, missing, quality, wrong, published in specs:
    directory = R / case
    journey = read(directory / "journey-receipt88.json")
    finance = read(directory / "native-provider70/final-receipt.json")
    assert (journey["status"] == "API_COMPLETED") == published
    first_checker = read(directory / "native-provider70/slot-02-normal-outcome.json")
    matrix.append({"case_id": case, "version": "A", "topic": topic, "actual_source_sufficiency": suff,
        "fragment_rows_sent_per_case": first_checker["diagnostic"]["checker_transport"]["fragment_count"],
        "required_facets": facets, "draft_complete": complete, "draft_partial": partial, "draft_missing": missing,
        "published_complete": complete if published else 0, "published_partial": partial if published else 0,
        "publication": published, "independent_QA": "PASS" if case in ("case06", "case09") else "FAIL",
        "finding": quality, "wrong_withholding_or_reservation": wrong,
        "clock": "API_SEND_TO_COMPLETE_RESPONSE" if published else "API_SEND_TO_TERMINAL_FAILURE",
        "milliseconds": journey["api_send_to_complete_response_ms"] if published else journey["api_send_to_terminal_ms"],
        "posts": finance["actual_posts"], "known_cost_USD": finance["native_settled_known_cost_USD"],
        "journey_pin": pin(directory / "journey-receipt88.json")})
assert sum(row["required_facets"] for row in matrix) == 32
assert sum(row["draft_complete"] for row in matrix) == 29
assert sum(row["published_complete"] for row in matrix) == 15
assert sum(row["fragment_rows_sent_per_case"] for row in matrix) == 489
pages = []
for case, base in (("case10", "case06"), ("case10b", "case09")):
    journey = read(R / case / "journey-receipt88.json")
    terminal = read(R / case / "root-page-terminal88.json")
    finance = read(R / case / "native-provider70/final-receipt.json")
    pages.append({"case_id": case, "base_case_id": base, "version": "A", "independent_QA": "FAIL",
        "published_complete_DOM": case == "case10b", "quality_qualified_DOM_n": 0,
        "send_to_complete_DOM_ms_technical_only": journey.get("send_to_complete_dom_ms"),
        "failure": "CHECKER_OUTPUT_TRUNCATED_NO_PUBLISHED_ANSWER" if case == "case10" else "CRITICAL_OWN_UNIT_PROOF_UNDERSELECTION",
        "posts": finance["actual_posts"], "known_cost_USD": finance["native_settled_known_cost_USD"],
        "original_pending_zero_qualification_preserved": terminal["qualified_complete_answer_n"] == 0,
        "original_journey_pin": pin(R / case / "journey-receipt88.json"), "original_terminal_pin": pin(R / case / "root-page-terminal88.json")})
assert pages[0]["send_to_complete_DOM_ms_technical_only"] is None
assert abs(pages[1]["send_to_complete_DOM_ms_technical_only"] - 17962.3) < 0.001
qualification_path = create("phase89-page-qualification-root.json", {"schema": "dev89_independently_derived_page_qualification_v1",
    "new_page_attempt_denominator": 2, "technical_complete_DOM_n": 1, "independently_qualified_complete_DOM_n": 0,
    "qualified_complete_DOM_latency_ms": [], "TTFT_ms": None, "stable_p95_ms": None,
    "historical_Phase88_qualified_sample_ms": "20437.10000000149", "historical_sample_not_new_trial": True,
    "historical_root_qualification_pin": pin(W / "phase88-page-qualification-root.json"),
    "independent_fresh_page_review_pin": pin(N / "page-review89.json"), "cases": pages,
    "original_Pending_and_n0_receipts_rewritten": False, "goal_5_to_10_seconds_met": False, "quality_latency_improvement_proven": False})
final_path = create("phase89-unified-results-root.json", {"schema": "dev89_root_science_software_and_clock_results_v1",
    "finished_utc": datetime.now(timezone.utc).isoformat(), "authorization": raw_results["authorization"],
    "protocol_sha256": raw_results["protocol_sha256"], "baseline_denominator": 8, "required_facets": 32,
    "exposed_AI_curated_DEV": True, "specific_new_points_not_used_in_Phase88_tuning": 4,
    "formal_blind_or_heldout": False, "HumanGold": None, "source_version_A": adoption["source_version_before_sha256"],
    "source_version_B": adoption["source_version_after_sha256"], "cohort_financial": totals,
    "source_complete_cases": 7, "source_partial_cases": 1, "per_case_occurrence_fragment_rows_reviewed": 489,
    "draft_complete_facets": 29, "draft_partial_facets": 2, "draft_missing_facets": 1,
    "published_complete_facets_of32": 15, "published_partial_facets_of32": 1, "unpublished_required_facets": 15,
    "published_missing_facets": 1, "API_published_cases": 4, "pipeline_failed_cases": 4,
    "independent_scientific_QA_PASS_cases": 2, "independent_scientific_QA_FAIL_cases": 6,
    "matrix": matrix, "pages": pages, "new_quality_qualified_DOM_n": 0, "new_page_attempt_denominator": 2,
    "B_actual_model_POSTs": 0, "B_affected_control_retest_status": "BOUND_FROZEN_NONPAGE_BUDGET",
    "B_model_quality_or_speedup_certified": False, "software_verification": pin(software_path),
    "raw_runtime_results": pin(R / "results89.json"), "independent_page_qualification": pin(qualification_path),
    "failure_counts_not_filtered_out": True, "checker_LOW_enabled": False, "TTFT_ms": None, "stable_p95_ms": None,
    "full_course_completed": False, "remote_push_upload_deploy_or_submission": False})

table = ["| Instance / A topic · sent fragment rows | Actual source sufficiency | Facets: draft → published | Citation / independent QA | Wrong withholding or valid gap | Published | Clock / result | POST / USD |",
         "|---|---|---|---|---|---|---|---|"]
for row in matrix:
    draft = f"{row['draft_complete']}/{row['required_facets']} complete"
    if row["draft_partial"]:
        draft += f", {row['draft_partial']} partial"
    if row["draft_missing"]:
        draft += f", {row['draft_missing']} missing"
    delivered = f"{row['published_complete']}/{row['required_facets']}" if row["publication"] else "0 (unpublished)"
    label = "API complete" if row["publication"] else "API failure"
    table.append(f"| {row['case_id']} {row['topic']} · {row['fragment_rows_sent_per_case']} | {row['actual_source_sufficiency']} | {draft} → {delivered} | {row['finding']} | {row['wrong_withholding_or_reservation']} | {'Yes' if row['publication'] else 'No'} | {label} {row['milliseconds']/1000:.5f}s | {row['posts']} / {row['known_cost_USD']} |")
table += ["| case10 page / case06 | FULL | 4/4 draft → 0 | FAIL: uncited opener; checker truncation | Wire failure | No | No complete DOM | 2 / 0.0299291 |",
          "| case10b page / case09 | FULL | 4/4 content → 4/4 | FAIL: three required unit proof selections incomplete | No | Yes | Technical complete DOM **17.96230s**; qualified n=0 | 2 / 0.0199510 |"]
report = f"""# DEV89 learning-assistant quality, timing and one local repair

This checkpoint closes eight fixed DEV questions and two distinct native-page attempts. Version A published 4/8 API responses; independent full-answer science, coverage and own-source review passed 2/8 and failed 6/8. Both new page attempts failed quality qualification (0/2), although one displayed a complete answer in 17.96230 seconds. Current Main Version B contains one reviewed input-only checker repair and passes 4532 unit tests. B has no actual model quality or latency sample. Project and latency acceptance remain open.

The new bounded cohort used **28 physical model POSTs / USD 0.4056684**, with 28 numerical settlements, UNKNOWN=0 and no terminal exposures. BASE used 24 POSTs / USD 0.3557883; pages used 4 POSTs / USD 0.0498801. All ten isolated API instances closed their owned worker threads and retained the five original metadata groups. Both page controllers closed their owned process trees and readers. Existing HTTP retries remained zero; the ordinary bounded teacher/checker correction calls are included in the physical denominator. Old cohorts and their unresolved records remain separate.

All actual rows below use A `{adoption['source_version_before_sha256']}`: teacher `anthropic/claude-haiku-5.5`, 4096 output limit, profile `haiku55_google_vertex_low_v1`; checker `google/gemini-3.5-flash-lite`, HIGH, 8192 output limit, profile `gemini35_google_vertex_high_research_v1`, `lossless_unit_findings_v1`. The full frozen configuration SHA is `22ae720ae20828cf62fa921b2793db12d8f229e33512b7b904c221fa39832047`. R2 uses the existing E5/cross-encoder CPU caches and ordinary full-release retrieval, not a question-specific chapter filter. Sources are the same four approved public OpenStax textbooks, 10594 chunks, release `4f11bd70-a486-4d16-b216-78cfe499530a`, in the original synthetic test fixture at 127.0.0.1:15433. The packet count is 489 fragment rows across eight cases, counting per-case occurrences, not 489 unique facts or documents.

The protocol froze eight questions and 32 required facets before the first POST. Four specific points were absent from Phase88 tuning, while broad biology/chemistry topics may overlap earlier project work. This is exposed, AI-curated DEV with independent AI source review, not a formal blinded/heldout study or HumanGold evaluation. No learner identity/history or authentication contents entered model requests or this archive.

The following is the interview result table. Coverage measures requested content separately from scientific and citation correctness. Failure clocks terminate at an API failure and are not complete-answer samples. The two page rows are fresh answers; baseline eligibility does not transfer their scientific status.

{chr(10).join(table)}

BASE evidence is complete for 7/8 cases; calorimetry retains a real apparatus-paragraph retrieval gap. Draft content covers 29/32 facets completely, two partially and one not at all; a draft can still contain a contradictory extra claim. Actually published complete content covers 15/32 facets, with one published partial, one published missing, and fifteen unpublished. These are content counts, not 15 science-qualified facets or learner-effect scores. The independent case06/case09 baseline passes retain the qualitative inference and direction/context clarity limitations in their reviews. The fresh DNA page has different unit selections: F013 does not establish the Pol I predicates in its U01, and the actual necessary F014 is selected only by a sibling unit. Complete parent citations cannot be relabelled as this unit's returned proof.

The Cu/Ag packet actually contains electron transfer through an external circuit and the Cu-to-Ag donor/acceptor relation. Its E3/E4 withholding is erroneous, not RAG_MISS. The local coverage metadata lists a budget-lost requirement despite those submitted fragments; it is a conflicting signal, not a proven causal explanation. The gas draft's 500*300/250=600 mL inference is correct; the checker rejected that calculation while other real citation defects coexist. Missing experimental calorimeter capacity legitimately prevents a numerical joule answer. Its solution-only bomb balance is an additional scientific defect. Truncated or malformed checker outputs are wire failures and are not silently counted as semantic refusal or semantic PASS.

The previously independently qualified 20.43710-second page remains one historical sample. Its measured exclusive decomposition is preparation 46.479ms, retrieval 1605.834ms, teacher 3618ms, checker 13194ms, other generation 441.975ms, other backend 454.777ms, and outside-worker residual 1076.035ms. They sum to 20437.100ms; the checker is 64.56% of that observed DOM duration and is the largest measured target. Query/plan, publication, queue markers and worker/generation totals are nested or partially overlapping and are not added again. The fresh technical DNA page has 3771ms teacher, 9659ms checker and 2120.905ms retrieval within its worker/DOM clocks, but fails quality. There is no demonstrated B speedup, qualified new-page duration, stable p95, TTFT, 5–10-second success or learner-effect result. Checker LOW remains a retained negative and was not enabled. Existing RAG69 arm results remain historical; this R2 DEV batch is not a new E0/E1 quality comparison.

One principal local repair changed only `generation/lossless_unit_findings_v1.py` from `81045fec9ddc851eda6f445bdd99b20c056de07c36a8acb7264fdbc5c2f5d459` to `8c830694093b41e9f6250939de2cf9f72b24726bddbc1cba0141a6b8cb9efa56`. B is `{adoption['source_version_after_sha256']}`. The program now supplies all unchanged C/unit/own-evidence domains and exact per-variant short field keys, with valid whole-F and long-Q quote domains. The input index supplies no selections, classifications, statuses or defaults. It addresses three observed common format defects: missing parent status, mixed `relation`/`rl`, and unit selections outside their parent's actual selected set. The complete source/claims/requirements, schemas, strict decoder and semantic/publication gates retain their original definitions. All other fifteen frozen source files and defaults match A. The original one-file code is preserved in W and this evidence selection.

Fourteen finite offline control groups passed; the five original malformed outputs still fail, with no repaired fields, status promotion or deleted required content. Eight BASE cases' fourteen actual checker wires were reconstructed with 3944–5776 additional bytes; maximum complete wire size is 106901 bytes, inside the existing byte bounds. The configured-price byte-proxy bound is conditional, not a tokenizer or current public Vertex-price proof. The two official endpoint price reads were unavailable through the web tool and were not bypassed or retried. Actual fees above come from numerical provider observations retained before model parsing.

Current B free verification: **198 contract tests PASS; 4532 full unit tests plus 215 subtests PASS, 21 optional SDK bridge tests skipped, 40 warnings; Ruff PASS**. Full pytest duration is 166.94s and owned parent duration 169.67378s. The first full attempt is preserved: Windows access violation `0xC0000005` after 40.60976s, not a parent timeout, without completed XML/guard receipt. Its crash stack references pytest FD capture/tempfile; the cause is not established. A finite retry reused the unchanged isolation guard and changed global pytest capture to `sys`, while explicit `capfd` remains FD. The successful run includes current B before/after pins and final sixteen-file readback. One urllib3 IPv6 capability bind probe was blocked by the isolation guard; no paid network or real PostgreSQL access was admitted. This is unit verification, not a clean install, fresh frontend/all-eight-stage verification, device study or full-course completion.

The frozen cohort allowed 32 POSTs/USD2 but reserved eight for two pages through a nonpage cap of 24. BASE consumed all 24; each affected/control admission requires nonpage+4<=24, so **B affected/control model retesting is blocked by that frozen allocation**. Authorization is present and dollars are not exhausted. No ledger, cap or runner was changed to obtain more calls, and the four globally unused slots are not an automatic new entitlement. All actual A instances closed before B adoption; their outcomes must not be represented as B tests. A revised bounded protocol allocation is required before a future B model iteration. That iteration should test only an affected format case plus a control, retain genuine source gaps and erroneous withholding as separate controls, and admit any new page only after its own current-B independent QA. Historical failed cases, source defects and financial uncertainty are retained.

The unified machine result is [root-results89.json](20261012-dev89-evidence/root-results89.json); original runtime results, independent case/page reviews, source versions, finite controls, unit/crash records, budget settlements and exact file hashes are in [readback-manifest89.json](20261012-dev89-evidence/readback-manifest89.json). Previous reports and database/experiment inputs were preserved. No branch reset, install, remote push/upload, deployment or course submission occurred.
"""
report_path = W / "phase89-final-report.md"
with report_path.open("xb") as out:
    out.write(report.encode())

selection = []
def add(source, destination):
    source = Path(source)
    assert source.is_relative_to(W) and not source.is_symlink()
    assert not any(word in source.name.lower() for word in ("binder", ".env", "sealed", "private-rubric"))
    selection.append({**pin(source), "destination": destination})
add(final_path, "root-results89.json")
add(software_path, "software-verification89.json")
add(qualification_path, "page-qualification-root89.json")
add(W / "phase89-codec-preimage.py", "source-A/lossless_unit_findings_v1.py")
for path in sorted(R.rglob("*.json")):
    add(path, "runtime-A/" + path.relative_to(R).as_posix())
for path in sorted(R.iterdir()):
    if path.is_file() and path.suffix in (".py", ".cjs", ".mjs"):
        add(path, "runtime-A/" + path.name)
for path in sorted(Q.glob("*-review89.json")):
    add(path, "independent-known/" + path.name)
for path in sorted(N.glob("*.json")):
    add(path, "independent-new/" + path.name)
for name in ("public-protocol89-frozen.json", "baseline-source89.json", "latency-breakdown89.json", "price-and-codec89.json",
             "codec-diagnosis89.json", "final-stage-audit89-candidate.json", "unit-crash89-readonly-audit.json", "common-repair-adoption89-root.json"):
    add(P / name, "preparation/" + name)
for name in ("lossless_unit_findings_v1.py", "selection-index89.patch", "control_selection_index89.py", "control-selection-index89-frozen.json", "release-selection-index89.json"):
    add(P / "selection-index-candidate" / name, "source-B/" + name)
for folder in (failed, focused, full):
    for name in ("receipt.json", "pytest.log", "pytest.xml", "tripwire.json", "faulthandler.log"):
        if (folder / name).is_file():
            add(folder / name, "software/" + folder.name + "/" + name)
for name in ("verify_unit89_root.py", "run-unit88-root.py", "adopt_common89_root.py", "finalize89_root.py"):
    add(W / name, "tools/" + name)
assert len({row["destination"] for row in selection}) == len(selection)
selection_path = create("phase89-evidence-selection.json", selection)
preimages = []
for relative, expected in (("docs/execution/progress.md", "165e213e4b89dd8723416b9595cd887c97162c7ef3e6e9780252c4c3e5bf887a"),
                           ("docs/foundation/handover_migration.md", "e379e3197ebbab179b32a7effe1902ab7c771ff9dc6e851430bff32454afd54c")):
    record = pin(M / relative)
    assert record["sha256"] == expected, "PRESERVE_CONCURRENT_DOCUMENT_CHANGES"
    preimages.append(record)
old_report = pin(M / "docs/execution/20261011-checker88-common-contract-results.md")
assert old_report["sha256"] == "856a3969952fba6b3e938047e67db4633f111cfb68f9ea011ad6237ddab4f0dc"
append_text = "\n\n## 2026-10-12 DEV89 source B software repair and bounded A results\n\nOne input-only lossless V1 selection-index repair is current in Main (codec 8c830694...efa56; sixteen-file B source 369bba3c...b2fc). Free B verification passed 198 relevant tests and the full 4532 tests plus 215 subtests, with 21 skips/40 warnings and Ruff PASS. The first native 0xC0000005 unit crash is preserved; a finite sys-capture retry passed under the unchanged isolation guard.\n\nActual model evidence remains source A: eight frozen DEV cases/32 facets, 4/8 published and 2/8 independent science QA passed; two distinct pages had 0/2 quality-qualified complete DOM results. The 17.9623-second DNA DOM result failed required unit proof, while the older 20.4371-second qualified page remains one historical sample. New cohort 28 POST/USD0.4056684/UNKNOWN0; all owned processes/threads closed and old metadata retained. The frozen nonpage24 reservation blocks B affected/control retesting; fee authorization is present and USD2 was not exhausted. No B quality/speedup, 5–10-second/p95/HumanGold/full-course success is claimed. No additional requests or cap changes occurred.\n\nSee [DEV89 unified report](../execution/20261012-dev89-quality-latency.md) and its single final evidence archive. Keep all original user changes, protected databases/experiment data, old deliveries and unresolved prior financial records. Next model work needs a revised finite allocation, affected/control-only B evaluation and fresh independent page QA.\n"
for name in ("phase89-progress-append.md", "phase89-handover-append.md"):
    with (W / name).open("xb") as out:
        out.write(append_text.encode())
ready = {"schema": "dev89_concrete_publication_ready_v1", "status": "READY_FOR_READ_ONLY_REVIEW",
    "report": pin(report_path), "selection": pin(selection_path), "selected_payload_count": len(selection),
    "selected_payload_bytes": sum(row["bytes"] for row in selection), "append_preimages": preimages,
    "progress_append": pin(W / "phase89-progress-append.md"), "handover_append": pin(W / "phase89-handover-append.md"),
    "source_version_B": adoption["source_version_after_sha256"], "current_source_pins": adoption["source_pins_after"],
    "old_report_preserved_pin": old_report, "Main_target_report": str(M / "docs/execution/20261012-dev89-quality-latency.md"),
    "Main_target_evidence": str(M / "docs/execution/20261012-dev89-evidence"), "no_private_auth_or_rubric_payload_copied": True,
    "publication_authorized_in_session": True, "actual_B_POSTs": 0, "new_quality_qualified_DOM_n": 0}
create("phase89-publication-ready.json", ready)
print(json.dumps({"status": ready["status"], "selected_payload_count": len(selection), "selected_payload_bytes": ready["selected_payload_bytes"], "report_bytes": ready["report"]["bytes"], "current_B_tests": 4532, "actual_POSTs": 28, "known_cost_USD": "0.4056684", "quality_BASE": "2/8", "quality_page": "0/2"}))
