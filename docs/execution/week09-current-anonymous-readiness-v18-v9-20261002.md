# Current V18 MAIN and installed CPU readiness — 2 October 2026

Eight anonymous GET requests passed: health, readiness, the complete frozen OpenAPI contract and the frontend HTML entry for both running installations. Every request returned HTTP 200. This checkpoint binds query preparation V18 and the default typed V5 checker to the current 818-input software gate. The two installations each matched 832 code and generated-contract inputs; the 16 intentionally private gate inputs remain outside the portable installation.

| Installation | Health | Ready | OpenAPI | Frontend |
|---|---:|---:|---:|---:|
| MAIN | 144.859 ms | 76.185 ms | 413.680 ms | 42.144 ms |
| Installed CPU | 38.946 ms | 35.079 ms | 515.407 ms | 42.949 ms |

The complete audit took 152.054 seconds, including source hashing and owned process inspection. Endpoint transport durations in the table have a different boundary from the complete audit. Both installations retained their source/settings and owned process identities before and after the eight requests. No authentication, direct database connection, database mutation, credential-content read, model call or runtime process start/stop occurred in this probe. Database preservation is bound to the earlier installation/start and finite-workflow receipts; this probe takes no new SQL snapshot.

The frontend check covers the returned HTML entry after Vite injection. Browser interaction, paid-answer quality, load, successful cancellation and independent device acceptance have their own evidence requirements.

Evidence: [allowlisted current receipt](../../evidence/week09-continuation/20261001/current-main-cpu-anonymous-readiness-v18-v9-20261002-sanitized.json). Private terminal SHA-256: `3278d455e13e1dc2f1582a2e4ba010fb7743f937bb2a91021be9f9a98615bc57`. Software gate SHA-256: `343ce4e457286fa48b7282b1cff002a3689ee6b60b2706336b601703e86961d8`; source snapshot SHA-256: `af8ed75839df54c610ce67ee88aa7f44a76fbba1c2a79fea2b878bbf1c7e503b`.
