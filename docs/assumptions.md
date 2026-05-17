# Assumptions & Local Decisions

`toonpy` implements TOON spec v3.0. This document records implementation-defined choices and exposes **strict** and **permissive** parsing modes for edge cases.

## Parsing Modes

- `from_toon(..., strict=True)` (default) — enforces all v3 invariants.
- `from_toon(..., strict=False)` / `permissive=True` — relaxes certain checks (see table below).
- `from_toon(..., spec="v2")` — routes to `toonpy._parser_v2` (the pre-v3 parser copy) for backward compatibility.

## Key Decisions

| Area | Strict Behavior | Permissive Behavior | Rationale |
| ---- | ----------------| ------------------- | ----------|
| Unquoted key format | Identifiers: `[A-Za-z_][A-Za-z0-9_]*` (no hyphens). Dotted paths allowed. | Same — no relaxation for keys | v3 spec removes hyphens from unquoted keys |
| Unquoted string with spaces | Error: `_parse_token` rejects tokens with spaces outside root context | Allowed | Root primitives always allow spaces |
| Table row count | Error if row count ≠ declared N | Rows may be fewer or more | Strict validates declared length |
| Blank lines in structures | Error in strict mode | Silently skipped | v3 spec §blank-lines |
| Delimiter mismatch | Error if `{fields}` delimiter ≠ bracket delimiter | Ignored | Catches authoring mistakes |
| Numbers | JSON number grammar; leading zeros → string; `-0` → 0 | Same | Follows spec exactly |

## Path Expansion

`from_toon(expand_paths="safe"|"lax")` post-processes dotted keys into nested objects.

- `"safe"`: only expands keys where all segments are plain identifiers (no digits, hyphens, or quoted parts). Conflicts raise `ToonSyntaxError`.
- `"lax"`: expands all dotted keys. Later keys win on conflict (last-write-wins).
- `"off"` (default): no expansion; dotted keys are stored verbatim.

Quoted keys (e.g. `"a.b": value`) are never expanded regardless of mode.

## Multiline Strings

The opening line ends with `"""` and the closing `"""` must appear on its own line. Content is captured verbatim with newline preservation.

## Tabular Format Selection (Serializer)

In `mode="auto"` (default), the serializer chooses tabular format when the estimated character savings are positive — i.e., when key repetition savings across rows outweigh the header overhead. With only 1 row, tabular is rarely worth it; with 3+ rows it almost always is.

## `@table` format

The legacy `@table` pipe-bordered format from v2 is NOT supported by the v3 parser. Documents using `@table` must be migrated to the `key[N]{fields}:` header syntax, or parsed with `spec="v2"`.
