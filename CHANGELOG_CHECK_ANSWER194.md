# Candidate194 change notes

15 October 2026 UTC. Base: the immutable Candidate182 source archive. Feature authority: accepted phase189 code and phase190 Main deployment. Historical experiments and earlier archives remain unchanged.

## Product behavior

- Ordinary new drafts show `Check answer` unchecked. The request sends the chosen boolean.
- Omitted/null API values retain legacy checked behavior. Internal verification mode is server selected.
- Request creation resolves the actual learning task before deciding whether checking is optional. Hints, pending attempts, practice, goals and protected experiments retain mandatory checking.
- Retry, cancellation recovery, regeneration and history retain the saved choice. A regenerated request gets fresh verification metadata, not a copied verdict.
- Unchecked answers do not read a checker configuration/key, allocate a checker call or claim a semantic pass. Source visibility, evidence/citation binding, parsing and privacy still apply.
- No new selector, reminder, badge or post-answer verification action is added. No database column, provider/window setting or credential migration is introduced.

## Integration and source parity

The phase189 increment is applied to phase182 rather than replacing the package with Main. The seven documented phase182 goal-review/portability files remain exact. The generation/checked.py checkbox hunks are ported onto the phase182 base; later Main-only assertion-provenance/revision work is excluded. Combined OpenAPI JSON/YAML and generated frontend types are produced from the actual combined application so its existing goal-review routes remain present. The resulting package therefore shares checkbox contracts/behavior with Main, but is not byte-identical to all 474 Main source pins. Exact unchanged/different/added paths are recorded in the release manifests and assembly evidence.

## Verification and limits

See the adjacent archive verification receipt for the fresh extracted-package checks. They use existing installed dependencies, mock answering and disposable synthetic storage, with real provider transports blocked. They establish only the recorded software/startup/default-choice/persistence behavior. Earlier phase189/190checks remain source-bound historical evidence. No paid call, complete-answer speed result, semantic-quality result, new-PC install or full-suite rerun is inferred. Existing UNKNOWN costs, paused real tests and prior rejection receipts stay unchanged.

## Safe use and recovery

Extract into a new directory and follow WINDOWS_SOURCE_INSTALL.md. Preserve the earlier archive and installation. Configure private model access only through that installation's normal controls; no key is supplied here. Routine development uses the intended existing DeepSeek configuration, while cross-model comparisons have separate explicit scope. To return to the prior release, open the retained old installation/archive; do not copy databases, keys or partial trees across releases. There is no automatic rollback or database downgrade.
