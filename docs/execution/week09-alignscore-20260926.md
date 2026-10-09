# Optional AlignScore CPU feasibility

The offline run completed 64 observations using the official AlignScore-base checkpoint. Seven of eight authored contrast pairs ranked the supported claim above the contrasting claim. One calculation pair ranked the incorrect numerical result higher. Several supported formula, unit-conversion and conditional claims received low absolute scores. The project keeps AlignScore outside the online answering path.

## Research basis and fixed assets

AlignScore measures consistency between supplied context and a claim. Its recommended `nli_sp` mode combines a three-way alignment head with chunk/sentence aggregation. The official base model uses RoBERTa-base. This experiment evaluates a possible local precheck on a small diagnostic set; it does not reproduce the paper's benchmarks. [Official paper](https://aclanthology.org/2023.acl-long.634/), [author code and usage](https://github.com/yuh-zha/AlignScore).

| Asset | Frozen identity |
|---|---|
| AlignScore code | `a0936d5afee642a46b22f6c02a163478447aa493` |
| Checkpoint repository revision | `8509e78d25bb914939fc585c626500c9b2944249` |
| AlignScore-base checkpoint | 1,966,965,771 bytes; SHA256 `6aedb637f0596ab29baef91e94466a57f032e02feea654978518919fe0981607` |
| RoBERTa revision | `e2da8e2f811d1448a5b465c236feacd80ffbac7b` |
| Python | Official side-by-side NuGet Python 3.10.11 |
| PyTorch | `1.13.1+cpu`; CUDA unavailable |
| Transformers / Lightning | `4.25.1` / `1.9.5` |
| spaCy / NLTK / NumPy | `3.7.5` / `3.8.1` / `1.26.4` |
| Inference | CPU, two threads, batch size one, `nli_sp` |

The project Python 3.13 environment had no compatible wheel for the upstream Torch <2 requirement. An independent Python 3.10 environment resolved this constraint. An initial older-pip dependency metadata failure was resolved inside that environment. `pip check` passed; installed AlignScore Python files matched the downloaded official commit. The original application environment remained intact.

Official checkpoint and backbone hashes were checked before execution. The checkpoint hash remained identical afterward. Lightning converted the loaded checkpoint metadata in memory; the checkpoint file was unchanged. Assets and the complete research environment are retained at `E:/5703/week09_generation_20260926/alignscore-probe/`, with download receipts and `requirements-isolated.lock`. These large optional research assets are separate from the runnable application dependencies.

## Fixed contrast experiment

Eight authored pairs cover two negation, two condition, two formula and two unit cases. Each has a supporting statement and a contrast. Cases and the expected relation were frozen before model scoring. The first pass ran 16 claims; three subsequent passes ran 48 warm observations, alternating within-pair order. All 64 completed. The premises are isolated diagnostic fixtures and were never added to the textbook corpus.

| Measurement | Observed result |
|---|---:|
| Model initialization | 3.494 s |
| First-pass median / p95 | 1.517 / 1.552 s per context–claim pair |
| Warm median / p95 | 1.520 / 1.558 s per context–claim pair |
| Execution failures | 0 / 64 |
| Pair ordering matching authored expectation | 7 / 8 |
| Independent human ratings | 0 |
| Online activation | Disabled |

Initialization timing starts after imports and asset-hash checks. Operating-system file caches were not cleared. Other application/provider work ran on the same host, so these are local feasibility observations. Scoring multiple claims would add repeated work to an interactive request.

The formula ranking failure and low supported scores require further investigation. A production cutoff has not been selected. Next work is independent labeling of textbook-derived claims, broader conditions and numerical reasoning, and a comparison against existing checking cost before any online integration decision.

## Evidence and tools

Public aggregate evidence: `evidence/week09-generation/20260926/alignscore-summary.json`.

Protected frozen inputs, per-observation scores, timing and exact executed runner: `evidence/week09-generation/20260926/private/alignscore-cpu-01/`. The exact executed runner is `frozen-runner.py`; the current source differs only by a typing annotation for the optional dependency.

`scripts/verify/alignscore_cpu.py` accepts a protected cases file, isolated environment root and new output directory. Run it with the isolated Python interpreter, from the directory containing the pinned `roberta-base` assets, with `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` and `NLTK_DATA` pointing to the recorded local splitter data. It verifies hashes, official installed source bytes, CPU-only execution and fixed thread policy before scoring.
