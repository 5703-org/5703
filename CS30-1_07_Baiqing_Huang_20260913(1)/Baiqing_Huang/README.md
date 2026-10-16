# Baiqing Huang: assigned development handover

Student ID: 540976443. Area: Learner and administrator UI, sources and responsive interaction.

This package contains 61 assigned project files. Use the complete runnable package for shared infrastructure, dependencies, corpus and model assets. These eight module packages are disjoint contributions to one application.

Original task IDs: FE-01, FE-02, FE-03, FE-04, FE-05, FE-06, FE-07, FE-08, FE-09, FE-10, FE-11, FE-12, CHAT-06. The authoritative current states and evidence are in `docs/execution/tasks.json`, `acceptance.json`, and `ui_acceptance.json` in the full project. Assignment records responsibility and review scope; Codex performed the shared implementation.

## Integration

1. Keep a copy of the complete project and its history.
2. Review `OWNED_FILES.json` and copy `repo_files/` into a separate working checkout, preserving relative paths.
3. Merge the eight packages in the order recorded in `EIGHT_MEMBER_INVENTORY.json`. Every source path has one owner.
4. Install from the complete package with `scripts/release/start_local.ps1 -Install`. Configure a new provider through Administration > Models.
5. Run the documented software checks and inspect the real-live evidence and outstanding independent review in the upgrade record.

The full package includes hashes for every source/resource. Keys and existing learner records are excluded. Member packages do not include duplicate shared model weights.
