# Native36 checker output bytes

The initial checker has **4,574 bytes of optional JSON formatting (38.86%)**; the final checker already has **zero**. Reasons are 8.95%/14.50% of the raw outputs and do not dominate. Repeated required field names, IDs, statuses and support records must remain.

| UTF8 bytes | Initial checker | Final checker |
| --- | ---: | ---: |
| Original model JSON | 11,770 | 7,646 |
| Outside-string whitespace | 4,574 | 0 |
| Field-name string lexemes | 3,211 | 3,336 |
| Value string lexemes | 3,054 | 3,341 |
| Punctuation + scalar literals | 931 | 969 |
| Losslessly minified JSON | 7,196 | 7,646 |
| Reason string lexemes (subset of values) | 1,053 | 1,109 |

Python lexical accounting reconciled each total exactly. Removing only outside-string whitespace preserved the parsed object and every original string lexeme. Neither original raw response was changed. The observed provider output counts3776/2366 are separate records; no token savings are inferred from bytes.

**Next one-variable candidate:** wait for Root's actual37 paired result, inspect its real initial formatting and serial path, then request that the model emit a single minified JSON object. Keep every V2 field, claim/unit/requirement check, selected source, quote, negative finding and quality gate; keep the full final recheck after any repair. Do not shorten reasons at the same time or change the running37 paired prompt. Post-response local minification cannot reduce the original model generation time. No new harness/API call or predicted speedup is supplied.

The observed first-checker/rechecker intervals are10.755s/7.740s. The other three requests sum22.437s, already over20s apart from the first checker. Therefore formatting alone cannot be asserted to solve that unchanged path. Repair+recheck16.811s remains the larger branch targeted by the adopted37 input hint; whether it disappears must come from actual37, without skipping recheck. Native34/36 legacy timings are single-case observations, not causal proof or p95.

The JSON report pins all three actual inputs and both retained raw strings. Its schema binding is the existing current-ReliableUnitCheck-V2 validation proof in the performance receipt (10 claims,19/21 units,71 fragments). It does not invent a canonical current37 schema hash or inspect Main. Existing independent source-quality limits remain unchanged.
