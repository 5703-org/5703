# Current MAIN and CPU anonymous readiness

The same-host MAIN and CPU runtimes passed eight scheduled anonymous requests on
1 October 2026 UTC, from 15:01:10.403318 to 15:03:27.305124. Each returned HTTP 200.
The [sanitized receipt](../../evidence/week09-continuation/20261001/current-main-cpu-anonymous-readiness-v17-v9-20261002-sanitized.json)
SHA-256 is `e3a0b545129cb68a9ecbefa741b48e03736075f416f6ba4aac3d733b843e9d80`.

| Target | Check | Port | Transport ms | Parent including child startup ms |
| --- | --- | --- | ---: | ---: |
| MAIN | Health | 18000 | 139.550 | 289.087 |
| MAIN | Ready | 18000 | 67.086 | 193.465 |
| MAIN | OpenAPI | 18000 | 368.278 | 500.678 |
| MAIN | Frontend root | 15173 | 55.796 | 191.409 |
| CPU | Health | 18849 | 121.076 | 247.569 |
| CPU | Ready | 18849 | 52.073 | 178.903 |
| CPU | OpenAPI | 18849 | 354.412 | 481.670 |
| CPU | Frontend root | 15249 | 46.770 | 190.583 |

Health returned `status=ok`. Ready returned exact `status=ready` and `database=up`
after the normal read-only `SELECT 1`. Both complete OpenAPI objects matched the
frozen JSON contract. Frontend checks matched English language, title, root element
and module entry after Vite injection.

The [Gate03 snapshot](../../evidence/week09-continuation/20261001/software-gate-answering-admin-v17-v9-03/source_snapshot.json)
binds all 815 current MAIN inputs. Both targets match 829 reviewed installed
code/contract pins, including generated contracts/HTML and the existing sixteen
private evaluator exclusions. Guards verified four roles per target, exact PID
creation identities, executable hashes, permitted descendants and two loopback
listener owners. Source/settings/process identities remained equal. Public data
omits private paths and actual process IDs.

Eight fixed-loopback anonymous GETs ran with redirects/proxies disabled and a
ten-second wall limit per new transport child. All eight HTTP entries are confirmed,
with zero unconfirmed attempts, authenticated actions, provider calls, direct tool
database connections, mutations and credential-content reads. Ready endpoints'
read-only server connections are normal endpoint behavior.

The guarded run took 136.901801 seconds, including source hashing and process
observations. Transport and child-startup times retain separate measurements.
Signed-in CPU questions/follow-ups/cancellation, browser interaction, quality,
concurrency and recovery keep their own acceptance. Earlier process/socket/cleanup
local-tool failures remain retained while signed-in verification continues.
