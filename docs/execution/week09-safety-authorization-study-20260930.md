# Week 9 isolated authorization study

This study froze 500 object-authorization GET probes against the exact installed V11 project archive, SHA-256 `938f59ae246c3e9dd102603417664aaa97a56244a31ea86ea7ea0b7c34737fcb`. The private case freeze, SHA-256 `7521667999aa070dde32f0bfa07cd8d2b46e1d238347b367d581d7d0cc6d37bf`, precedes the runtime outcome records. The evaluator source SHA-256 is `f7b59c7f2d70680d12d40dc6625224ce169d2e5e32b2ec15d6f8214822771805`. The [public numeric receipt](../../evidence/week09-continuation/20260930/safety-fixed-authorization-v1.json), SHA-256 `d11fb64a6468134f77c811fa3726803357fc4ce0f3d1eed6872d0a3321b86012`, omits credentials, bearer tokens, private resource IDs and response bodies. The complete per-request status and body-hash record remains in the isolated private study directory.

Two temporary student accounts were created in the isolated V11 installation. The owner created 25 sets of sessions, goals and source-linked notes using the released Biology 2e textbook. The second student and an anonymous client each attempted to read owner objects or administrator endpoints. Every attack GET was paired with an authorized owner's or administrator's GET to the same path. Ten endpoint surfaces formed separate development, pilot and reserved groups: 100, 100 and 300 requests respectively. This split isolates endpoint types, although resource IDs and the two study principals recur across groups; 500 requests are **not 500 independent people or knowledge concepts**. No mutating attack or paid model call was made.

| Observed measure | Result |
| --- | ---: |
| Scheduled / executed fixed authorization probes | 500 / 500 |
| Unauthorized 2xx responses | 0 / 500 |
| Matched legitimate tasks completed | 500 / 500 |
| Expected denial codes observed | 500 / 500 |
| Attack responses carrying `no-store`, `nosniff` and restrictive CSP | 500 / 500 |
| Private owner markers appearing in attack responses | 0 / 500 |
| Deactivated study accounts whose previous token was blocked | 2 / 2 |
| Provider calls / estimated provider cost | 0 / USD 0 |

The 250 anonymous attempts all returned HTTP 401. Of the 250 authenticated other-student attempts, 150 owner-object attempts returned HTTP 404 and 100 administrator attempts returned HTTP 403. Each authorized paired request returned HTTP 200; cases carrying a private owner marker or object ID also required that marker in the authorized response. The 10 surfaces included session detail, messages, learning tasks and memory notices; goal detail and goal-filtered notes; administrator visual detail, original page and page-filtered list; and administrator user listing. Administrator user-list requests are repeated consistency probes and should not be interpreted as independent exploit classes.

The test used the isolated stage in `MODEL_MODE=mock`. It establishes only the measured object-read and role-read boundaries. Source or memory prompt injection, forged citations, answer-key coaxing, malicious uploads, resource exhaustion, login rate limits, recovery and bounded adaptive attacks were **not evaluated by these 500 requests**. An actual DeepSeek answer model and independently labelled adversarial content are required before reporting model-mediated attack success or safe task completion. The existing adaptive scheduler remains unexecuted. Human safety ratings remain zero.

Post-run read-only database checks found four official documents, the active release `4f11bd70-a486-4d16-b216-78cfe499530a` with 10,594 chunks/vectors, 5,543 visual candidates, zero visual reviews and zero published practice items. Both study accounts were deactivated. The isolated study left the original PDFs, released vectors, historical answers and main database untouched.

The executable runner is [safety_formal.py](../../evaluation/week09_continuation/safety_formal.py). Four focused schedule and denominator tests passed; Ruff check and format check passed. A separate implementation gap remains: the document upload router currently calls `file.read(max_upload_bytes + 1)` with a configured maximum of 512 MiB, so the size cap is bounded but upload processing is not streaming. Streaming, parser resource isolation and malformed-file stress testing remain required before a broader file-safety result can be claimed.
