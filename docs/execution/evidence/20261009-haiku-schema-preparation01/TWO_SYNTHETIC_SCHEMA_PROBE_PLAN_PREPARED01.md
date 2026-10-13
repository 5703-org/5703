Two synthetic schema probes are prepared; neither has been executed. The actual05 checker HTTP400 cause remains unobserved. This plan uses the parent's independent authorization of at most two new physical POSTs and $0.06.

The executable is `haiku_two_schema_probe_PREPARED04.py` (24426 bytes, SHA256 `5ea9cebfd91fc85609ef73cac8467266843343644d9e20cc27eaef0308e0d992`). Candidate01–03 remain preserved and must not be executed. The minimal 03→04 diff is `HAIKU_PROBE_03_TO_04_PUBLIC_DIFF01.txt` (4422 bytes, SHA256 `3234a6d1680b7ca62ca071b0ad648c41b26da818d3ecfb5ecfaf71db9d8311e7`).

Both cases use the same pinned public fabricated native checker messages: speed 3 m/s, time 4 s, two messages ending in user. They contain no Q3/Q4 or learner input. Both retain the actual checker schema name `joint_check_v5`, model `anthropic/claude-haiku-5.5`, OpenRouter endpoint, Google Vertex global route only, fallback false, require_parameters true, reasoning low, no sampling parameters, max_tokens 4096, strict json_schema, and price caps prompt $0.30/completion $2.50 per million tokens. The only payload variable is the response schema: first the required Boolean `{ok: bool}` object with additionalProperties false; then the exact full actual05 checker schema.

Pinned inputs under `continuous-preparation/haiku-schema-analysis`:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| CHECKER_ACTUAL05_EXACT_SCHEMA01.json | 6047 | 08195238e12de5a2e49a575625af7ecd8e4f1bed776ac57853c63a0c7bb80524 |
| CHECKER_ACTUAL05_EXACT_WIRE_CONTROLS01.json | 6409 | bb9549c9baa74e085ea4b049ecf859a03e8945334f2bd9101670da8a519a73f7 |
| FABRICATED_DISTANCE_CHECKER_MESSAGES01.json | 17237 | db61aee38b9fbecf314f5c4903f8b683804a2775ada41f0ffcbfbeedc2947718 |
| TINY_STRUCTURED_CONTROL_SCHEMA01.json | 104 | ae2311429294622046afe45e52f2fe2c9a5ca59349414e9ab43579ba66df94fb |

Full schema canonical hash is `7988037e08d52662a1b232f049776a42b6d10ad5d896f1a26c8c912b3efd79d4`; actual full controls canonical hash is `4e5b6ed97b6d71ed4bca1dffd22c07e82dc404c92de457cd340aaa61114eafe9`. Wire is capped at 60000 bytes; input upper bound is wire bytes plus 512, at most 60512, below the 100000 token tier boundary. Conservatively pricing this upper bound at the retained caps gives $0.02839360 per POST, or $0.05678720 for two. Full reservations remain $0.03 each/$0.06 total. Verified base tariff $0.10/$0.50 gives a separate uniform upper bound $0.00809920 each/$0.01619840 for two; it does not replace reservations.

The first case must return HTTP200, finish_reason stop, no refusal or embedded error, and pass local strict Boolean validation. A valid result missing reported cost keeps its full $0.03 UNKNOWN hold and may proceed to the second reserved $0.03. A first HTTP error, timeout, invalid or incomplete result ends the run before case two. No retry, redirect, provider fallback, generation GET, or extra model request exists. The exact checker result uses the unchanged public `ReliableCheckV5.model_validate(strict_json(rawtext))`. These are transport/schema diagnostics; they establish no native answer publication, course acceptance, or RAG quality PASS. If the minimal case fails, schema causality is not established, particularly given the shared full checker prompt.

Actual05's old UNKNOWN finished receipt and STOP are checked before each POST and at final cleanup, never edited or cleared. Its $0.03 full hold remains protected independently; old hold plus this new reservation is $0.09. No original Q3 request is retransmitted. New valid-result missing metering is distinguished from an invalid provider response, never treated as zero cost.

Only Root execution loads the existing approved credential. The existing PG URI consumer is pinned at `serve_current_fixture_native_API_PREPARED08.py` SHA256 `d8d3ec29dc11cd4fa3d0b5ea636412d840dc4177300b77a3ee1703ac1b15d2b6`. It targets only the already existing synthetic B database `cs30_week10_pair_b_20261009_01` at 127.0.0.1:15433. Both transaction_read_only and default_transaction_read_only must report on. The public actual05 binder (92397 bytes/SHA256 `fe88a271eb6203dc4d04fc0ef3263428a4b269d56057ee0eeee9f48ecf4ae471`) binds workspace `5ef0e22c-45f2-4c72-9ff8-acfee1e6b655`, baseline `74c8201e-aca0-400d-bcc5-5785e24c1c11`, revision 1, config hash `703c94a357ddd4b826d8b5fe25d503198d3d56e1e9130f6a37ed9e9c3396aa4a`. The existing public resolve_secret(db, settings, configuration_id) is AST-loaded exactly, with original ORM/decrypt dependencies. The existing key-file reference is used only by normal approved decrypt in memory. No new secret/key/environment file, DB write, rebuild, activation or default change occurs; Session and engine are closed before POST. The pure generation namespace is installed before that credential consumer, avoiding the denied providers module.

Each started receipt is create-only and fsynced before POST. Finished receipts retain UTC timestamps, latency, safe request/generation ID, HTTP status, finish reason, token usage, reported cost or full UNKNOWN hold, and local validation status. HTTP error bodies are bounded in memory at 65536 bytes; only outer error.message and parsed nested provider error.message are exported after actual-secret/Bearer/sk/URL-credential redaction and 600-character clipping. Public schema pointers/features may be recorded. No raw body, prompts, headers, credentials or learner data is exported. Request timeout is 180 seconds to allow schema compilation.

Three actual offline pure checks passed in 0.002s, with zero application imports, DB connections, credential reads, network or model calls. Evidence: `ACTUAL_HAIKU_PROBE_PURE_FREE_GATE01.json` (1643 bytes/SHA256 `a389bbec86314943cc173394899bdb9a243de55f8b2f76e6001513158d1154a1`) plus its `.log`. Reproduction:

```powershell
& 'D:\Python\python.exe' -I -B -S 'C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-week10-native-pair-20261009-01\diagnostic-preparation\test_haiku_probe_pure_PREPARED02.py'
```

Root's exact paid execution command after review and recovery of only the existing owned test service:

```powershell
& 'D:\Python\python.exe' -I -B -S 'C:\Users\PC\Documents\Codex\2026-10-04\task-2\5703-week10-native-pair-20261009-01\diagnostic-preparation\haiku_two_schema_probe_PREPARED04.py' --execute-authorized-two-probes --workspace-id '5ef0e22c-45f2-4c72-9ff8-acfee1e6b655'
```

Launch with a short tool yield so Root can send progress while the process runs. Output is the fixed fresh directory `diagnostic-preparation/haiku-schema-diagnostic01`; no prior directory may be resumed or overwritten. Remaining blocker at preparation time: the original Docker/PG service is down after reboot. Root owns restoring the installed daemon and starting the same existing container, with no pull/create/compose/rebuild/seed. This agent has not started services, queried DB, read credentials, or sent POSTs.
