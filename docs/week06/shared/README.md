# Week 6 handover record

This directory accompanies the eight module contributions. It records the 8 September 2026 existing-project baseline, package ownership, external inputs and newly executed isolated checks. The original project documents and code were copied unchanged. Historical execution dates and Codex/shared implementation attribution remain intact; accountability does not establish independent personal authorship.

## Read these records first

- `source-inventory.json`: the 433 original source/configuration/document/test files frozen before package verification, their unique owners and SHA-256 values. Task IDs indicate the original accountable module scope, not a claim that a single file proves every task complete.
- `remote-baseline.json` and `cleanup-actions.json`: observed main commit `9f6354db409241e681b7ed82a725c8279c135592`, four replacements and 24 exact obsolete-file deletions. Preserve history and PR1. Re-check new remote work before applying a cleanup list.
- `verification-summary.json`: actual isolated source merge, 188 Python unit tests, 25 frontend tests, locked frontend dependency installation and production build. These do not repeat the full PostgreSQL integration suite or verify a live answer provider.
- `runtime-ports.json`: current host database 15432, API 8000 and frontend 5173. The actual API database sockets confirm 15432. The unchanged example and Compose fallback still say 55432. Set the intended local values in a new clone; environment variables can override `.env`, and running processes need a deliberate restart to consume changes.
- `external-dependencies.json`: official books, immutable source identities, genuine E5 and R3 checkpoints, OCR assets, evaluation-data metadata and private backup recovery prerequisites. No PDFs, weights, database dumps or private SciQ rows are contained here. Raw download/restore is not performed by opening a source ZIP.
- `evidence-index.json`: original evidence-file hashes and paths. Historical source evidence omitted from the code packages must be obtained separately when reproducing an existing helper or screenshot. There are no fabricated personal images.

## Import and review

Xianshu first creates the proposed `week06/integration` from a freshly verified main baseline, removes only the listed obsolete files in an ordinary commit, then contributes the shared foundation through a personal branch and reviewed PR. The other module branches start from that published foundation. The recommended merge order is Xianshu Zhang, Zeping Liao, Hongle Yang, Chengzhou Liu, Pengyuan Xia, Sijin Lu, Baiqing Huang, Chong Zhang. Copy each `repo_files` directory's contents into the repository root. Do not upload ZIPs as a substitute, duplicate the whole application, modify whitespace to manufacture a change, rewrite shared files under multiple owners or claim validation-only commits as member work.

Each English report has its own `docs/week06/First_Last/Week06_Report_EN.docx` path. The identical report in the package root is for class. Chinese operation guides stay outside `repo_files`. The overall Chinese report is delivered only in the top-level handover folder. These are module contributions to one system, not eight standalone applications. Core imports become runnable only after their dependencies have been assembled.

The isolated Git validation used `core.autocrlf=false` to preserve the exact mixed source-file bytes. To reproduce that hash check, each member can use GitHub Desktop's Repository > Open in Terminal from their NEW clone and run `git config --local core.autocrlf false` before importing files. This setting applies only to that clone; do not change global settings or the protected original project. Retain the packaged `.gitattributes` for the authored text fixture. Check byte hashes before committing; do not reformat source files to make a commit appear nonempty.

## Current scientific boundary

The active v5 corpus `4f11bd70-a486-4d16-b216-78cfe499530a` contains 10,594 genuine 384-dimensional E5 vectors from the four complete official books. The answering model remains explicitly mock. The fixed-window comparison already has 11,461 genuine vectors and is not activated. R0-R3 technical runs, existing backups and software evaluation frameworks are already implemented; live answer quality, compatible independent qrels, teaching ratings and physical-device acceptance remain conditional work.

Keep the database and matching source storage together when restoring existing answers and citations. A fresh rebuild creates new IDs and does not recreate historical identity. The retained 09:33:08 UTC backup excludes later test sessions. Existing source/processing helpers may require historical catalogs, review decisions or registries; the external inventory identifies these dependencies. The two files under `evaluation/private_fixture` are explicitly authored public software fixtures, including four SciQ-style example rows, not real private SciQ labels.

## Official GitHub Desktop references

[Managing branches](https://docs.github.com/en/desktop/making-changes-in-a-branch/managing-branches-in-github-desktop) explains choosing a base branch. [Creating a pull request](https://docs.github.com/en/desktop/working-with-your-remote-repository-on-github-or-github-enterprise/creating-an-issue-or-pull-request-from-github-desktop?platform=windows) explains publishing and previewing a PR. Always inspect the actual base `week06/integration`, compare branch and changed paths. No remote branch was created or pushed during this handover task.
