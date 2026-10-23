# Personalisation: offline verification evidence

Pengyuan Xia | CS30-1 | Prepared for the 23 October 2026 update

This folder documents verification of **existing** personalisation code. It does not introduce a new product feature or claim that existing tests were newly written this week. The verification and publication preparation were assisted by Codex.

## Start here for the tutorial

1. Open the [compiler result](evidence/compiler_evidence.json): `summary` shows the nine level/style combinations and two positive controls; `known_limitations` records the two negative-instruction failures.
2. Open the [handover result](evidence/handover_validation_receipt.json): `summary`, `tests` and `negative_probes` show the four original test-function outcomes, mock-call count and unresolved failures.
3. Explain how the checks ran using [verify_compiler.py](scripts/verify_compiler.py) and [verify_handover.py](scripts/verify_handover.py).
4. Show the [original test file](../../prototypes/personalisation_week10/tests/unit/test_profiles.py), then [compiler.py](../../prototypes/personalisation_week10/personalisation/compiler.py) at `turn_override` to explain the keyword-negation limitation.

Suggested summary: "I verified the existing profile rules and comparison workflow, documented the passing checks, and reproduced two unresolved negative-instruction failures. These are offline software checks, not evidence of improved student learning."

## Recorded results: keep the units separate

| Check | Recorded outcome | What it means |
|---|---|---|
| Source comparison | 13 assigned module files match the 19 October complete snapshot | Confirms source identity, not functional correctness |
| Handover integrity | 14/14 source and test files match the handover index hashes and sizes | Confirms the supplied files are intact |
| Profile matrix | 9/9 level/style combinations pass; each is compiled twice | Checks fixed rules, normalization, revision and repeatability |
| Positive controls | 2/2 pass: request more detail; profile off without a current request | Checks two specific behaviours, not general language understanding |
| Existing tests | 4/4 test functions pass when called directly | Selected assertions pass; this is not a full pytest run |
| Mock study | 9 simulated calls within one of those four tests | Three levels x C0/C1/C2; not nine students or nine independent studies |
| Negative instructions | 2/2 examples remain incorrectly classified | These are failures, not successful adaptations |
| External calls | 0 live model calls; handover run records 0 network attempts | No API credentials or paid provider calls are needed for these checks |

Do not add these counts into a single overall pass rate. The two probes recur across both records; they are the **same two examples**, not four distinct bugs.

### The unresolved failures

| Input | Expected | Observed |
|---|---|---|
| `Do not simplify; keep advanced terminology.` | Do not create the negated simplification override | Beginner/Concise override |
| `Please do not give more detail.` | Do not create the negated detail override | Detailed override |

The keyword matcher recognizes `simplify` or `more detail` without accounting for the preceding negation. No fix is included in this publication.

## Existing code to inspect

| File | Relevant functions |
|---|---|
| [test_profiles.py](../../prototypes/personalisation_week10/tests/unit/test_profiles.py) | Original four tests: compiler/validation, temporary override, fixed comparison inputs and missing ratings |
| [compiler.py](../../prototypes/personalisation_week10/personalisation/compiler.py) | `LEVEL_RULES`, `STYLE_RULES`, `turn_override`, `compile_profile` |
| [study.py](../../prototypes/personalisation_week10/personalisation/study.py) | `TeachingStudyService.generate` and `matrix` |
| [rubric.py](../../prototypes/personalisation_week10/personalisation/rubric.py) | `rating_template`, `validate_rating` |

These links point to the existing Week 10 snapshot on this branch. The four files were checked against the handover files and are byte-identical. Their presence in a responsibility partition is not proof of sole personal authorship. In particular, `test_profiles.py` already existed in the 13 October package; its absence from the narrower 19 October package does not make it a new test.

The archived 14-file integrity check refers to the original handover files, not to Git's stored bytes. When comparing those files with this branch, 13 are byte-identical; `memory_v3.py` differs only in CRLF versus LF line endings. All 14 match after line-ending normalization. The original raw-byte hashes in the receipts have not been changed.

## Evidence provenance and publication changes

- Compiler record: original run at **2026-10-19T05:30:25.341486+00:00**.
- Handover record: original run at **2026-10-23T03:25:25.680972+00:00**.
- The two JSON files are **path-redacted copies of those historical records**, not newly generated results. Their timestamps, result values, hashes, inputs, observed outputs and limitations remain unchanged.
- Exactly 36 local absolute path strings were replaced with logical aliases. See [PUBLICATION.json](PUBLICATION.json) for the affected fields and original-file SHA-256 hashes. Local originals remain unchanged.
- The two published scripts are CLI adaptations of the preparation scripts: paths are now explicit parameters, and existing output files cannot be overwritten. The checks themselves are retained. These adapted scripts did not produce the historical records; the original preparation scripts did.
- `<OWNER_20261019>` means the earlier owner snapshot; `<COMPLETE_20261019>` means the earlier complete application; `<HANDOVER_20261023>` means the supplied handover module. These aliases are provenance labels, not downloadable folders in this repository.

## Re-running: external package snapshots are required

**This folder is not a standalone runnable application.** A repository checkout alone does not include all original manifests and the exact shared dependency snapshot. Obtain the original course project packages through the team's approved sharing channel:

1. The 19 October owner `learning-assistant` directory, including `RELEASE_MANIFEST.json`.
2. The 19 October complete `learning-assistant` directory, including `PACKAGE_MANIFEST.json` and its supporting modules.
3. The handover root containing `MODULE-INDEX.json` and `learning-assistant/`.
4. The original `CS30-1_Current_20261019_Complete_Application.zip`.

Use the compatible Python environment for that complete application. Do not substitute another dependency release silently. First inspect the command-line options:

```powershell
python verification/pengyuan_20261023/scripts/verify_compiler.py --help
python verification/pengyuan_20261023/scripts/verify_handover.py --help
```

From the repository root, replace each `D:/inputs/...` example with your actual extracted input path:

```powershell
python verification/pengyuan_20261023/scripts/verify_compiler.py --owner "D:/inputs/owner-20261019/learning-assistant" --complete "D:/inputs/complete-20261019/learning-assistant" --output "verification/pengyuan_20261023/reruns/compiler_evidence.json"

python verification/pengyuan_20261023/scripts/verify_handover.py --source "D:/inputs/handover" --old-full "D:/inputs/complete-20261019/learning-assistant" --old-owner "D:/inputs/owner-20261019/learning-assistant" --old-zip "D:/inputs/CS30-1_Current_20261019_Complete_Application.zip" --output "verification/pengyuan_20261023/reruns/handover_validation_receipt.json"
```

Network connections are blocked in the scripts. The handover harness additionally permits only the built-in mock adapter, imports the handover module first, and supplies missing contracts/generation modules from the explicitly older 19 October snapshot. It directly calls four test functions; it does **not** run repository `conftest` or the full pytest suite.

Choose a new output filename for each run. `reruns/` is ignored by Git. Fresh outputs contain local runtime/input paths and possibly traceback paths if a test fails; review/redact those before sharing. Do not overwrite or relabel the archived evidence. A zero script exit code is not an all-behaviours-pass verdict: inspect the separate test results and negative-probe outcomes.

## Limits and next work

The matching 22 October complete application was not available for these recorded checks. No latest-release integration acceptance, database persistence check, end-to-end UI test, general V5 memory-selection regression, independent human rating or learning-gain study was performed. A guardrail sentence appearing in a policy does not establish that a real model follows it.

Next: repair negation handling, add regression cases, rerun against the matching complete application, and obtain independent answer-quality ratings. Product source files were not modified by this verification publication.

中文提示：先展示两份结果，再解释两个脚本怎么测，最后用原有测试和 `turn_override` 说明检查对象与问题。这里是“已有功能的验证记录”，不是“本周新增功能”，也不能说全部测试或系统已经通过。
