# Source17 restricted full-unit result

The current public Source17 unit snapshot finished with **FAIL_RETAINED**. It does not certify a passing full suite or the later Source18 change.

Actual pytest summary: **95 failed, 3710 passed, 27 skipped, 47 warnings, 29 errors, 127 subtests passed in 80.42s (0:01:20)**. The observer collected 3,859 items; pytest exited 1. The 127 passing subtests are separate from the 3,710 ordinary passing results.

The independent snapshot contains 833 public input files (36,757,596 bytes). All copied source pins remained unchanged during the final run. Main and other workspaces were not writable from the audit boundary.

## Tested source boundary

- `generation/checked.py`: `8a23ecef2f43d4e8d6fd43f1015c6636ef95fb3146d50c8757318f9ab71d1d2d`
- `generation/reliability_v5.py`: `dc8af40d6975da5378531335e93e2deb928f97b150b576773ef8270482d5ce21`
- `generation/prompts/joint_check_v5.txt`: `00592221afa33050cc5cd56d0a6985093296ef48499611a2413eac0a73e106a4`

Source17 used the final 00592221 prompt with dc8af40d reliability and 8a23ecef checked code. Source18 removes the reason-symbol exemption after this snapshot; it is outside this result. The older 1,637-row public index supplied paths only. Every copied file was freshly hashed against Main before and after copying; the changed prompt and document pins were not asserted to match that old index.

## Preserved failures and restrictions

The 124 failure/error reports comprise 105 explicit audit denials, 12 failures associated with a refused operation in the same node, and seven missing-resource failures. No reports remained unclassified by those rules. Association is a diagnostic grouping, not a passing code certificate.

The final audit refused 65 socket binds, 50 file reads and nine subprocess launches. It observed no connect or DNS events in that final run because local server fixtures were refused at bind. Authentication stores, .env files, model keys, binder/seed receipts, forbidden Codex directories, network and process launch remained restricted. Private-file denials include synthetic temporary stores used by tests; real stores were not opened.

Four remaining resource cases depend on historical retrieval-verification evidence that was deliberately not copied. Three depend on uncopied pinned local DeepSeek tokenizer resources. Twenty-seven skips remain in the retained result. Missing files were not fabricated, and old experimental results were not substituted for fresh verification.

Run01 retained the refused default NUL logger; run02 retained the missing public helper collection failures. Both were repaired by changing local output configuration or copying real public source. Run03 retained the initial execution failures. Its audit omitted socket.bind, allowing test loopback fixtures to bind before their network connections were refused; that interpreter ended. Run04 fixed the omission without granting network or service permission. All original attempt logs and runners remain retained.

No integration tests, PostgreSQL connection, product API/DB service, installation, paid provider, Main update or Source18 re-run formed part of the final validation. Temporary SQLite unit data stayed in this owned workspace. The complete software gate and scientific/human acceptance remain separate.

Evidence: `ACTUAL_SOURCE17_RESTRICTED_UNIT16_SUMMARY.json`, the original snapshot and two public-input supplemental receipts, and `run01` through `run04` console/JSON records. Final JUnit output is `run04/pytest.xml`.
