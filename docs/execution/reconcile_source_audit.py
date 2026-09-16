"""Reconcile the preserved v5 registry with observed, explicitly bounded evidence.

Run from the repository root. This is a documentation audit, not a test runner.
Original documents and imported requirements are never modified.
"""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT.parent / "development_inputs"
PACKAGE = INPUT / "CS30-1_Full_Project_v5"
OUTPUT = ROOT / "evidence/source_audit"
OUTPUT.mkdir(parents=True, exist_ok=True)
NOW = datetime.now(timezone.utc).isoformat()
R = "REAL_FLOW_VERIFIED"
M = "MOCK_TEST_PASSED"
I = "IMPLEMENTED_UNVERIFIED"
N = "NOT_IMPLEMENTED"
W = "WAITING_EXTERNAL"
STATUS = {
    N: "The named required artifact or result is absent.",
    I: "Implementation exists, but required verification or a material part of acceptance remains open.",
    M: "The cited software scope passed with mock/simulated model or authored test inputs; no real-model quality claim.",
    R: "The cited real component flow ran (for example parser, PostgreSQL, HTTP or browser); read the explicit component boundary, not a whole-project claim.",
    W: "The named remaining requirement needs a genuinely unavailable external input; independent work continues.",
}

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

tasks_path = ROOT / "docs/execution/tasks.json"
checks_path = ROOT / "docs/execution/acceptance.json"
tasks = read_json(tasks_path)
checks = read_json(checks_path)
source_tasks = read_json(PACKAGE / "TASKS_V5.json")
source_checks = read_json(PACKAGE / "ACCEPTANCE_V5.json")
task_ids = {x["task_id"] for x in tasks["tasks"]}
check_ids = {x["check_id"] for x in checks["checks"]}
assert task_ids == {x["task_id"] for x in source_tasks["tasks"]}
assert check_ids == {x["check_id"] for x in source_checks["checks"]}

documents = [
    Path("C:/Users/PC/Downloads/CS30-1_Full_Project_Development_Taskbook_Chinese_v5 (1).docx"),
    Path("C:/Users/PC/Downloads/CS30-1_Codex_Full_Project_Prompt_English_v5.docx"),
    PACKAGE / "CODEX_MASTER_PROMPT_EN_v5.md",
    PACKAGE / "DEVELOPMENT_TASKBOOK_ZH_v5.md",
    INPUT / "FRONTEND_UI_RESPONSIVE_REQUIREMENTS_EN.md",
]
source_reads = []
for source in documents:
    raw = source.read_bytes()
    entry = {"path": str(source), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
    if source.suffix == ".docx":
        with ZipFile(source) as archive:
            xml = ET.fromstring(archive.read("word/document.xml"))
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = ["".join(t.text or "" for t in p.findall(".//w:t", ns)) for p in xml.findall(".//w:p", ns)]
            content = "\n".join(paragraphs)
            entry.update(paragraphs_in_body_order=len(paragraphs), tables=len(xml.findall(".//w:tbl", ns)),
                         embedded_media=[x for x in archive.namelist() if x.startswith("word/media/")])
            candidates = list(PACKAGE.glob("*Taskbook_Chinese_v5.docx")) if "Taskbook" in source.name else list(PACKAGE.glob("*Prompt_English_v5.docx"))
            entry["archive_copy_hash_matches"] = any(sha256(p.read_bytes()).hexdigest() == entry["sha256"] for p in candidates)
    else:
        content = raw.decode("utf-8-sig")
    entry.update(characters=len(content), text_sha256=sha256(content.encode()).hexdigest(),
                 task_ids_present=sorted(task_ids & set(re.findall(r"(?:INT|DAT|RET|GEN|PER|BE|FE|QA|CHAT)-\d{2}", content))),
                 acceptance_ids_present=sorted(check_ids & set(re.findall(r"(?:AC|HC)-\d{2}", content))),
                 inspection="Complete file re-extraction and ID/structure reconciliation; scope, contracts, technical sections and appendices reviewed against canonical task/check requirements.")
    source_reads.append(entry)

originals = [
    ("CS30-1_Project_Framework_and_Delivery_Workflow.pdf", [1], "Original full-system Figure 1"),
    ("tut5/xianshu/architecture-en-preview.png", [], "Original baseline image; unpaginated"),
    ("了解项目/CS30-1_Project_Overall_Requirements_CN.pdf", [5, 6], "Original six-module grid and numbered flows"),
    ("tut5/Chong Zhang/Framework.pdf", [1], "Original evaluation graph"),
    ("tut5/xianshu/basicframework.png", [], "Repository screenshot; incomplete README diagram"),
]
source_root = INPUT / "sources/COMP5703"
visuals = [{"path": str(source_root / name), "sha256": sha256((source_root/name).read_bytes()).hexdigest(),
            "pages_visually_inspected": pages, "whole_image_inspected": not pages, "description": meaning}
           for name, pages, meaning in originals]
search_paths = sorted(str(p.relative_to(source_root)) for p in source_root.rglob("*")
                      if p.is_file() and p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".svg", ".drawio"})
write_json(OUTPUT / "source_read_manifest.json", {"recorded_at": NOW, "documents": source_reads,
    "visual_sources": visuals, "visual_source_search_inventory": search_paths,
    "read_only_originals": True, "source_search_boundary": str(source_root),
    "four_book_authority": "tut5/HongleYang/WEEK4_SUMMARY_AND_WEEK5_PLAN.md lines 12-14",
    "official_books_required": ["Biology 2e", "Chemistry 2e", "Anatomy & Physiology 2e", "Concepts of Biology"],
    "retired_book_excluded": "College Physics", "interpretation": "Documentation requirements and historical claims are not current execution proof."})

# A row-specific status is deliberately distinct from its component observations.
status_groups = {
 R: "INT-03 DAT-02 DAT-04 DAT-05 DAT-06 DAT-07 DAT-10 RET-02 BE-03 BE-04 BE-05 BE-10 BE-14 FE-02 FE-06 FE-07 FE-09",
 M: "INT-04 INT-06 INT-08 DAT-11 RET-03 RET-04 RET-05 RET-06 RET-07 RET-08 RET-10 GEN-01 GEN-03 GEN-04 GEN-05 GEN-06 GEN-07 GEN-08 GEN-09 GEN-10 PER-01 PER-02 PER-04 PER-05 PER-06 PER-08 BE-01 BE-06 BE-07 BE-08 BE-09 BE-11 BE-12 BE-15 FE-01 FE-03 FE-04 FE-08 FE-11 QA-01 QA-02 QA-03 QA-05 QA-06 QA-08 CHAT-02 CHAT-03 CHAT-04 CHAT-05 CHAT-06 CHAT-07 CHAT-09 CHAT-10",
 N: "DAT-03 RET-11 PER-09",
 W: "QA-04 QA-07 QA-10",
 I: "INT-01 INT-02 INT-05 INT-07 INT-09 INT-10 DAT-01 DAT-08 DAT-09 DAT-12 RET-01 RET-09 GEN-02 GEN-11 PER-03 PER-07 BE-02 BE-13 BE-16 BE-17 FE-05 FE-10 FE-12 QA-09 QA-11 QA-12 QA-13 QA-14 CHAT-01 CHAT-08 CHAT-11 CHAT-12",
}
task_status = {identifier: status for status, ids in status_groups.items() for identifier in ids.split()}
assert set(task_status) == task_ids, (task_ids - set(task_status), set(task_status) - task_ids)

AI = "evidence/ai/verification.json"
EV = "evaluation/software_verification.log"
UI = "docs/execution/audit-ui.md"
CHAT = "evidence/integration/postgres_lifecycle.log"
FAULT = "evidence/integration/runtime_faults.log"
OPS = "evidence/integration/operations.log"
CONTRACT = "evidence/contracts/verification.json"
SCOPE = "evidence/contracts/chat_scope.json"
JOURNEYS = "evidence/integration/chat_journeys.json"
RESTORE = "evidence/recovery/backup-20260908-verified/restore-cs30_restore_20260908.json"
LEGACY = "evidence/legacy/generation_manifest_audit.json"
AUDIT = "docs/execution/source-architecture-audit.md"

groups = {
 "INT": (["docs/foundation/requirements.md", "docs/foundation/architecture.md", "scripts/verify/foundation.py", "compose.yaml"], ["scripts/verify/contracts.py", "scripts/verify/chat_scope.py"], [AUDIT, CONTRACT, SCOPE, JOURNEYS]),
 "DAT": (["pipelines", "backend/app/modules/knowledge/service.py", "docs/data_rebuild.md"], ["tests/unit/test_pipeline.py", "tests/integration/test_corpus_runtime.py"], [AI, "docs/execution/audit-ai.md"]),
 "RET": (["retrieval/embedding.py", "retrieval/ranking.py", "backend/app/modules/knowledge/service.py"], ["tests/unit/test_retrieval.py", "tests/integration/test_corpus_runtime.py"], [AI, "docs/execution/audit-ai.md"]),
 "GEN": (["generation/service.py", "generation/adapters.py", "generation/parser.py", "generation/prompt_builder.py", "generation/prompts"], ["tests/unit/test_generation_contracts.py", "tests/unit/test_generation_engine.py"], [AI, "docs/execution/audit-ai.md"]),
 "PER": (["personalisation/compiler.py", "personalisation/study.py", "personalisation/rubric.py"], ["tests/unit/test_profiles.py", "tests/unit/test_evaluation_study.py", "tests/integration/test_evaluation_postgres.py"], [AI, EV, "docs/execution/audit-evaluation.md"]),
 "BE": (["backend/app/modules", "backend/app/worker.py", "backend/app/core", "backend/alembic/versions"], ["tests/integration/test_chat_runtime.py", "tests/integration/test_runtime_faults.py", "tests/integration/test_operations.py"], [CHAT, FAULT, OPS]),
 "FE": (["frontend/src", "docs/frontend.md"], ["frontend/tests"], [UI]),
 "QA": (["evaluation", "configs/evaluation"], ["tests/unit/test_evaluation_metrics.py", "tests/integration/test_evaluation_postgres.py"], [EV, "docs/execution/audit-evaluation.md"]),
 "CHAT": (["conversation", "backend/app/modules/answering/service.py", "frontend/src/Chat.tsx"], ["tests/unit/test_conversation.py", "tests/integration/test_chat_runtime.py", "tests/integration/test_evaluation_postgres.py"], [AI, CHAT, EV, JOURNEYS, UI]),
}

notes = {
 "INT-01": "Original diagrams now identified; source/implementation mapping and preserved manifests exist. Historical missing assets remain explicit; this first pass is not every final delivery check.",
 "INT-02": "Chat-first requirements and source authority reconciled; root PRD/SPEC/PLANS and stale audit wording are being updated for four official books and real local embeddings.",
 "INT-03": "54 OpenAPI paths/64 schemas and two-field chat input verified; schema verification is real local validation, not model behavior.",
 "INT-04": "Actual clean Compose rebuild and persisted authored chat observed with mock generation/embedding; complete official-corpus rebuild remains separate.",
 "INT-05": "Schema/unit/PostgreSQL/frontend/browser checks exist. No full format/lint/Python-type/CI evidence is established by this snapshot.",
 "INT-06": "Real API/worker/DB/browser authored chat and follow-up recorded; generation and embeddings mock. This original task expressly permits authored sources.",
 "INT-07": "Connected journeys have evidence, but administrator rollback retest and final combined browser run remain open.",
 "INT-08": "Freeze/register/resume/protocol tooling exercised through actual PostgreSQL with authored fixtures; official data/model runs not measured.",
 "INT-09": "Blocker register exists; official acquisition and learned embeddings must be removed from older deferred-work wording. Only actual missing external inputs block dependent research.",
 "INT-10": "Runnable implementation exists; complete official corpus, real embedding flow, final source reconciliation, package verification and research/human limitations still require closure.",
 "DAT-01": "Authored manifest and official catalogue evidence exist. Complete four-book downloaded bytes, actual editions/licences/hashes and ingestion manifest not yet established.",
 "DAT-02": "Actual PDF/TXT upload validation, content-hash reuse and failed-input exclusion tested on real PostgreSQL; authored inputs only.",
 "DAT-03": "Historical original pilot PDF hash and pages 1-2 review absent. New official edition must be recorded as a new asset rather than retroactive review.",
 "DAT-04": "Real authored PDF extraction and TXT dispatch tested; full-book reading order, page completeness and authentic section boundaries remain a corpus-level gap.",
 "DAT-05": "Actual source-unit quality, raw/clean hashes, blocking issues and persisted quality export tested; full-book QA not performed.",
 "DAT-06": "Actual deterministic chunker/source spans and section boundaries tested on authored text; full-book token/section sampling pending.",
 "DAT-07": "Same raw bytes with changed processing produce separate persisted runs and meaningful diff exports; historical identities remain intact.",
 "DAT-08": "Validated authored releases and integrity rejection implemented; complete four-book learned-vector release is absent.",
 "DAT-09": "Gold-free adapters implemented and tested on authored SciQ-shaped rows. Actual SciQ revision/splits/checksums still need acquisition; no runtime dependency on SciQ.",
 "DAT-10": "Real PostgreSQL deactivation/restoration/reprocessing/rollback and old evidence tests passed on authored releases; final browser rollback needs a valid fresh baseline.",
 "DAT-11": "Two chunking strategies and compatible-span/qrel checks implemented; controlled official-corpus comparison not run.",
 "DAT-12": "Portable authored rebuild guide exists; actual four-book counts, exclusions, QA decisions and full rebuild evidence remain missing.",
 "RET-01": "Learned embedding adapter exists, but cited execution uses model doubles. Must download/pin/execute actual local weights/tokenizer before claiming real embedding readiness.",
 "RET-02": "Actual pgvector exact cosine search/ranking and integrity constraints tested on numeric vectors in PostgreSQL; semantic quality not inferred.",
 "RET-09": "Configurable cross-encoder wrapper exists; actual checkpoint inference and resource/window evidence not yet executed.",
 "RET-10": "One-factor manifest/qrel compatibility validation and preparation tooling passed; actual controlled runs remain separate.",
 "RET-11": "No actual controlled retrieval quality/resource finding exists. Run after official corpus/local models and required relevance judgements are ready.",
 "GEN-02": "Deterministic mock and simulated hosted adapter tests pass. Current live connectivity/one configured real answer provider is user-deferred, never silently replaced.",
 "GEN-11": "Generation migration and current software audit exist; final documentation must correct stale real-embedding deferment and distinguish live findings.",
 "PER-03": "All three policy levels implemented/tested as rules; supported meaning and level-fit quality of real generated outputs not established.",
 "PER-07": "Automated evidence/schema/profile constraints exist; actual factual/negation/formula preservation requires real outputs and human review.",
 "PER-09": "No real paired personalisation findings or independent ratings. Tooling/templates are not research results or student-learning evidence.",
 "BE-02": "Actual replayable PostgreSQL migrations used by integration and clean install; explicit upgrade preservation of an old MCQ-row fixture is not established in cited evidence.",
 "BE-03": "Actual account provision/update/disable/reset/password/token-version/ownership checks; no model dependency.",
 "BE-04": "Actual profile optimistic revision/reset and immutable turn snapshot persistence tested; generation quality separate.",
 "BE-05": "Actual ordered persisted messages/session ownership/history/re-login/revisions tested; mock answers remain marked.",
 "BE-10": "Actual feedback create/update and administrator review controls exercised. Concurrent first-insert race requires targeted verification.",
 "BE-11": "Real experiment/study tables, migrations, shared jobs and independent budget/outcome exports exercised; gold stays evaluator-only.",
 "BE-12": "Actual frozen environment readiness/pending-input reasons implemented; official corpus/real embedding readiness not yet established.",
 "BE-13": "Error envelopes, trace IDs and settings bounds exist. Raw exception-message logging and regeneration default-budget gap were reported for repair/retest.",
 "BE-14": "Actual 54-path OpenAPI/64 schemas export and generated TypeScript drift checks passed; generic administrator dictionary payloads remain explicit.",
 "BE-15": "Actual PostgreSQL concurrency/cancellation/restart/failure tests passed; final changes need appropriate affected rerun, not an aggregate inferred pass.",
 "BE-16": "Actual clean Compose and disposable restore ran. Restore checks table counts and selected value hashes; full user/profile-value equality and final package exclusions require closure.",
 "BE-17": "CLI/rebuild/runbook implementation exists; full official corpus and final exact-build command replay still pending.",
 "FE-05": "Full prose/Markdown/math/copy/source controls tested; historical MCQ row browser rendering not exercised by an inserted old-record fixture.",
 "FE-10": "Actual admin upload/build/activation observed. Legacy rollback correctly rejected; fresh validated-baseline rollback browser retest remains pending.",
 "FE-12": "Real native zoom, width/boundary/state checks and clean browser smoke exist. Final combined rerun plus physical keyboard/orientation/native IME/human review remain open.",
 "QA-01": "Twelve authored multi-turn families and 40 real API/DB turns captured; semantic judgments remain null, labels private.",
 "QA-04": "Versioned qrel/source-review tooling exists; actual independent relevance/source-coverage judgments are unavailable.",
 "QA-07": "Both real shared benchmark paths exercised with mock answers; actual answer-model baselines are explicitly user-deferred. Official corpus/SciQ acquisition remains actionable local work.",
 "QA-09": "Controlled one-factor validation implemented; actual improvement study results not yet produced.",
 "QA-10": "Blind packages/import/analysis and all nine independent mocked teaching jobs tested; actual independent human ratings unavailable.",
 "QA-11": "Focused real DB/provider-simulation/ownership/input fault checks passed. Reported retry-budget/logging/race gaps and final affected reruns remain open.",
 "QA-12": "Actual API/DB/worker/browser journey evidence exists with authored/mock providers; final full browser rerun and official-corpus journey still pending.",
 "QA-13": "Phase timing/missingness software implemented; separately frozen full-workload actual corpus/concurrency/resource p50/p95 report not established.",
 "QA-14": "108/60 first-pass ledger reconciled with source IDs and evidence categories; this is not completion of final source/implementation/research/human audit.",
 "CHAT-01": "Original source diagrams identified and old MCQ-only restriction explicitly superseded; root current PRD/SPEC reconciliation still in progress.",
 "CHAT-08": "Latest-answer revision retention/deduplication tested with mock answers. Regeneration uses default RequestBudget in audited code; original configured limits need repair/retest.",
 "CHAT-11": "Chat-scope verifier confirms no choices/evaluator imports/mounts; actual legacy MCQ-row migration fixture and current-doc final consistency still open.",
 "CHAT-12": "English architecture/demo and no-SciQ clean chat evidence exist; complete official corpus, real embeddings and final 108/60 closure still pending.",
}

for task in tasks["tasks"]:
    identifier = task["task_id"]
    prefix = identifier.split("-")[0]
    code, tests_for_task, evidence = groups[prefix]
    status = task_status[identifier]
    detail = notes.get(identifier, {
        "RET": "Shared retrieval implementation and deterministic fixture checks pass; embedding providers are mock, with no official-corpus semantic-quality claim.",
        "GEN": "Strict generation/mode/prompt/repair behavior passed with mock, spy or simulated HTTP providers; no paid/live answer calls.",
        "PER": "Deterministic profile or independent study software tested; real response quality and actual human ratings are not inferred.",
        "BE": "Actual shared API/worker/PostgreSQL behavior exercised with authored sources and mock answer/embedding providers; scope is the cited software checks.",
        "FE": "Actual API/DB/worker browser and component checks recorded in audit-ui; answer model and source fixtures mock/authored. Final combined corpus-based rerun remains separate.",
        "QA": "Evaluator software checks pass on authored/private fixtures and mock providers; no actual dataset/model-quality measurement or human rating is claimed.",
        "CHAT": "Actual conversation data/context pipeline and authored multi-turn checks pass using mock answer/embedding providers; semantic real-model review separate.",
    }.get(prefix, "See scoped source/component audit and explicit remaining full-project requirements."))
    task.update(status=status, implementation_status=N if status == N else I,
        verification_status=status, actual_executor="Codex shared implementation; domain owner remains reporting metadata",
        actual_completed_at=None, evidence=list(evidence), evidence_paths=list(evidence),
        changed_files=list(code), reconciliation_note=detail, reconciled_at=NOW,
        completion_claim=False, evidence_scope="Specific observed component behavior; not blanket satisfaction of every task acceptance clause.",
        remaining_scope=detail, user_status_definition=STATUS[status])
    task["research_status"] = "WAITING_EXTERNAL" if identifier in {"QA-04", "QA-07", "QA-10"} else "NOT_ASSESSED"
    task["human_review_status"] = "WAITING_EXTERNAL"
    task["component_statuses"] = [
        {"component": "required task scope", "status": status, "detail": detail},
        {"component": "full official four-book corpus", "status": N, "detail": "Not established by current authored releases; official acquisition/processing is actionable work."},
    ] if prefix in {"DAT", "RET"} else [{"component": "observed implementation scope", "status": status, "detail": detail}]
    if prefix in {"GEN", "RET", "PER", "CHAT", "QA"}:
        task["component_statuses"].append({"component": "answer model", "status": M, "detail": "Only the explicitly cited deterministic/mock/simulated behavior passed; live answer calls user-deferred."})
    if identifier in {"RET-01", "RET-03", "RET-09", "DAT-08"}:
        task["component_statuses"].append({"component": "learned local embedding/reranker inference", "status": I, "detail": "Adapter exists; actual learned weights were not executed in current AI evidence."})
    task["implementation_trace"].update(concrete_code_paths=list(code), concrete_test_paths=list(tests_for_task),
        mapping_status="EVIDENCE_SCOPED_FIRST_PASS", limitation=detail)

check_status_groups = {
 R: "AC-02 AC-03 AC-04 AC-05 AC-06 AC-12 AC-14 AC-15 AC-26 AC-28 AC-31 AC-32 HC-01",
 I: "AC-11 AC-13 AC-20 AC-21 AC-24 AC-25 AC-33 AC-34 AC-35 AC-40 AC-44 AC-45 AC-48 HC-02",
 M: "AC-01 AC-07 AC-08 AC-09 AC-10 AC-16 AC-17 AC-18 AC-19 AC-22 AC-23 AC-27 AC-29 AC-30 AC-36 AC-37 AC-38 AC-39 AC-41 AC-42 AC-43 AC-46 AC-47 HC-03 HC-04 HC-05 HC-06 HC-07 HC-08 HC-09 HC-10 HC-11 HC-12",
}
check_status = {identifier: status for status, ids in check_status_groups.items() for identifier in ids.split()}
assert set(check_status) == check_ids
check_notes = {
 "AC-01": "Actual clean Compose and browser chat passed with mock model/embeddings and authored sources; not full official corpus.",
 "AC-02": "Actual fresh migrations and development seed used by isolated PostgreSQL and clean Compose. Nondevelopment seed is explicitly guarded.",
 "AC-03": "Actual invalid PDF/TXT type/path/size input tests and readiness isolation on PostgreSQL; authored assets.",
 "AC-04": "Real quarantine/blocking and quality/exclusion software tested; original missing pilot pages remain unresolved and are not silently included.",
 "AC-05": "Actual same-byte upload/reprocessing identity tests retain old answer/evidence; authored corpus.",
 "AC-06": "Actual numeric pgvector ranks and vector integrity validation; mock/model-double embeddings do not prove learned semantics.",
 "AC-11": "Simulated 429/5xx/auth/timeout bounds pass; reported regeneration default-budget gap needs repair/retest before whole scenario closure.",
 "AC-13": "Actual stale/cancelled job and teaching recovery tests pass. Full final worker-process interruption/restart evidence requires final affected verification.",
 "AC-20": "Disposable restore passed table counts, active pointer and selected content hashes. Full user/profile-value comparison and final distributable credential/content inspection remain open.",
 "AC-21": "108/60 IDs and acyclic artifact dependencies verified; final all-six-journey G8 browser regression remains pending.",
 "AC-23": "Strict public DTOs/frozen refs and code/Compose no-gold boundary verified. Clean product starts without evaluator; no evaluator labels in public application models.",
 "AC-24": "Tail retry PostgreSQL tests pass. Generic retry/regenerate mode eligibility for formal benchmark requests was reported for restriction/retest.",
 "AC-25": "Persistent calls/time and independent study budgets tested; regenerate currently creates default RequestBudget instead of preserving configured initial bounds in audited code.",
 "AC-26": "Backend PostgreSQL validated A/B/A activation and invalid-target preservation tests pass; browser legacy target rejection remains a separate FE-10 retest.",
 "AC-31": "Actual CLI account provision/disable/reset and browser password change/token revocation; no provider required.",
 "AC-32": "Actual saved feedback and admin review/reload observed; concurrent first-insert race not established by sequential success.",
 "AC-33": "Actual cleanup dry-run/apply and path/content/reference guards plus disposable restore exist. Combined stuck-job/operator-unavailable-evidence recovery walkthrough remains to be closed.",
 "AC-34": "Actual PDF/TXT and R0/R1 dispatch plus behaviorally distinct simulated adapters verified; one real configured answer adapter remains deferred.",
 "AC-35": "Cache/dimension/release boundary tests pass with authored model doubles; actual learned embedding replacement drill pending.",
 "AC-40": "Authored query correction/topic unit tests pass. Shared service new-topic example reuse gap reported; final affected runtime assertion must establish irrelevant citations are not reused.",
 "AC-44": "Actual browser controls/zoom/width/state evidence exists. Final combined run after latest UI changes and physical/native IME checks remain pending.",
 "AC-45": "Actual latest-revision and feedback retention/dedup tests pass with mock answers; regenerated configured budget issue remains open.",
 "AC-48": "Source diagrams/IDs/current mode contracts audited. No explicit old-MCQ-row migration preservation fixture is established; root canonical docs are being reconciled.",
 "HC-01": "Fresh immutable manifest audit and copied legacy verification recorded; Python 3.13.2, 39 tests and two mock rows. Original historical logs are not substituted.",
 "HC-02": "All generation assets preserved/ported and shared runtime evaluator tested. Clean app build exists; final relocated installed-package prompt/evaluator proof remains to be consolidated.",
 "HC-11": "Missing live settings fail explicitly in local tests; original past provider probe remains historical, not current connectivity.",
 "HC-12": "Original 20-item fixture, two mock rows and 40 failed diagnostics preserved by manifest audit; new evaluator freeze/resume retains all scheduled outcomes separately.",
}
for check in checks["checks"]:
    identifier = check["check_id"]
    linked = [t for t in tasks["tasks"] if t["task_id"] in check["task_ids"]]
    evidence = sorted({p for task in linked for p in task["evidence_paths"]})
    if identifier in {"AC-01", "AC-20", "AC-33", "AC-37", "HC-02"}:
        evidence += ["evidence/recovery/clean-chat.json", RESTORE]
    if identifier.startswith("HC-"):
        evidence += [LEGACY, "evidence/legacy/generation_verification_copy/results/handoff/verification.json"]
    detail = check_notes.get(identifier, "The linked component audits and saved test logs exercise this scenario's software boundary with authored data and mock/simulated answer providers. Read their explicit assertion scope; semantic quality, full official corpus and human review are not inferred.")
    check.update(status=check_status[identifier], actual=detail, evidence_paths=sorted(set(evidence)),
        reconciled_at=NOW, executed_at=None, completion_claim=False,
        component_statuses=[{"component": "cited scenario software scope", "status": check_status[identifier], "detail": detail}],
        verification_note="Existing saved runs are referenced, not newly executed by this documentation audit.")

for ledger in (tasks, checks):
    ledger.update(reconciled_at=NOW, status_definitions=STATUS, reconciliation_phase="source_and_evidence_first_pass",
        project_complete=False, source_architecture_audit=AUDIT,
        current_required_real_corpus=["Biology 2e", "Chemistry 2e", "Anatomy & Physiology 2e", "Concepts of Biology"],
        answer_generation_may_remain_mock=True, learned_embeddings_may_remain_mock=False,
        status_scope="Per-row component evidence and limitations; no row is labelled a blanket complete task.")

# Do not turn missing/typo paths into invented evidence.
paths = {p for task in tasks["tasks"] for p in task["evidence_paths"] + task["changed_files"]
         + task["implementation_trace"]["concrete_test_paths"]}
paths |= {p for check in checks["checks"] for p in check["evidence_paths"]}
missing = sorted(p for p in paths if not (ROOT / p).exists())
assert not missing, missing
assert len(tasks["tasks"]) == len(task_ids) == 108
assert len(checks["checks"]) == len(check_ids) == 60
for task in tasks["tasks"]:
    assert set(task["dependencies"]) <= task_ids
    assert set(task["acceptance_ids"]) <= check_ids
visiting, done = set(), set()
dependencies = {t["task_id"]: t["dependencies"] for t in tasks["tasks"]}
def visit(identifier):
    assert identifier not in visiting, identifier
    if identifier in done:
        return
    visiting.add(identifier)
    for dependency in dependencies[identifier]:
        visit(dependency)
    visiting.remove(identifier)
    done.add(identifier)
for identifier in task_ids:
    visit(identifier)

write_json(tasks_path, tasks)
write_json(checks_path, checks)
result = {"recorded_at": NOW, "audit_kind": "documentation_reconciliation_not_application_execution",
          "task_count": 108, "check_count": 60, "original_id_sets_preserved": True,
          "dependencies_acyclic": True, "cited_paths_checked": len(paths), "missing_paths": missing,
          "task_status_counts": dict(Counter(t["status"] for t in tasks["tasks"])),
          "check_status_counts": dict(Counter(t["status"] for t in checks["checks"])),
          "source_read_manifest": "evidence/source_audit/source_read_manifest.json",
          "no_application_tests_rerun_by_this_script": True,
          "required_real_corpus_complete": False, "learned_embedding_inference_verified": False}
write_json(OUTPUT / "ledger_reconciliation.json", result)
print(json.dumps(result, indent=2))
