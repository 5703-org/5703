# Week 9 real free-text assessment trial

On 3 October 2026, the current candidate completed sixteen real DeepSeek assessments and six deterministic grading controls. The trial retained all twenty-two terminal records. Ten model returns passed the production assessment contract; six entered pending review because the returned evidence coordinates were invalid. All sixteen provider replies completed with HTTP 200 and finish reason `stop`, using one call per text response.

## Inputs and method

The fixed development population contains eight source-correct text responses, eight contradictory text responses, four choice controls and two numeric controls. Each response keeps its original finite official OpenStax source locator and scoring points. A read-only query verified the twenty-two original source units and the saved real checker configuration. The generator used `deepseek-flash`; responses were preserved before comparison with frozen development AI labels. Choice and numeric controls used their existing deterministic rules.

This execution exercised production preparation and validation with unpersisted item, attempt and progress objects. Separate earlier database/API controls used scripted assessments. Real submission, persistence and learning progression remain a separate acceptance journey.

## Actual results

| Population | Correct | Incorrect | Partial | Pending review |
|---|---:|---:|---:|---:|
| Eight source-correct text controls | 6 | 0 | 0 | 2 |
| Eight contradictory text controls | 0 | 2 | 2 | 4 |
| Six deterministic controls | 6 | 0 | 0 | 0 |

Four pending records returned response-span endpoints beyond the supplied response. Two returned zero-length source and response spans. Pending results retain the learner submission and pause progress under the implemented contract. Both partial assessments identified a source contradiction. Independent human review will determine the appropriate final outcome and whether the cited fragments support the assessment.

One accepted response span ends at the words “organelles are”, omitting “absent.” The trial therefore exposes a remaining semantic-support issue alongside the coordinate failures. Bounded coordinates and a valid output structure are measured separately from correct evidence support.

Exact product-label agreement with the frozen development AI labels was 8/16 for model records and 14/22 including deterministic controls. Raw unvalidated model labels agreed in 14/16 cases. The accepted-label measure includes pending results; the raw measure retains rejected output for diagnosis. Team human ratings are zero. These are exposed development cases, with source-disjoint scientific evaluation still pending.

## Timing and usage

The trial lasted 103.017 seconds, including local guards, source checks and record persistence. Provider latency totaled 19.240 seconds: median 1.166 seconds, minimum 0.984 and maximum 1.818 seconds. These figures describe this direct trial rather than installed end-to-end latency.

Usage was 22,625 input tokens and 2,626 output tokens, totaling 25,251 tokens. Recorded input cache counts were 9,728 hits and 12,897 misses. Provider cost fields were null; invoice cost remains unavailable. All sixteen calls, raw outputs and failures are retained privately. Retry calls, product-row writes and human labels were zero.

## Follow-up

Calibrate evidence-span output and semantic support on separate development cases, complete the installed submission-to-progress journey, and have group members independently rate the blinded materials. Final experiment reporting will preserve pending outcomes and report automatic and human results separately.

[Deidentified execution record](../../evidence/week09-continuation/20261003/real-practice-assessment-63.json), [current assessment contract](week09-practice-model-assessment-20261003.md), [current source and regression](week09-current880-native-v7-and-restoration-20261003.md).
