"""Append observed local audit evidence without changing original requirements."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BROWSER = "artifacts/reports/frontend/keyboard-suggestion/2026-09-08T09-54-55-082Z/verification.json"
BINDING = "evidence/frontend/keyboard-request-binding-20260908T095633Z/verification.json"
ADAPTER = "evidence/operations/adapter-replacement/verification.json"
REPORT = "docs/execution/local-audit-continuation.md"


def main():
    now = datetime.now(timezone.utc).isoformat()
    path = ROOT / "docs/execution/acceptance.json"
    ledger = json.loads(path.read_text("utf-8"))
    if ledger.get("local_audit_continuation"):
        raise RuntimeError("This dated amendment has already been applied")
    observations = {
        "AC-19": (
            "MOCK_TEST_PASSED",
            "The original honesty clause is verified by frozen manifests, missing-label/rating nulls, all-outcome retention and explicit mock/live separation. Actual real-source/SciQ technical records preserve failures and do not claim research quality.",
            ["Actual independent qrels, blind ratings and real-answer runs remain absent in their original research tasks. Their absence does not prevent verification of this honesty behavior."],
            [REPORT],
        ),
        "AC-34": (
            "MOCK_TEST_PASSED",
            "The same unmodified GenerationService switches mock to actual loopback HTTP and back through configuration for chat/OpenQA/MCQ. Five tests verify distinct valid authored responses, exact role/profile/evidence/schema transmission, usage and standard bounded HTTP/citation failures. Existing real PDF/TXT and PostgreSQL R0/R1 evidence remains separate.",
            ["The loopback response is an authored software fixture, not a learned answer model. Actual configured provider connectivity remains user-deferred under GEN-02; the shared-service drill is not itself a persisted API job."],
            [ADAPTER, "docs/execution/adapter-replacement-drill.md", "tests/unit/test_adapter_replacement.py", REPORT],
        ),
        "AC-44": (
            "REAL_FLOW_VERIFIED",
            "Actual browser key presses verify Shift+Enter newline/no submission and Enter exact single submission. A persisted socratic suggestion sends its exact text once. Real polled stages match display; archived-session HTTP409 retains the draft and historical rows. Error alerts are fully visible at1440/390, and restore/reload preserves complete history/draft. Earlier actual clipboard, keyboard citation, stop/retry and other browser evidence retains its scope. Current gate includes25 frontend checks.",
            ["Answering remains mock. This new failure case is a real submission rejection, not provider execution fault injection. Physical/native/independent-human checks remain in UI-05/UI-09 and FE-12, without relabelling desktop key events as physical mobile or native IME evidence."],
            [BROWSER, BINDING, "docs/execution/keyboard-suggestion-verification.md", REPORT],
        ),
    }
    for row in ledger["checks"]:
        if row["check_id"] not in observations:
            continue
        status, actual, remaining, evidence = observations[row["check_id"]]
        row.setdefault("reconciliation_history", []).append({
            "superseded_by": "local_requirement_audit_continuation",
            "observation": deepcopy({k: v for k, v in row.items() if k != "reconciliation_history"}),
        })
        paths = list(dict.fromkeys(row.get("evidence_paths", []) + evidence))
        assert all((ROOT / p).exists() for p in paths)
        row.update(status=status, actual=actual, remaining_scope=remaining, evidence_paths=paths,
                   reconciled_at=now, completion_claim=False,
                   verification_note="Current unchanged-source gate:236 Python and25 frontend tests. Historical scenarios retain their original dates/data/mode scope; only the cited new runs are new observations.",
                   component_statuses=[{"component": "observed original software clause", "status": status, "detail": actual}, {"component": "separate unverified research/device scope", "status": "WAITING_EXTERNAL", "detail": remaining}])
        if row["check_id"] == "AC-34":
            row["test_nodes"] = list(dict.fromkeys(row.get("test_nodes", []) + [
                "tests/unit/test_adapter_replacement.py::test_configuration_switch_keeps_shared_consumer_modes_context_and_citations",
                "tests/unit/test_adapter_replacement.py::test_configured_http_failures_use_shared_error_and_repair_bounds",
            ]))
    ledger["local_audit_continuation"] = {"recorded_at": now, "report": REPORT, "checks": list(observations), "project_complete": False}
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", "utf-8")

    path = ROOT / "docs/execution/ui_acceptance.json"
    ui = json.loads(path.read_text("utf-8"))
    row = next(r for r in ui["checks"] if r["check_id"] == "UI-11")
    row.setdefault("reconciliation_history", []).append({"checkpoint": "before_local_error_visibility_fix", "observation": deepcopy({k: v for k, v in row.items() if k != "reconciliation_history"})})
    row["actual"] += " New real-browser rejection checks at1440/390 verify the whole alert without manual scrolling; automatic reveal respects intentional older reading. Drafts/history and original failed attempts are preserved."
    row["evidence_paths"] = list(dict.fromkeys(row["evidence_paths"] + [BROWSER, "docs/execution/keyboard-suggestion-verification.md"]))
    row["reconciled_at"] = now
    ui["reconciled_at"] = now
    path.write_text(json.dumps(ui, indent=2, ensure_ascii=False) + "\n", "utf-8")

    path = ROOT / "docs/execution/blockers.json"
    blockers = json.loads(path.read_text("utf-8"))
    for row in blockers["blockers"]:
        if row["id"] in {"INPUT-LIVE-MODEL", "INPUT-ANNOTATIONS-RATINGS"}:
            row["previous_affected_checks"] = row["affected_checks"]
            row["related_acceptance_ids"] = row["affected_checks"]
            row["affected_checks"] = []
            row["component_scope"] = "These unavailable inputs block the named research/live-provider task components. AC-19 honesty and AC-34 simulated adapter switching have local software evidence; absent research inputs are not missing prerequisites for those software checks."
    blockers["updated_at"] = now
    blockers["latest_local_audit"] = REPORT
    path.write_text(json.dumps(blockers, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print("Appended AC-19/34/44 and UI-11 observations; original clauses and external research/device scope preserved.")


if __name__ == "__main__":
    main()
