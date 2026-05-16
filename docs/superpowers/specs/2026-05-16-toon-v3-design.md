# toonpy — TOON Format v3.0 Support Design

**Date:** 2026-05-16
**Status:** Approved
**Scope:** Full conformance with TOON spec v3.0 via surgical in-place extension

---

## Context

toonpy v0.5.0 implements TOON spec v2.0. The official spec has advanced to v3.0
(as of 2025-11-24), adding multiple delimiters, inline primitive arrays, root form
disambiguation, key folding, path expansion, and stricter validation. The goal is
full v3.0 conformance without regressing parse throughput on the common case
(comma delimiter, no key folding).

---

## Decisions

| Question | Decision |
|---|---|
| Scope | Full v3.0 conformance |
| Backward compat | `spec="v2"` opt-in; v3 is new default |
| Performance | Zero regression on common path; overhead only when features are used |
| API style | Individual kwargs (consistent with existing API) |
| Legacy `@table` | Eliminated; accessible only via `spec="v2"` |
| Versioning | Bump 0.5.0 → 0.6.0 |

---

## Architecture Overview

Changes are distributed across three files. The hot path (per-line parsing) is
touched only in `_parse_header_syntax` and `guess_number`.

```
toonpy/
  parser.py       ← 8 surgical changes
  serializer.py   ← 3 new areas (primitive inline, key folding, delimiter option)
  utils.py        ← extend guess_number + add is_identifier_segment

tests/
  test_spec_fixtures.py   ← NEW: auto-loads all spec repo JSONs
  tests/fixtures/         ← NEW: cached copies of spec fixtures for offline CI
```

**Performance invariant:** for a document using comma delimiter with no key folding,
the only new code executed is:
1. `_delimiter_stack` initialization — one `list` allocation
2. Extended header regex match — same O(n) on header line, larger pattern
3. `guess_number` exponent branch — only if token contains `e`/`E`

---

## Parser Changes (`parser.py`)

### P1 — Unified header syntax

`_parse_table_header_syntax` is renamed `_parse_header_syntax` and extended to
detect all header forms with a single pass:

| Pattern | Type | Example |
|---|---|---|
| `key[N]:` | Primitive inline array | `tags[3]: a,b,c` |
| `key[N]{f1,f2}:` | Tabular array (comma) | `items[2]{id,name}:` |
| `key[N\t]{f1\tf2}:` | Tabular array (tab) | `items[2\t]{id\tname}:` |
| `key[N\|]{f1\|f2}:` | Tabular array (pipe) | `items[2\|]{id\|name}:` |
| `[N]{fields}:` | Root array header | `[2]{id,name}:` |

Returns `HeaderSpec(key, length, fields, delimiter)` namedtuple. `fields=[]`
signals primitive inline. `key=None` signals root array.

All regex patterns compiled at module level.

### P2 — Delimiter stack

```python
# __init__:
self._delimiter_stack: list[str] = [","]

@property
def _active_delimiter(self) -> str:
    return self._delimiter_stack[-1]
```

Pushed/popped at header entry/exit only. The row-split hot path uses
`if delimiter == ","` → existing `split_escaped_row` call unchanged.
For tab/pipe, a dedicated `split_escaped_row(row, separator=delimiter)` call
uses the already-existing utility.

### P3 — Root form disambiguation

`parse()` updated to:
- Empty document (0 non-blank lines) → returns `{}`
- First non-blank line is `[N]...` header → root array
- First non-blank line has no key and no `-` prefix → root primitive
- Otherwise → root object (current behavior)

### P4 — Numeric normalization in `guess_number`

Extended to accept:
- Exponent notation: `1e6 → 1000000`, `-1E+03 → -1000` (via `float()` + int
  conversion when result is whole)
- `-0` and `-0.0` → `0`
- Leading zeros → returns `None` (treated as string) — already partially correct,
  made explicit

### P5 — Primitive inline array parsing

When `_parse_header_syntax` returns `fields=[]`, the value after `:` is split
by the active delimiter, each token parsed via `_parse_token`. Count validated
against `N` in strict mode.

### P6 — Arrays of arrays and mixed lists

`_parse_array` extended: when an item line starts with `[N]` or `[N\t]` etc.
(no `- key:` form), it is parsed as a nested array header. This handles:

```
pairs[2]:
  - [2]: 1,2
  - [2]: 3,4
```

### P7 — Path expansion (post-processing)

A new `_expand_paths(obj: dict, strict: bool) -> dict` function applied after
`parse()` only when `expand_paths="safe"`. It:

1. Iterates root keys
2. If key is unquoted, contains `.`, and all segments match
   `^[A-Za-z_][A-Za-z0-9_]*$` → expands with deep-merge
3. Quoted keys and keys with non-identifier chars → left as literals
4. Conflicts: `ToonSyntaxError` if `strict=True`, last-write-wins if `strict=False`

Zero overhead when `expand_paths="off"` (default).

### P8 — Blank line detection in strict mode

The current `ToonLexer.iter_lines()` discards all blank lines globally. In strict
mode the spec forbids blank lines *inside* array blocks (list and tabular), but
allows them between object fields and at root level.

When `strict=True`, the lexer emits a sentinel `Line(indent=-1, content="", line_no=n)`
for each blank line instead of discarding it. Array-parsing methods
(`_parse_array`, `_parse_table_from_header`) check for this sentinel and raise
`ToonSyntaxError`. Object-parsing and root-parsing methods skip sentinels.

When `strict=False` (or default), blank lines are discarded as today — zero overhead.

### P9 — Remove `@table`

`_parse_table()` and `TABLE_PREFIX` constant deleted. The v2 parser (dispatched
via `spec="v2"`) is the entire current `parser.py` copied verbatim to
`_parser_v2.py` before any v3 modifications — providing `@table` support and the
exact v2 semantics as a stable fallback.

---

## Serializer Changes (`serializer.py`)

### S1 — Primitive inline arrays

`_write_array` gains a pre-check before the tabular check:

```python
if all(self._is_inline(item) for item in seq):
    # emit as key[N]: v1,v2,v3
```

This is only called from `_write_object` (where key is known) and `_write_array`
(root array). Detection is O(n) — same as current tabular detection.

### S2 — Key folding

New `__init__` params: `key_folding: str = "off"`, `flatten_depth: float = inf`.

Only `_write_object` is changed. Before emitting `key: value`, calls:

```python
folded = self._try_fold(key, value, mapping_siblings, depth=self.flatten_depth)
```

`_try_fold` recursively follows single-key objects, building a dotted path string,
stopping when:
- Value is not a single-key Mapping
- Next segment requires quotes
- Dotted key would collide with a sibling literal key
- `depth` reaches 0

Returns `(folded_key, terminal_value)` or `None` (fall back to normal emit).
Collision check is O(k) over siblings — not O(n²).

### S3 — Delimiter option

`ToonSerializer.__init__` gains `delimiter: str = "comma"`. When non-default,
`_write_table_as_key` and `_write_array` emit the appropriate bracket character
(`\t` or `|`) and use it as the row separator.

---

## Updated Public API

### Decoder

```python
def from_toon(
    source: str,
    *,
    strict: bool = True,
    expand_paths: Literal["off", "safe"] = "off",
    spec: Literal["v2", "v3"] = "v3",
    permissive: bool = False,
) -> object: ...
```

### Encoder

```python
def to_toon(
    obj: Any,
    *,
    indent: int = 2,
    mode: Literal["auto", "compact", "readable"] = "auto",
    delimiter: Literal["comma", "tab", "pipe"] = "comma",
    key_folding: Literal["off", "safe"] = "off",
    flatten_depth: int | float = float("inf"),
) -> str: ...
```

### Backward compatibility

| Existing call | Behavior after upgrade |
|---|---|
| `from_toon(src)` | v3 default — same except: empty doc → `{}`, exponents accepted |
| `from_toon(src, permissive=True)` | Unchanged |
| `from_toon(src, spec="v2")` | Exact v2 parser, `@table` supported |
| `to_toon(obj)` | Identical |
| `to_toon(obj, mode="compact")` | Identical |
| Document with `@table` | Error in v3; use `spec="v2"` |

---

## Testing Strategy

### `test_spec_fixtures.py` (new)

Parametrically loads all fixture JSONs from the official spec repo
(`github.com/toon-format/spec/tests/fixtures/`). Fixtures cached in
`tests/fixtures/decode/` and `tests/fixtures/encode/` for offline CI.

Decode fixtures: `primitives`, `numbers`, `objects`, `arrays-primitive`,
`arrays-tabular`, `arrays-nested`, `delimiters`, `whitespace`, `root-form`,
`validation-errors`, `indentation-errors`, `blank-lines`, `path-expansion`

Encode fixtures: `primitives`, `objects`, `arrays-primitive`, `arrays-tabular`,
`arrays-nested`, `arrays-objects`, `delimiters`, `whitespace`, `options`,
`key-folding`

Each test case with `shouldError: true` asserts `ToonSyntaxError` is raised.
Cases with `options` pass them as kwargs.

### Benchmarks

Run `benchmark_*.py` before any code changes to capture baseline, then again
after completion. Tracked metrics:

- Parse throughput MB/s — comma-only documents (must not regress > 2%)
- Parse throughput — tab/pipe delimiter documents
- Serialize throughput — without and with key folding
- Memory peak via `tracemalloc`

### Done criteria

- All spec fixtures pass (decode + encode)
- All existing tests pass
- Parse throughput regression < 2% on comma-only documents
- `mypy` clean on modified files
