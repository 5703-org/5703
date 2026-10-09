# Week 8 Work Report

Pengyuan Xia | Learning memory and teaching policy | 2026-09-22

## Week 8 contribution

Upgrade opt-in learning memory to typed, versioned learner state. Current instructions and explicit subject preferences control presentation without becoming textbook facts, access rights or unsupported mastery claims.

Original task allocation: PER-01, PER-02, PER-03, PER-04, PER-05, PER-06, PER-07, PER-08, PER-09, CHAT-07.

## Completed implementation

Typed identities distinguish durable preferences, goals, self-reported observations and assessment-supported records. Provenance, source ordering and deletion epochs prevent older asynchronous work from replacing a newer correction or restoring erased content.

A deterministic reader selects relevant state and applies current-turn corrections before asynchronous extraction finishes. Precedence is current instruction, applicable explicit subject preference, global saved setting and other relevant defaults. Temporary requests stay bounded to their turn.

Observation gates require an appropriate scoring or attestation basis. Asking a question does not prove difficulty or mastery. New authored memory trajectories compare extraction, updates, summary behavior and unconditioned versus query-conditioned selection separately.

## Interfaces and operation

Zeping supplies transactional ownership and erasure fences; Sijin uses the frozen relevant context with safe prompt persistence; Baiqing exposes source/version/category controls; Chong separates selection correctness from final-answer behavior.

- Opt in and inspect an entry category, scope, provenance and summary.

- Correct a preference and inspect the current snapshot before background persistence.

- Disable, expire or delete entries and verify delayed-work behavior while preserving the original conversation.

## Verification and findings

Memory V2 represents durable preferences, goals, course context, self-reports and individual assessment outcomes with typed keys, scope, provenance and revision. The selected state follows the confirmed precedence: current instruction, relevant subject preference, global profile setting, global memory preference and evidence-gated observations.

The focused checkpoint passed 45 checks covering selection, immediate correction, delayed older jobs, repeated erasure, assessment provenance and the preserved M2 path. The current full gate includes these behaviours within its 828 Python tests. The M3 and M4 comparison shares one writer and identical state; only the reader selection differs.

Actual browser preview applied a biology preference to an ATP question, then showed that a current instruction and profile-off choice suppress the older state as required. Source inspection, typed edit, global disable and deletion used real endpoints in a separate database. The original owned source message remained available after deletion.

The state payload is bounded by the configured counter and a 768-token ceiling. Current recognised corrections affect the snapshot before background extraction finishes. Expiry, settings epochs and erasure fences prevent stale selected values from reappearing. The summary is derived from current eligible entries, while the preview explains the question-specific selection.

The completed numerical report retains all planned outcomes for the assigned studies, including failures and human-dependent oracle cases. Domain accountability does not imply that the member personally executed the recorded automated work.

T2 minus T1: -16.67 percentage points (95% paired cluster interval -36.11 to +2.78); negative observed difference. Conservative successes 19/36 versus 25/36; 12 paired families/trajectories. M4 minus M3: -2.78 percentage points (95% paired cluster interval -13.89 to +8.33); negative observed difference. Conservative successes 20/36 versus 21/36; 12 paired families/trajectories.

| Study | Recorded | Planned |
| --- | --- | --- |
| Study T Teaching Control | 180 | 180 |
| Study M Learning Memory | 180 | 180 |

## Current limits

The memory study evaluates actual answer behavior using authored trajectories. Assessment observations apply to their recorded task. Student learning outcomes and broader mastery require a separate educational study.

Automatic state equality and extraction checks do not measure whether an answer uses memory helpfully. The separate output study and independent review address that question. A recorded assessment remains scoped to its task; educational progress and broader mastery require a different longitudinal design.

## Week 9 goals

- Analyze stale reuse, scoped exceptions and instruction conflicts in the frozen trajectories.

- Review observation provenance with independent reviewers.

- Register any participant learning-quality study separately.

## Code and evidence

Module paths: personalisation/memory_v2.py; personalisation/memory_extraction.py; backend/app/modules/learning_state/memory_v2.py; evaluation/memory_v2/memory_study.py; evaluation/memory_v2/memory_gates.py.

Codex performed the implementation, automated checks and recorded local browser verification through the shared project workflow. The eight reports follow the original accountable domains; member submissions and independent human reviews retain their own execution records.

Memory implementation checkpoint. 45 focused Python checks and the dated component/build/browser checkpoint; the recorded pre-formal status belongs to this earlier checkpoint.

evidence/week08-memory-v2/20260921/memory/implementation-checkpoint.json

SHA256 879a6ed51d67605fd9fad3a11388e689dad6198f5a6390e9ae49c09b6e9f0d43

Actual Memory V2 browser workflow. Owned authored data in a separate migrated database; preview, source, edit, disable and deletion through actual endpoints at 1440 and 390 pixels; zero provider calls.

evidence/week08-memory-v2/20260921/memory/browser-final/verification.json

SHA256 aff7e1263b4d2bd6fbbab2a69cba2fbb9c372fa80ea8862965875139a1495d8c

Memory visual and runtime review. Five screenshots inspected individually, no original-database mutations, and owned temporary services stopped.

evidence/week08-memory-v2/20260921/memory/browser-final/visual-and-runtime-review.json

SHA256 e93263266e6f28f922583ef84c7c46b44b1a164f4cc50829f9a1f01e582d6a87

Final integrated Python results. 828 passing unit and isolated PostgreSQL checks; zero failures, errors or skips

evidence/week08-memory-v2/20260921/software-gate-release-final-20260922/pytest.xml

SHA256 4931f56a94e316368d999f884dc8b8d4b6834c464985b869a410b0464af4d015

Registered automatic study results. 552 scheduled requests across 18 arms; all generation and offline judgment outcomes retained; independent human ratings zero

evidence/week08-memory-v2/20260921/formal/public-results.json

SHA256 b470c9c5df020d3dd7dae9625fdfabc82afdf60569f33a3d62c84a5ea340e7f6

Actual blank blinded review export. Two randomized 552-row reviewer slots; zero completed or imported ratings

evidence/week08-memory-v2/20260921/formal/review-export-verification.json

SHA256 9f9f675f3f00a30b7e64745be7d9ef0f2d2786295fb2cbdbc5a6a43041a75b5a
