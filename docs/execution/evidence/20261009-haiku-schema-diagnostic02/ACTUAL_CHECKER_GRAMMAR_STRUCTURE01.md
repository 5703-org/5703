# Haiku full-checker schema structure (offline)

This analysis reproduces the exact existing projection using public, pinned W-only inputs. It performs no API calls, database access or Main writes. Provider compiled grammar size is unknown.

| Metric | Original full schema | Bounds projection |
| --- | ---: | ---: |
| Canonical UTF-8 bytes | 6046 | 7246 |
| Schema nodes | 99 | 99 |
| Local definitions | 10 | 10 |
| Local ref occurrences | 11 | 11 |
| Unique local ref targets | 10 | 10 |
| Declared fields | 70 | 70 |
| Required fields | 70 | 70 |
| Optional fields | 0 | 0 |
| Required nullable fields | 2 | 2 |
| Bounds | 43 | 1 |
| Enum nodes | 12 | 12 |
| Enum values (occurrences) | 36 | 36 |
| Constants | 4 | 4 |
| String patterns | 1 | 1 |
| Physical schema edge depth | 3 | 3 |
| Serialized JSON container depth | 7 | 7 |

The composition metrics remain identical:

- `anyOf`: 3 nodes / 9 explicitly written branches.
- `oneOf`: 0 nodes / 0 explicitly written branches.
- `allOf`: 0 nodes / 0 explicitly written branches.

With local references expanded, maximum output value depth is 6 and maximum container depth is 6. The separate maximums are 4 object levels and 3 array levels; they need not occur on the same path. One longest value path is `$.claims[]<(anyOf:0)>.citations[].fragment_ids[]`. One three-array path is `$.claims[]<(anyOf:0)>.citations[].fragment_ids`.

The claims array (`maxItems=100`) has five item variants. The calculation variant traverses `DerivationV4` to an inputs array (`maxItems=12`, `minItems=1`), then `CalculationInputV4`. The citation path nests `claims[]`, `citations[]` and `fragment_ids[]` arrays. Two required nullable fields each use `anyOf[string,null]`. There are no absent-from-required optional fields or `oneOf`/`allOf` combinations. These are structural descriptors, not a compiled state count.

The candidate removes 42 bounds: 18 `maxLength`, 15 `minLength` and 9 `maxItems`, and annotates 27 nodes. It retains the one `minItems=1`, the string pattern, all fields/types/required lists/enums/constants/local refs and `additionalProperties=false`. It also retains all union branches and nesting. Canonical schema text grows by 1200 bytes due to descriptions; grammar simplification cannot be inferred from fewer bytes.

Repeated reason/citation fields are in different claim variants; their similarity does not prove their local constraints redundant. Removing them from local validation, flattening claims, dropping variants or changing nullable behavior would alter the contract. The bounds-only transport projection preserves the original full local Pydantic validation, but live provider compatibility remains unverified.

The new diagnostic's minimal schema returned 200; the full schema returned 400 with a compiled-grammar-too-large explanation. That comparison identifies a schema-sensitive rejection. It does not attribute the failure to bounds, a union, nesting or a specific interaction. The historical original 400 has no captured nested explanation and must not be retroactively assigned this cause.

Reproduce with `D:\Python\python.exe -I -B -S quantify_checker_schema01.py --output-dir <fresh-folder-inside-this-W-preparation>`: result creation is exclusive and reruns never overwrite evidence. The exact source pins, metric definitions, all bounds and preserved structures are in `ACTUAL_CHECKER_GRAMMAR_STRUCTURE01.json`.
