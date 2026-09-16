# Chat-first scope migration

Effective source: v5 Sections 2, 6–8, 17–21 and the responsive UI refinement. Preserve original archives and historical MCQ records. This migration changes active behaviour without rewriting what the historical prototypes accomplished.

| Previous assumption or source | Effective replacement | Affected artifacts/checks |
| --- | --- | --- |
| Older SciQ input diagram and four-option form define the product | `/chat` takes one ordinary natural-language message; SciQ is an offline evaluation branch | Requirements, architecture sequence, API/client and FE-03/08, CHAT-01/05/06; AC-36/37/48 |
| All generation requires options or returns an A–D answer | ChatResponseV1 returns full prose, compact answer and conversational type; only MCQResponseV1 has candidate selection | GEN-01/05, contracts, renderer; HC-04/05 |
| Conversation history is display-only or excluded everywhere | Interactive requests use owned completed messages, active revisions, bounded summary and immutable context snapshot | CHAT-02/03/04, GEN-08, BE-05; AC-38/42/43 |
| Individualisation is a later obligatory second call | Current explicit profile and temporary wording enter one main answer generation; independent matched C0/C1/C2 experiments remain separate | GEN-09, PER-02/05/06, CHAT-07; AC-29/30 |
| Disabling profile means baseline mode with no history | `use_profile=false` removes policy only; history remains selected under interactive mode | Request policy, prompt builder, UI toggle; AC-30, HC-09 |
| Nonempty evidence/fixture evidence_status proves sufficient support | No runtime oracle status. Model examines actual current evidence; clear factual empty-evidence requests refuse, greetings and missing-topic clarification remain valid | GEN-03/04; HC-03/09 |
| Mock OPTION_A test hook in live prompts | Versioned unbiased prompts; mock behaviour stays in a labelled local adapter | GEN-02/03; HC-03 |
| Lenient fenced JSON, duplicate keys, normalized selected answer text or numeric refusal confidence | One strict object; reject invalid keys/nonfinite values/types/extras. Refusal confidence is null. MCQ answer_text equals the selected option exactly | GEN-01/05; HC-05/06 |
| Smoke run_case owns format repair | Shared GenerationService and persisted worker attempts own one finite global budget and one repair | GEN-06, BE-07; HC-08/10 |
| Old turn regeneration can overwrite transcript | Latest completed answer only, no later user turn/active job. New request uses pre-answer snapshot; successful replacement atomically changes active revision | CHAT-08, BE-15; AC-45 |
| Historical citations may be reconstructed from latest corpus | Retain exact original evidence text/provenance; new availability may hide it explicitly, never substitute a similar new passage | GEN-07, DAT-10; AC-14/41 |
| Week buckets or named domain owners restrict coding | One artifact-dependent 108-task queue. Weeks and owners are exported accountability views | INT-10, QA-14; AC-21 |

## Three-mode contract migration

`interactive_chat` accepts content/use_profile in an owned session and persists a user message, context/profile snapshots, job and typed prose answer. Server-owned context cannot be replaced by caller-supplied history. `benchmark_openqa` accepts a stem and trusted frozen run/item identity, forces empty dialogue/profile context and returns ChatResponseV1 through the same free-form components. `benchmark_mcq` accepts exactly A–D normalized-unique candidates without their gold label, and returns MCQResponseV1. E0/E1 are evaluation conditions inside these explicit protocols.

New learner navigation is `/login` → `/chat` or `/chat/:sessionId`; `/profile` and admin corpus/experiment pages remain. Old `/sessions` URLs may redirect. Error contracts retain 401/403/404, 409 conflict, 410 unavailable evidence, 413/415/422 input errors and 503/504 dependency failures.

Migration must preserve users, session identities, source versions, existing MCQ payloads and citation links. Historical MCQ records remain explicitly typed and rendered by the legacy mode. New schema defaults cannot turn old A–D values into prose or fabricate conversation messages. A fixture upgrade on PostgreSQL and typed-renderer test are required before AC-48 passes.

## Reopened task families

INT-02/03/06/07/08/10, GEN-01–11, BE-02/05/07/08/09/11/12/14/15, PER-02–06, RET-03–06, FE-03–08/10–12 and QA-01–14 require reconciliation wherever an old assumption applied. CHAT-01–12 provide explicit additional conversation acceptance. Existing working code can satisfy unchanged parts after a current test; old logs remain historical rather than marking the new task complete.

The G4 product milestone includes context, profiles and recovery before scientific baseline or blind-rating conclusions. New chat requires no SciQ asset or evaluator mount. The separate product/evaluation sequences belong in `architecture.md`; this record is the authority for which old mainline assumptions must be removed.
