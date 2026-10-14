# Review results

This reusable preparation contains 12 public synthetic cases, five source fixtures, deterministic proxy rubrics and a staged provider matrix. Real provider quality has not been measured. The underlying records preserve method, authorship, reviewer execution and unknown usage/cost provenance.

The initial live scope is one authenticated catalogue resolution and a six-call DeepSeek smoke batch, after safe configuration binding. A 24-request DeepSeek pilot is a separate decision. Later route, model and reviewer expansions are separately activated; the full 3,404-transport ceiling is not scheduled or launched by these scripts. All eight preset routes and the explicit local protocol remain in the planned route coverage. Endpoint compatibility and verified underlying-model comparisons have separate records.

`build_matrix.py` reads the explicit source root, source default policy, current preset definitions and public source/prompt files. It freezes a new run directory using `manifest_template.json`, `fixtures.json`, `cases.json` and `rubrics.json`. Exact live model/configuration/tokenizer bindings remain pending. Existing output directories are rejected, preserving previous source states and final receipts.

`validate_dryrun.py` imports only the explicitly supplied native source root, rejects network/subprocess/external-write attempts and runs authored mock checks. It validates 12 cases, 24 V21/V7 and V22/V8 requests, nine protocol wire shapes and six mock compatibility probes. It preserves the original refusal and missing semantic-checker failure. Passing validation does not imply that every intended behavior passes the lexical proxy. Semantic source support, presentation quality and protected-result disclosure need separately executed review.

Outputs stay in a new run directory outside the captured source root; both scripts reject nested output paths. Default capture is compact; `--capture-requests` explicitly includes full public requests and native mock messages. Historical snapshots, generated reports and full request captures are not production code dependencies. The source root must already contain both reviewed producer pairs and their compatible consumers. The scripts do not use credentials, databases or live transports.

Validation accepts exactly six pinned input filenames and canonical relative source/prompt paths with SHA256 hashes. It rejects duplicate pins, links, junctions and reparse paths before reading their targets. The complete bounded source/prompt inventory must match the freeze, including added modules that could change import resolution. Imported native module origins must be pinned. Use an explicit combined source root; historical override snapshots are excluded. The executing validator and initially loaded manifest remain pinned before results are saved.

The reachable import root is the supplied source root. Its immediate Python modules and package directory names are frozen before imports, alongside package initializers and all Python files in the bounded native trees. Direct source-less or binary modules/packages are rejected; existing `__pycache__` contents remain untouched and unused through a fresh owned bytecode prefix with bytecode writing disabled. The backend directory is not added to the import path.

Dependencies in the active interpreter's `sysconfig` `purelib` and `platlib` directories are excluded from native source pins, including an interpreter installed inside the repository. These directories must remain strictly within active `sys.prefix`; file and reparse checks still apply. The validation receipt records the active interpreter prefix and dependency roots separately from native module origins.

Execute the validator copy that the builder writes into the frozen run directory outside the source tree. That executing copy is pinned as an input artifact; the native-module guard applies to modules from the reviewed source tree.

```powershell
$matrixInputs = "<matrix-input-folder>"
$matrixSource = "<reviewed-source-root>"
$matrixRun = "<new-run-folder-outside-source>"
python -B (Join-Path $matrixInputs "build_matrix.py") --source-root $matrixSource --inputs-dir $matrixInputs --output-dir $matrixRun
python -B (Join-Path $matrixRun "validate_dryrun.py") --source-root $matrixSource --run-dir $matrixRun
```

Source changes require a new build and receipt. Live execution additionally requires frozen account-supported model IDs, capabilities, configurations, token counters, module/dependency environment and an executor that reserves global budgets before transport. Absolute stage/global wall deadlines preserve uncertain receipts and prohibit automatic replay. No live executor is supplied here.
