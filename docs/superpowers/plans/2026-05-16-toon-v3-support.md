# TOON v3.0 Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement full TOON spec v3.0 compliance in toonpy via surgical in-place extension, with zero performance regression on the common path (comma delimiter, no key folding), and all official spec fixtures passing.

**Architecture:** Keep existing `parser.py` / `serializer.py` / `utils.py` as the base. Add v3 features additively: delimiter stack (only activated when non-comma headers are encountered), primitive inline arrays, root form disambiguation, blank-line sentinels in strict mode, key folding in serializer, and path expansion as a post-processing pass. Copy the current `parser.py` verbatim to `toonpy/_parser_v2.py` before modification for the `spec="v2"` backward-compat path.

**Tech Stack:** Python 3.9+, pytest, hypothesis, urllib.request (stdlib — no new deps), existing toonpy infrastructure.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `toonpy/_parser_v2.py` | **Create** | Verbatim copy of current `parser.py` — used when `spec="v2"` |
| `toonpy/utils.py` | **Modify** | Extend `guess_number`, add `is_identifier_segment`, add `split_row_v3` |
| `toonpy/parser.py` | **Rewrite** | Full v3 parser with all new features |
| `toonpy/serializer.py` | **Modify** | Primitive inline arrays, key folding, delimiter option |
| `toonpy/_path_expansion.py` | **Create** | `expand_paths()` post-processing function |
| `toonpy/api.py` | **Modify** | New kwargs on `from_toon` and `to_toon` |
| `tests/fixtures/download_fixtures.py` | **Create** | Script to download and cache spec fixtures |
| `tests/fixtures/decode/*.json` | **Create** | Cached spec decode fixtures |
| `tests/fixtures/encode/*.json` | **Create** | Cached spec encode fixtures |
| `tests/test_spec_fixtures.py` | **Create** | Parametric test runner for all spec fixtures |
| `benchmark_baseline.txt` | **Create** | Benchmark output captured before any code changes |

---

## Task 0: Capture Performance Baseline

**Files:**
- Create: `benchmark_baseline.txt`

- [ ] **Step 1: Run all benchmarks and save output**

```
python benchmark_optimizations.py > benchmark_baseline.txt 2>&1
python benchmark_serializer.py >> benchmark_baseline.txt 2>&1
python benchmark_parallel.py >> benchmark_baseline.txt 2>&1
```

Expected: File `benchmark_baseline.txt` created with timing numbers. Note the parse throughput MB/s figures — these are the targets to beat or match after implementation.

- [ ] **Step 2: Commit the baseline**

```
git add benchmark_baseline.txt
git commit -m "chore: capture performance baseline before v3 changes"
```

---

## Task 1A: Create v2 Backward-Compat Parser

**Files:**
- Create: `toonpy/_parser_v2.py`
- Read: `toonpy/parser.py` (source to copy verbatim)

- [ ] **Step 1: Copy current parser.py verbatim**

```
copy toonpy\parser.py toonpy\_parser_v2.py
```

- [ ] **Step 2: Verify the copy is byte-identical**

```
python -c "
a = open('toonpy/parser.py', 'rb').read()
b = open('toonpy/_parser_v2.py', 'rb').read()
assert a == b, 'Copy failed!'
print('OK — files are identical')
"
```

Expected output: `OK — files are identical`

- [ ] **Step 3: Commit**

```
git add toonpy/_parser_v2.py
git commit -m "chore: copy parser.py to _parser_v2.py for spec=v2 backward compat"
```

---

## Task 1B: Download and Cache Spec Fixtures

**Files:**
- Create: `tests/fixtures/download_fixtures.py`
- Create: `tests/fixtures/decode/*.json` (13 files)
- Create: `tests/fixtures/encode/*.json` (10 files)

- [ ] **Step 1: Write the download script**

Create `tests/fixtures/download_fixtures.py`:

```python
"""Download and cache TOON spec fixtures from the official repo."""
import json
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/toon-format/spec/main/tests/fixtures"
DECODE = [
    "primitives", "numbers", "objects", "arrays-primitive", "arrays-tabular",
    "arrays-nested", "delimiters", "whitespace", "root-form",
    "validation-errors", "indentation-errors", "blank-lines", "path-expansion",
]
ENCODE = [
    "primitives", "objects", "arrays-primitive", "arrays-tabular",
    "arrays-nested", "arrays-objects", "delimiters", "whitespace",
    "options", "key-folding",
]

def download_all():
    root = Path(__file__).parent
    for category, names in [("decode", DECODE), ("encode", ENCODE)]:
        out_dir = root / category
        out_dir.mkdir(exist_ok=True)
        for name in names:
            url = f"{BASE}/{category}/{name}.json"
            dest = out_dir / f"{name}.json"
            print(f"Downloading {url} …")
            with urllib.request.urlopen(url) as resp:
                data = json.loads(resp.read())
            dest.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"  → {dest} ({len(data['tests'])} tests)")

if __name__ == "__main__":
    download_all()
```

- [ ] **Step 2: Run the download script**

```
python tests/fixtures/download_fixtures.py
```

Expected: 23 JSON files created across `tests/fixtures/decode/` and `tests/fixtures/encode/`.

- [ ] **Step 3: Verify counts**

```
python -c "
import json, pathlib
total = 0
for f in sorted(pathlib.Path('tests/fixtures').rglob('*.json')):
    data = json.loads(f.read_text())
    n = len(data['tests'])
    total += n
    print(f'{f.relative_to(\"tests/fixtures\")}: {n} tests')
print(f'Total: {total} test cases')
"
```

Expected: ~200+ test cases total across all fixture files.

- [ ] **Step 4: Commit fixtures**

```
git add tests/fixtures/
git commit -m "test: cache TOON spec v3.0 fixtures from official repo"
```

---

## Task 1C: Extend utils.py

**Files:**
- Modify: `toonpy/utils.py`
- Test: `tests/test_parser.py` (add number tests inline for now; spec fixtures cover the rest)

The current `guess_number` has three issues:
1. `int("-05")` returns -5 but should return None (leading zero after sign)
2. `float("1e6")` returns `1000000.0` (float) but spec expects `1000000` (int)
3. `-0` and `-0.0` should normalize to `0`

- [ ] **Step 1: Rewrite `guess_number` in `utils.py`**

Replace the existing `guess_number` function (lines 209–250 in current utils.py) with:

```python
def guess_number(token: str) -> int | float | None:
    """Attempt to parse a token as a number per TOON spec v3.

    Rules:
    - Leading zeros (e.g. '05', '-05') → None (treated as string)
    - Exponent notation (e.g. '1e6', '-1E+03') → evaluated, int if whole
    - -0 and -0.0 → 0
    - Returns int for whole numbers, float otherwise
    """
    if not token:
        return None
    first = token[0]
    if not (first.isdigit() or first == '-'):
        return None
    # Regex validates first — rejects leading zeros, validates grammar
    if not NUMBER_RE.match(token):
        return None
    # Has decimal point or exponent — use float path
    if '.' in token or 'e' in token or 'E' in token:
        try:
            val = float(token)
        except ValueError:
            return None
        # Normalize -0.0 → 0
        if val == 0:
            return 0
        # Return int if the float is a whole number (e.g. 1e6 → 1000000)
        int_val = int(val)
        return int_val if int_val == val else val
    # Integer path
    try:
        return int(token)  # int("-0") == 0 in Python, handles -0 case
    except ValueError:
        return None
```

- [ ] **Step 2: Add `is_identifier_segment` to `utils.py`**

Add after `is_safe_identifier`:

```python
IDENTIFIER_SEGMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def is_identifier_segment(segment: str) -> bool:
    """Check if a string is a valid path-expansion segment (no dots or hyphens).

    Used by path expansion (expandPaths='safe') to determine if a dotted
    key segment can be expanded. Stricter than is_safe_identifier — no hyphens,
    no dots.
    """
    return bool(IDENTIFIER_SEGMENT_RE.match(segment))
```

Also add `"is_identifier_segment"` to `__all__`.

- [ ] **Step 3: Add `split_row_v3` to `utils.py`**

Add after `split_escaped_row`:

```python
def split_row_v3(row: str, separator: str) -> list[str]:
    """Split a v3 table/array row by separator, respecting quoted strings.

    Unlike split_escaped_row (which handles legacy @table pipe-bordered format),
    this function treats separator as a pure delimiter with no stripping magic.
    Fast path for rows with no quoted strings (the common case).

    Args:
        row: Row string to split (already stripped of leading/trailing whitespace)
        separator: Single-character delimiter (',' '\\t' or '|')

    Returns:
        List of raw cell strings (caller strips whitespace and parses tokens)
    """
    # Fast path: no quotes — simple split is O(n) with no allocation overhead
    if '"' not in row:
        return row.split(separator)
    # Slow path: walk char-by-char to respect quoted strings
    parts: list[str] = []
    start = 0
    in_string = False
    i = 0
    n = len(row)
    while i < n:
        ch = row[i]
        if ch == '\\' and in_string and i + 1 < n:
            i += 2
            continue
        if ch == '"':
            in_string = not in_string
            i += 1
            continue
        if ch == separator and not in_string:
            parts.append(row[start:i])
            start = i + 1
        i += 1
    parts.append(row[start:])
    return parts
```

Also add `"split_row_v3"` and `"is_identifier_segment"` to `__all__`.

- [ ] **Step 4: Run existing tests to make sure nothing broke**

```
pytest tests/ -x -q
```

Expected: All existing tests pass.

- [ ] **Step 5: Commit**

```
git add toonpy/utils.py
git commit -m "feat(utils): extend guess_number for v3 numerics, add split_row_v3 and is_identifier_segment"
```

---

## Task 2D: Rewrite parser.py for TOON v3

**Files:**
- Modify: `toonpy/parser.py`

This is the largest task. Work section by section. After each section, run `pytest tests/ -x -q` to catch regressions early.

**Required imports at top of `parser.py`** (ensure these are present):
```python
from __future__ import annotations
from dataclasses import dataclass
from io import StringIO
import json
import re
from typing import List, NamedTuple, Sequence, Tuple
from .errors import ToonSyntaxError
from .utils import guess_number, is_safe_identifier, split_row_v3
```

### 2D-1: Add `HeaderSpec` and update module-level constants

- [ ] **Step 1: Replace module-level regex block**

At the top of `parser.py`, replace the two regex patterns with:

```python
from typing import NamedTuple

COMMENT_PREFIXES = ("#", "//")
# TABLE_PREFIX removed — @table is not part of v3 spec

# Sentinel content value for blank lines in strict mode
_BLANK_SENTINEL = "\x00BLANK"

class HeaderSpec(NamedTuple):
    """Parsed result of a TOON array header line."""
    key: str | None        # None for root-level headers like [N]{fields}:
    length: int            # declared array length N
    fields: list[str]      # field names; empty list = primitive inline or list format
    delimiter: str         # active delimiter: "," "\t" or "|"

# Compiled at module level for O(1) reuse
# Matches: optionally-quoted-key [N<delim?>] {fields<delim?>}: or just [N<delim?>]{fields<delim?>}:
# Groups: (quoted_key | unquoted_key | None), N, delim_char, fields_str, inline_values_or_empty
_HEADER_RE = re.compile(
    r'^(?:("(?:[^"\\]|\\.)*")|([A-Za-z_][A-Za-z0-9_.]*)|)'  # optional key
    r'\[(\d+)([|\t]?)\]'                                       # [N<delim?>]
    r'(?:\{([^}]*)\})?'                                        # optional {fields}
    r':(.*)$'                                                  # : and rest of line
)

_LITERAL_CACHE = {
    "true": True, "True": True, "TRUE": True,
    "false": False, "False": False, "FALSE": False,
    "null": None, "None": None, "NULL": None,
}
```

### 2D-2: Update `ToonLexer` to support strict mode and blank sentinels

- [ ] **Step 2: Update `ToonLexer.__init__` and `iter_lines`**

```python
class ToonLexer:
    def __init__(self, source: str, *, strict: bool = True, indent_size: int = 2) -> None:
        self.source = source.replace("\r\n", "\n").replace("\r", "\n") if "\r" in source else source
        self.strict = strict
        self.indent_size = indent_size

    def iter_lines(self) -> list[Line]:
        text = self._remove_block_comments(self.source)
        lines: list[Line] = []
        for idx, raw in enumerate(text.split("\n"), start=1):
            stripped = self._strip_inline_comment(raw)
            # A line that is whitespace-only (but not empty) is a "blank with spaces"
            is_blank = not stripped.strip()
            if is_blank:
                if self.strict:
                    # Emit sentinel so array parsers can detect and raise an error.
                    # Lines of pure whitespace are treated the same as empty lines.
                    lines.append(Line(indent=-1, content=_BLANK_SENTINEL, line_no=idx))
                continue  # always skip blank lines in non-strict (current behaviour)
            leading = len(stripped) - len(stripped.lstrip(" \t"))
            prefix = stripped[:leading]
            if "\t" in prefix:
                raise ToonSyntaxError("Tabs are not allowed for indentation", idx, 1)
            indent = len(prefix)
            # Strict mode: indentation must be a multiple of indent_size
            if self.strict and indent > 0 and indent % self.indent_size != 0:
                raise ToonSyntaxError(
                    f"Indentation ({indent} spaces) is not a multiple of indent size ({self.indent_size})",
                    idx, 1,
                )
            content = stripped[leading:].rstrip()
            lines.append(Line(indent=indent, content=content, line_no=idx))
        return lines
```

### 2D-3: Update `ToonParser.__init__` with delimiter stack and v3 options

- [ ] **Step 3: Update `ToonParser.__init__`**

```python
class ToonParser:
    def __init__(
        self,
        source: str,
        *,
        strict: bool = True,
        permissive: bool = False,
        indent: int = 2,
        expand_paths: str = "off",
    ) -> None:
        self.strict = strict
        self.permissive = permissive
        self.expand_paths = expand_paths
        self.lines = ToonLexer(source, strict=strict, indent_size=indent).iter_lines()
        # Delimiter stack: only modified at header entry/exit.
        # Fast path: if _delimiter_stack[-1] == "," use existing split logic.
        self._delimiter_stack: list[str] = [","]
        self._stored_indent = indent  # used by _dispatch_header for child indent calculation
```

### 2D-4: Update `parse()` for root form disambiguation

- [ ] **Step 4: Replace `parse()` method**

```python
def parse(self) -> object:
    # Skip leading blank sentinels
    real_lines = [l for l in self.lines if l.content != _BLANK_SENTINEL]
    if not real_lines:
        return {}  # empty document → empty object (v3 spec §5)

    first = real_lines[0]

    # Root array: first non-blank line is a header with no key
    header = self._parse_header_syntax(first.content)
    if header is not None and header.key is None:
        value, next_idx = self._dispatch_header(0, header, indent=0)
        # skip trailing blank sentinels
        while next_idx < len(self.lines) and self.lines[next_idx].content == _BLANK_SENTINEL:
            next_idx += 1
        if next_idx != len(self.lines):
            extra = self.lines[next_idx]
            raise ToonSyntaxError("Unexpected content after root array", extra.line_no, 1)
        return value

    # Root object: line has a colon (key: value)
    if ":" in first.content:
        key, _ = self._split_key_value(first.content)
        if key is not None:
            value, next_idx = self._parse_object(0, first.indent)
            while next_idx < len(self.lines) and self.lines[next_idx].content == _BLANK_SENTINEL:
                next_idx += 1
            if next_idx != len(self.lines):
                extra = self.lines[next_idx]
                raise ToonSyntaxError("Unexpected content after document", extra.line_no, 1)
            result = value
            if self.expand_paths != "off" and isinstance(result, dict):
                from ._path_expansion import expand_paths as _ep
                result = _ep(result, strict=self.strict)
            return result

    # Root primitive: single value (may contain spaces, unicode — no quoting required)
    if len(real_lines) == 1 or not self.strict:
        value = self._parse_root_primitive(first)
        return value

    raise ToonSyntaxError(
        "Two primitives at root depth are not allowed in strict mode",
        real_lines[1].line_no, 1,
    )

def _parse_root_primitive(self, line: Line) -> object:
    """Parse a root-level primitive (the entire line is the value)."""
    content = line.content
    # Check literal cache first
    if content in _LITERAL_CACHE:
        return _LITERAL_CACHE[content]
    # Quoted string
    if content.startswith('"'):
        return self._parse_string_literal(content, line)
    # Try number (includes exponent notation)
    if content and (content[0].isdigit() or content[0] == '-'):
        n = guess_number(content)
        if n is not None:
            return n
    # Raw string — at root level, spaces and unicode are allowed unquoted
    return content
```

### 2D-5: Implement `_parse_header_syntax` (unified for all header types)

- [ ] **Step 5: Replace `_parse_table_header_syntax` with `_parse_header_syntax`**

```python
def _parse_header_syntax(self, content: str) -> HeaderSpec | None:
    """Parse a TOON v3 array header line.

    Recognises all forms:
      key[N]:               → primitive inline (fields=[])
      key[N]{f1,f2}:        → tabular (comma)
      key[N|]{f1|f2}:       → tabular (pipe)
      key[N\\t]{f1\\tf2}:    → tabular (tab)
      [N]:                  → root list array (key=None)
      [N]{fields}:          → root tabular array (key=None)
    Quoted keys ("my-key") are supported.
    Returns None if the line is not a header.
    """
    m = _HEADER_RE.match(content.strip())
    if m is None:
        return None
    quoted_key, unquoted_key, n_str, delim_char, fields_str, rest = m.groups()
    # Determine key
    if quoted_key is not None:
        try:
            import json as _json
            key: str | None = _json.loads(quoted_key)
        except Exception:
            return None
    elif unquoted_key is not None:
        key = unquoted_key
    else:
        key = None  # root-level header

    length = int(n_str)
    delimiter = delim_char if delim_char else ","

    # Parse fields using the detected delimiter
    if fields_str is not None:
        raw_fields = fields_str.split(delimiter) if fields_str.strip() else []
        fields = [f.strip() for f in raw_fields if f.strip()]
        # Strict: field delimiter must match bracket delimiter
        if self.strict and fields_str and delimiter == "," and "\t" in fields_str:
            raise ToonSyntaxError("Delimiter mismatch between brackets and field list", None, None)
    else:
        fields = []

    return HeaderSpec(key=key, length=length, fields=fields, delimiter=delimiter)
```

### 2D-6: Add `_dispatch_header` — routes headers to the right parser

- [ ] **Step 6: Add `_dispatch_header` method**

```python
def _dispatch_header(
    self, index: int, header: HeaderSpec, indent: int
) -> tuple[object, int]:
    """Route a parsed header to the correct array parser.

    - Primitive inline (fields=[] + inline values after ':'): parse inline
    - List format (fields=[] + no inline values): parse '- ' items
    - Tabular (fields != []): parse indented rows
    """
    line = self.lines[index]
    # Get the text after the final ':' in the header
    colon_pos = line.content.rfind(":")
    inline_rest = line.content[colon_pos + 1:].strip() if colon_pos != -1 else ""

    if header.fields:
        # Tabular array: push delimiter, parse rows, pop
        self._delimiter_stack.append(header.delimiter)
        result, next_idx = self._parse_table_rows(
            index, header.fields, header.length, indent, header.delimiter
        )
        self._delimiter_stack.pop()
        return result, next_idx

    if inline_rest:
        # Primitive inline array: 'key[N]: v1,v2,v3'
        return self._parse_inline_array(
            inline_rest, header.length, header.delimiter, line, index
        )

    # List format array: 'key[N]:' followed by '- ' items
    # Handle [0]: — empty array
    if header.length == 0:
        return [], index + 1

    self._delimiter_stack.append(header.delimiter)
    result, next_idx = self._parse_list_items(
        index + 1, indent + self._indent_size(), header.length, line
    )
    self._delimiter_stack.pop()
    return result, next_idx


```

### 2D-7: Implement `_parse_inline_array`

- [ ] **Step 7: Add `_parse_inline_array` method**

```python
def _parse_inline_array(
    self, inline_str: str, expected: int, delimiter: str, line: Line, line_index: int
) -> tuple[list, int]:
    """Parse 'key[N]: v1,v2,v3' — values after the colon, comma/tab/pipe separated.

    line_index is the index of `line` in self.lines (passed by caller to avoid O(n) lookup).
    """
    if expected == 0:
        if inline_str:
            raise ToonSyntaxError(
                "Array declared length 0 but has inline values", line.line_no, 1
            )
        return [], line_index + 1

    raw_cells = split_row_v3(inline_str, delimiter)
    if self.strict and len(raw_cells) != expected:
        raise ToonSyntaxError(
            f"Inline array declared {expected} items, got {len(raw_cells)}",
            line.line_no, 1,
        )
    values = [self._parse_token(cell.strip(), line) for cell in raw_cells]
    return values, line_index + 1
```

### 2D-8: Implement `_parse_list_items` (replaces old `_parse_array`)

- [ ] **Step 8: Add `_parse_list_items` method**

```python
def _parse_list_items(
    self, start: int, indent: int, expected: int, header_line: Line
) -> tuple[list, int]:
    """Parse '- ' delimited list items at given indent level.

    Handles: scalars, objects (first field on hyphen line), nested arrays
    (- [N]: ...), and the special case where the first field of an object
    is a tabular array (- key[N]{fields}: with rows at indent+2).
    """
    values: list = []
    index = start

    while index < len(self.lines):
        line = self.lines[index]

        # Skip blank sentinels — but in strict mode they're errors inside arrays
        if line.content == _BLANK_SENTINEL:
            if self.strict:
                raise ToonSyntaxError(
                    "Blank line inside array is not allowed in strict mode",
                    line.line_no, 1,
                )
            index += 1
            continue

        if line.indent != indent or not self._is_array_line(line.content):
            break

        rest = line.content[2:] if line.content.startswith("- ") else line.content[1:]

        # Bare '-' → empty object {}
        if not rest.strip():
            values.append({})
            index += 1
            continue

        rest = rest.strip()

        # Check if rest is a nested array header: '[N]...' (no key)
        nested_header = self._parse_header_syntax(rest)
        if nested_header is not None and nested_header.key is None:
            # Inline nested: '- [2]: 1,2' or '- [N]{fields}:' + rows
            # For list/tabular nested arrays, the indent base is `line.indent`
            # We need to temporarily insert a virtual line context.
            # Simplest: call _dispatch_header on a synthetic context.
            inner, next_idx = self._dispatch_header_from_rest(
                index, nested_header, line, outer_indent=indent
            )
            values.append(inner)
            index = next_idx
            continue

        # Check if rest is a keyed header: 'key[N]{fields}:' as first field of object
        keyed_header = self._parse_header_syntax(rest)
        if keyed_header is not None and keyed_header.key is not None:
            obj, next_idx = self._parse_object_item_with_header(
                index, keyed_header, line, indent
            )
            values.append(obj)
            index = next_idx
            continue

        # Regular object-as-list-item: '- key: value'
        inline_key_text, inline_value_text = self._split_key_value(rest)
        if inline_key_text is not None:
            obj_item: dict = {}
            key = self._parse_key(inline_key_text, line)
            if inline_value_text == "":
                child_index = index + 1
                if child_index >= len(self.lines) or self.lines[child_index].indent <= indent:
                    raise ToonSyntaxError("Expected block for inline object entry", line.line_no, 1)
                value, next_idx = self._parse_value(child_index)
                obj_item[key] = value
                index = next_idx
            else:
                obj_item[key] = self._parse_token(inline_value_text, line)
                index += 1
            # Continue reading sibling fields at indent+2
            child_indent = indent + 2
            while index < len(self.lines):
                sib = self.lines[index]
                if sib.content == _BLANK_SENTINEL:
                    if self.strict:
                        raise ToonSyntaxError("Blank line inside array item object", sib.line_no, 1)
                    index += 1
                    continue
                if sib.indent != child_indent:
                    break
                sib_header = self._parse_header_syntax(sib.content)
                if sib_header and sib_header.key:
                    sib_val, next_idx = self._dispatch_header(index, sib_header, child_indent)
                    obj_item[sib_header.key] = sib_val
                    index = next_idx
                    continue
                sib_key_text, sib_val_text = self._split_key_value(sib.content)
                if sib_key_text is None:
                    break
                sib_key = self._parse_key(sib_key_text, sib)
                if sib_val_text == "":
                    grandchild = index + 1
                    if grandchild >= len(self.lines) or self.lines[grandchild].indent <= child_indent:
                        raise ToonSyntaxError("Expected block for sibling key", sib.line_no, 1)
                    sib_val_parsed, next_idx = self._parse_value(grandchild)
                    obj_item[sib_key] = sib_val_parsed
                    index = next_idx
                else:
                    obj_item[sib_key] = self._parse_token(sib_val_text, sib)
                    index += 1
            values.append(obj_item)
            continue

        # Scalar item: '- text' or '- 42'
        value, next_idx = self._parse_inline_value(index, rest)
        values.append(value)
        index = next_idx

    # expected=-1 means no header count declared (called without header context)
    if expected >= 0 and self.strict and len(values) != expected:
        raise ToonSyntaxError(
            f"Array declared {expected} items, found {len(values)}",
            header_line.line_no, 1,
        )
    return values, index

def _dispatch_header_from_rest(
    self, index: int, header: HeaderSpec, line: Line, outer_indent: int
) -> tuple[object, int]:
    """Handle a nested header that appears on a '- ' item line.

    e.g., '  - [2]: 1,2'  or  '  - [2]{id,name}:\\n      1,Ada\\n      2,Bob'
    """
    # Inline primitive: '- [N]: values'
    colon_pos = line.content.rfind(":")
    rest_after_colon = line.content[colon_pos + 1:].strip() if colon_pos != -1 else ""

    if header.fields:
        # Tabular nested: rows are at outer_indent + 4 (hyphen line + 2 extra)
        self._delimiter_stack.append(header.delimiter)
        result, next_idx = self._parse_table_rows(
            index, header.fields, header.length, outer_indent + 2, header.delimiter
        )
        self._delimiter_stack.pop()
        return result, next_idx

    if rest_after_colon:
        return self._parse_inline_array(
            rest_after_colon, header.length, header.delimiter, line, index
        )

    if header.length == 0:
        return [], index + 1

    self._delimiter_stack.append(header.delimiter)
    result, next_idx = self._parse_list_items(
        index + 1, outer_indent + 4, header.length, line
    )
    self._delimiter_stack.pop()
    return result, next_idx

def _parse_object_item_with_header(
    self, index: int, header: HeaderSpec, line: Line, outer_indent: int
) -> tuple[dict, int]:
    """Handle '- key[N]{fields}:' as first field of a list-item object.

    Per spec §10: tabular rows at depth+2, sibling fields at depth+1.
    """
    obj: dict = {}
    # The header's array value
    array_val, next_idx = self._dispatch_header(index, header, outer_indent + 2)
    obj[header.key] = array_val
    # Read sibling fields at outer_indent + 2
    child_indent = outer_indent + 2
    index = next_idx
    while index < len(self.lines):
        sib = self.lines[index]
        if sib.content == _BLANK_SENTINEL:
            if self.strict:
                raise ToonSyntaxError("Blank line inside array item", sib.line_no, 1)
            index += 1
            continue
        if sib.indent != child_indent:
            break
        sib_key_text, sib_val_text = self._split_key_value(sib.content)
        if sib_key_text is None:
            break
        sib_key = self._parse_key(sib_key_text, sib)
        if sib_val_text == "":
            grandchild = index + 1
            sib_val_parsed, next_idx2 = self._parse_value(grandchild)
            obj[sib_key] = sib_val_parsed
            index = next_idx2
        else:
            obj[sib_key] = self._parse_token(sib_val_text, sib)
            index += 1
    return obj, index
```

### 2D-9: Update `_parse_object` to use new header dispatch

- [ ] **Step 9: Update `_parse_object` to call `_dispatch_header`**

Replace the existing `_parse_object` method body:

```python
def _parse_object(self, start: int, indent: int) -> tuple[object, int]:
    result: dict[str, object] = {}
    index = start
    while index < len(self.lines):
        line = self.lines[index]

        # Skip blank sentinels — allowed between object fields even in strict mode
        if line.content == _BLANK_SENTINEL:
            index += 1
            continue

        if line.indent != indent:
            break

        # Check for array header syntax: key[N]{fields}: or key[N]:
        header = self._parse_header_syntax(line.content)
        if header is not None and header.key is not None:
            value, next_idx = self._dispatch_header(index, header, indent)
            result[header.key] = value
            index = next_idx
            continue

        key_text, value_text = self._split_key_value(line.content)
        if key_text is None:
            break
        key = self._parse_key(key_text, line)

        if value_text == "":
            child_index = index + 1
            # Skip blank sentinel between key and its block
            while child_index < len(self.lines) and self.lines[child_index].content == _BLANK_SENTINEL:
                child_index += 1
            if child_index >= len(self.lines):
                raise ToonSyntaxError("Missing block for key", line.line_no, 1)
            child_line = self.lines[child_index]
            if child_line.indent <= indent:
                raise ToonSyntaxError("Expected indented block", child_line.line_no, 1)
            value, next_idx = self._parse_value(child_index)
            index = next_idx
        else:
            value, next_idx = self._parse_inline_value(index, value_text)
            index = next_idx

        result[key] = value
    return result, index
```

### 2D-10: Update `_parse_table_rows` (renamed from `_parse_table_from_header`)

- [ ] **Step 10: Replace `_parse_table_from_header` with `_parse_table_rows`**

```python
def _parse_table_rows(
    self, start: int, fields: list[str], expected_length: int, indent: int, delimiter: str
) -> tuple[list[dict], int]:
    """Parse tabular rows following a key[N]{fields}: header."""
    rows: list[dict] = []
    index = start + 1
    header_line = self.lines[start]

    while index < len(self.lines):
        line = self.lines[index]

        # Blank sentinels inside tabular arrays: error in strict mode
        if line.content == _BLANK_SENTINEL:
            if self.strict:
                raise ToonSyntaxError(
                    "Blank line inside tabular array is not allowed in strict mode",
                    line.line_no, 1,
                )
            index += 1
            continue

        if line.indent <= indent:
            break

        raw_cells = split_row_v3(line.content.strip(), delimiter)
        if self.strict and len(raw_cells) != len(fields):
            raise ToonSyntaxError(
                f"Tabular row has {len(raw_cells)} values, expected {len(fields)}",
                line.line_no, 1,
            )
        row = {k: self._parse_token(cell.strip(), line) for k, cell in zip(fields, raw_cells)}
        rows.append(row)
        index += 1

    if self.strict and len(rows) != expected_length:
        raise ToonSyntaxError(
            f"Table declares {expected_length} rows, found {len(rows)}",
            header_line.line_no, 1,
        )
    return rows, index
```

### 2D-11: Remove `_parse_table` (legacy @table) and clean up

- [ ] **Step 11: Delete `_parse_table`, `_parse_array`, `_split_header` from `ToonParser`**

These methods are no longer used in v3:
- `_parse_table` (legacy @table format — moved to `_parser_v2.py`)
- `_parse_array` (replaced by `_parse_list_items`)
- `_split_header` (replaced by header regex)

Also remove `TABLE_PREFIX = "@table"` constant.

### 2D-12: Update `from_toon` function signature

- [ ] **Step 12: Update `from_toon` in `parser.py`**

```python
def from_toon(
    source: str,
    *,
    strict: bool = True,
    permissive: bool = False,
    indent: int = 2,
    expand_paths: str = "off",
) -> object:
    """Parse a TOON v3 string into a Python object.

    Args:
        source: TOON-formatted string
        strict: If True (default), enforce all v3 validation rules
        permissive: If True, relax identifier and numeric validation
        indent: Expected indentation size in spaces (default: 2); used for strict validation
        expand_paths: "off" (default) or "safe" — expand dotted keys to nested objects
    """
    return ToonParser(
        source, strict=strict, permissive=permissive,
        indent=indent, expand_paths=expand_paths,
    ).parse()
```

- [ ] **Step 13: Run all existing tests**

```
pytest tests/ -x -q
```

Expected: Most tests pass. Some may fail due to the `_parse_value` dispatch needing updates — fix any failures before proceeding.

- [ ] **Step 14: Fix `_parse_value` to use new header dispatch**

```python
def _parse_value(self, index: int) -> tuple[object, int]:
    line = self.lines[index]
    if line.content == _BLANK_SENTINEL:
        # Should not happen — callers skip sentinels before calling _parse_value
        raise ToonSyntaxError("Unexpected blank line", line.line_no, 1)
    header = self._parse_header_syntax(line.content)
    if header is not None and header.key is not None:
        return self._dispatch_header(index, header, line.indent)
    if self._is_array_line(line.content):
        # Shouldn't reach here at root — but handle for nested contexts
        return self._parse_list_items(index, line.indent, expected=-1, header_line=line)
    key, value = self._split_key_value(line.content)
    if key is not None:
        return self._parse_object(index, line.indent)
    return self._parse_root_primitive(line), index + 1
```

Note: pass `expected=-1` to `_parse_list_items` to skip count validation when called without a header.

- [ ] **Step 15: Run all existing tests again**

```
pytest tests/ -x -q
```

Expected: All pre-existing tests pass.

- [ ] **Step 16: Commit parser changes**

```
git add toonpy/parser.py
git commit -m "feat(parser): implement TOON v3.0 parser with delimiter stack, root forms, inline arrays, blank-line strict mode"
```

---

## Task 2E: Write `test_spec_fixtures.py`

**Files:**
- Create: `tests/test_spec_fixtures.py`

This test file runs against the cached fixtures from Task 1B. It must run even if the spec repo is unreachable.

- [ ] **Step 1: Write the fixture test file**

Create `tests/test_spec_fixtures.py`:

```python
"""Parametric test runner for TOON spec v3.0 official fixtures.

Loads JSON fixtures from tests/fixtures/{decode,encode}/*.json.
Each fixture file contains a list of test cases with:
  - name: str
  - input: str | dict (TOON text for decode, Python object for encode)
  - expected: any Python value (None if shouldError)
  - options: dict | absent — passed as kwargs to from_toon / to_toon
  - shouldError: bool | absent — if true, expect ToonSyntaxError
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from toonpy import from_toon, to_toon
from toonpy.errors import ToonSyntaxError

FIXTURES_DIR = Path(__file__).parent / "fixtures"

DECODE_FIXTURES = [
    "primitives", "numbers", "objects", "arrays-primitive", "arrays-tabular",
    "arrays-nested", "delimiters", "whitespace", "root-form",
    "validation-errors", "indentation-errors", "blank-lines", "path-expansion",
]
ENCODE_FIXTURES = [
    "primitives", "objects", "arrays-primitive", "arrays-tabular",
    "arrays-nested", "arrays-objects", "delimiters", "whitespace",
    "options", "key-folding",
]


def _load_fixture(category: str, name: str) -> list[dict]:
    path = FIXTURES_DIR / category / f"{name}.json"
    if not path.exists():
        pytest.skip(f"Fixture not found: {path} — run tests/fixtures/download_fixtures.py")
    return json.loads(path.read_text(encoding="utf-8"))["tests"]


def _decode_params() -> list[tuple[str, dict]]:
    params = []
    for name in DECODE_FIXTURES:
        try:
            cases = _load_fixture("decode", name)
        except Exception:
            continue
        for case in cases:
            params.append((f"{name}::{case['name']}", case))
    return params


def _encode_params() -> list[tuple[str, dict]]:
    params = []
    for name in ENCODE_FIXTURES:
        try:
            cases = _load_fixture("encode", name)
        except Exception:
            continue
        for case in cases:
            params.append((f"{name}::{case['name']}", case))
    return params


def _options_to_kwargs(options: dict) -> dict[str, Any]:
    """Convert fixture options dict to from_toon / to_toon kwargs."""
    mapping = {
        "strict": "strict",
        "indent": "indent",
        "expandPaths": "expand_paths",
        "keyFolding": "key_folding",
        "flattenDepth": "flatten_depth",
        "delimiter": "delimiter",
    }
    return {mapping[k]: v for k, v in options.items() if k in mapping}


@pytest.mark.parametrize("name,case", _decode_params(), ids=[p[0] for p in _decode_params()])
def test_decode_fixture(name: str, case: dict) -> None:
    source: str = case["input"]
    options = _options_to_kwargs(case.get("options", {}))
    should_error: bool = case.get("shouldError", False)

    if should_error:
        with pytest.raises(ToonSyntaxError, match=""):
            from_toon(source, **options)
        return

    result = from_toon(source, **options)
    assert result == case["expected"], (
        f"\nTest: {name}\nInput: {source!r}\nExpected: {case['expected']!r}\nGot: {result!r}"
    )


@pytest.mark.parametrize("name,case", _encode_params(), ids=[p[0] for p in _encode_params()])
def test_encode_fixture(name: str, case: dict) -> None:
    obj = case["input"]
    options = _options_to_kwargs(case.get("options", {}))
    should_error: bool = case.get("shouldError", False)
    expected: str = case.get("expected", "")

    if should_error:
        with pytest.raises(Exception):
            to_toon(obj, **options)
        return

    result = to_toon(obj, **options).strip()
    assert result == expected.strip(), (
        f"\nTest: {name}\nInput: {obj!r}\nExpected:\n{expected}\nGot:\n{result}"
    )
```

- [ ] **Step 2: Run fixture tests (expect many failures — that's expected at this stage)**

```
pytest tests/test_spec_fixtures.py -v --tb=no -q 2>&1 | head -50
```

Note the failures — they document what's still left to implement.

- [ ] **Step 3: Commit**

```
git add tests/test_spec_fixtures.py
git commit -m "test: add parametric spec fixture test runner"
```

---

## Task 2F: Extend serializer.py

**Files:**
- Modify: `toonpy/serializer.py`

### 2F-1: Add primitive inline array support

- [ ] **Step 1: Add `_maybe_primitive_inline` method**

Add to `ToonSerializer`:

```python
def _maybe_primitive_inline(self, seq: Sequence[Any]) -> bool:
    """Return True if seq should be serialized as an inline primitive array.

    Conditions: non-empty, all items are scalars (not Mapping, not Sequence
    except str/bytes), and none contain newlines.
    """
    if not seq:
        return False
    for item in seq:
        if isinstance(item, Mapping):
            return False
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            return False
        if isinstance(item, str) and "\n" in item:
            return False
    return True
```

- [ ] **Step 2: Update `_write_object` to emit inline array for primitive sequences**

In `_write_object`, before the tabular check, add:

```python
if (isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))
        and self._maybe_primitive_inline(value)):
    delim_char = {"comma": ",", "tab": "\t", "pipe": "|"}.get(self.delimiter, ",")
    cells = delim_char.join(self._format_cell(v) for v in value)
    bracket = {"comma": "", "tab": "\t", "pipe": "|"}.get(self.delimiter, "")
    lines.append(indent_str + f"{key_repr}[{len(value)}]{bracket}: {cells}")
    continue
```

- [ ] **Step 3: Update `_write_array` to emit inline for primitive sequences at root**

At the top of `_write_array`, before the tabular check:

```python
if self._maybe_primitive_inline(seq):
    delim_char = {"comma": ",", "tab": "\t", "pipe": "|"}.get(self.delimiter, ",")
    bracket = {"comma": "", "tab": "\t", "pipe": "|"}.get(self.delimiter, "")
    cells = delim_char.join(self._format_cell(v) for v in seq)
    indent_str = self._get_indent(level)
    lines.append(indent_str + f"[{len(seq)}]{bracket}: {cells}")
    return
```

### 2F-2: Update `_write_table_as_key` for delimiter support

- [ ] **Step 4: Update `ToonSerializer.__init__` to accept new options**

```python
def __init__(
    self,
    *,
    indent: int = 2,
    mode: mode_type = "auto",
    delimiter: str = "comma",
    key_folding: str = "off",
    flatten_depth: float = float("inf"),
) -> None:
    self.indent = indent
    self.mode = mode
    self.delimiter = delimiter
    self.key_folding = key_folding
    self.flatten_depth = flatten_depth
    self._indent_cache: dict[int, str] = {}
    self._max_cached_indent = 20
    # Pre-compute delimiter character for performance
    self._delim_char = {"comma": ",", "tab": "\t", "pipe": "|"}.get(delimiter, ",")
    self._delim_bracket = {"comma": "", "tab": "\t", "pipe": "|"}.get(delimiter, "")
```

- [ ] **Step 5: Update `_write_table_as_key` to use delimiter**

```python
def _write_table_as_key(self, key, seq, schema, level, lines):
    key_formatted = format_key(key)
    fields = self._delim_char.join(format_key(k) for k in schema.keys)
    header = f"{key_formatted}[{len(seq)}]{self._delim_bracket}{{{fields}}}:"
    indent_str = self._get_indent(level)
    lines.append(indent_str + header)
    inner_indent = self._get_indent(level + 1)
    for row in seq:
        cells = self._delim_char.join(self._format_cell(row.get(k)) for k in schema.keys)
        lines.append(inner_indent + cells)
```

### 2F-3: Add key folding

- [ ] **Step 6: Add `_try_fold` method**

```python
def _try_fold(
    self,
    key: str,
    value: Any,
    siblings: Mapping,
    depth_remaining: float,
) -> tuple[str, Any] | None:
    """Try to fold 'key → {single_key: child}' into 'key.single_key'.

    Returns (folded_key_str, terminal_value) or None if folding is not safe.
    depth_remaining limits how many dots can be added (flattenDepth).
    """
    if self.key_folding == "off" or depth_remaining <= 0:
        return None
    if not isinstance(value, Mapping) or len(value) != 1:
        return None
    child_key = next(iter(value))
    child_val = value[child_key]
    # child_key must be a valid identifier segment (no hyphens, no dots)
    if not is_identifier_segment(child_key):
        return None
    folded = f"{key}.{child_key}"
    # No collision with sibling literal keys
    if folded in siblings:
        return None
    # Recurse (consume one depth unit)
    deeper = self._try_fold(child_key, child_val, {}, depth_remaining - 1)
    if deeper is not None:
        deeper_key, deeper_val = deeper
        return f"{key}.{deeper_key}", deeper_val
    return folded, child_val
```

Add `from .utils import is_identifier_segment` at the top of `serializer.py`.

- [ ] **Step 7: Apply key folding in `_write_object`**

In `_write_object`, at the start of the key loop, add:

```python
if self.key_folding == "safe":
    folded = self._try_fold(str(key), value, mapping, self.flatten_depth)
    if folded is not None:
        folded_key_str, terminal_value = folded
        key_repr = format_key(folded_key_str)
        value = terminal_value
        # re-check if terminal_value is primitive/inline/tabular below
```

### 2F-4: Fix numeric canonicalization in `_format_scalar`

- [ ] **Step 8: Fix float formatting**

In `_format_scalar`, replace the `isinstance(value, (int, float))` branch:

```python
if isinstance(value, (int, float)) and not force_string:
    if isinstance(value, float):
        # Normalize -0.0 → 0
        if value == 0.0:
            return "0"
        # Return int representation if it's a whole number
        int_val = int(value)
        if int_val == value:
            return str(int_val)
        return repr(value)
    return str(value)
```

- [ ] **Step 9: Update `to_toon` function in `serializer.py`**

```python
def to_toon(
    obj: Any,
    *,
    indent: int = 2,
    mode: mode_type = "auto",
    delimiter: str = "comma",
    key_folding: str = "off",
    flatten_depth: float = float("inf"),
) -> str:
    return ToonSerializer(
        indent=indent, mode=mode, delimiter=delimiter,
        key_folding=key_folding, flatten_depth=flatten_depth,
    ).dumps(obj)
```

- [ ] **Step 10: Run all tests**

```
pytest tests/ -x -q
```

Fix any failures before committing.

- [ ] **Step 11: Commit serializer changes**

```
git add toonpy/serializer.py
git commit -m "feat(serializer): add primitive inline arrays, key folding, delimiter option, numeric canonicalization"
```

---

## Task 3G: Implement Path Expansion

**Files:**
- Create: `toonpy/_path_expansion.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_parser.py`:

```python
def test_expand_paths_basic():
    from toonpy.parser import from_toon
    result = from_toon("a.b.c: 1", expand_paths="safe")
    assert result == {"a": {"b": {"c": 1}}}

def test_expand_paths_off_by_default():
    from toonpy.parser import from_toon
    result = from_toon("a.b.c: 1")
    assert result == {"a.b.c": 1}

def test_expand_paths_conflict_strict():
    from toonpy.parser import from_toon
    from toonpy.errors import ToonSyntaxError
    with pytest.raises(ToonSyntaxError):
        from_toon("a.b: 1\na: 2", expand_paths="safe", strict=True)

def test_expand_paths_lww():
    from toonpy.parser import from_toon
    result = from_toon("a.b: 1\na: 2", expand_paths="safe", strict=False)
    assert result == {"a": 2}

def test_expand_paths_quoted_keys_preserved():
    from toonpy.parser import from_toon
    result = from_toon('"c.d": 2', expand_paths="safe")
    assert result == {"c.d": 2}
```

Run: `pytest tests/test_parser.py::test_expand_paths_basic -v`
Expected: FAIL (module not found)

- [ ] **Step 2: Create `toonpy/_path_expansion.py`**

```python
"""Path expansion post-processing for TOON v3 expandPaths='safe' option."""
from __future__ import annotations

from .errors import ToonSyntaxError
from .utils import is_identifier_segment


def expand_paths(obj: dict, *, strict: bool = True) -> dict:
    """Expand dotted keys in obj to nested objects with deep-merge.

    Only expands keys where:
    - The key is not quoted (we receive it as a plain str from the parser)
    - All dot-separated segments are IdentifierSegments
    - No collision with existing sibling keys

    Quoted keys were parsed without modification and will not contain dots
    from path expansion — they remain as literal keys.

    Args:
        obj: Parsed TOON object (root dict)
        strict: If True, raise ToonSyntaxError on path conflicts.
                If False, last-write-wins (document order).

    Returns:
        New dict with paths expanded and deep-merged.
    """
    result: dict = {}
    for key, value in obj.items():
        segments = _try_split(key)
        if segments is None:
            # Not expandable — insert as literal
            _merge_into(result, [key], value, strict=strict, original_key=key)
        else:
            _merge_into(result, segments, value, strict=strict, original_key=key)
    return result


def _try_split(key: str) -> list[str] | None:
    """Return dot-split segments if all are valid IdentifierSegments, else None."""
    if "." not in key:
        return None
    parts = key.split(".")
    if all(is_identifier_segment(p) for p in parts):
        return parts
    return None


def _merge_into(target: dict, segments: list[str], value: object, *, strict: bool, original_key: str) -> None:
    """Deep-merge value at the path described by segments into target."""
    key = segments[0]
    if len(segments) == 1:
        if key in target:
            if strict:
                raise ToonSyntaxError(
                    f"Path expansion conflict: key '{original_key}' conflicts with existing key '{key}'"
                )
            # LWW: overwrite
        target[key] = value
        return

    # Need to recurse — target[key] must be a dict
    if key in target:
        existing = target[key]
        if not isinstance(existing, dict):
            if strict:
                raise ToonSyntaxError(
                    f"Path expansion conflict: '{key}' exists as non-object, cannot expand '{original_key}'"
                )
            # LWW: create new dict, overwrite
            target[key] = {}
    else:
        target[key] = {}

    _merge_into(target[key], segments[1:], value, strict=strict, original_key=original_key)
```

- [ ] **Step 3: Run the new tests**

```
pytest tests/test_parser.py -k "expand_paths" -v
```

Expected: All 5 tests PASS.

- [ ] **Step 4: Commit**

```
git add toonpy/_path_expansion.py tests/test_parser.py
git commit -m "feat: add path expansion (expandPaths=safe) post-processing"
```

---

## Task 3H: Update Public API (`api.py`)

**Files:**
- Modify: `toonpy/api.py`
- Modify: `toonpy/__init__.py` (if exports need updating)

- [ ] **Step 1: Update `from_toon` in `api.py`**

Replace the current `from_toon` function:

```python
def from_toon(
    source: str,
    *,
    strict: bool = True,
    expand_paths: Literal["off", "safe"] = "off",
    spec: Literal["v2", "v3"] = "v3",
    permissive: bool = False,
    indent: int = 2,
) -> Any:
    """Parse a TOON string into a Python object.

    Args:
        source: TOON-formatted string to parse
        strict: Enforce strict v3 validation (default: True)
        expand_paths: "off" (default) or "safe" — expand dotted keys
        spec: "v3" (default) or "v2" — which spec version to use
        permissive: Relax identifier/numeric validation (v2 compat)
        indent: Expected indentation size for strict validation (default: 2)

    Returns:
        Python object (dict, list, or scalar value)

    Raises:
        ToonSyntaxError: If the TOON string is malformed
    """
    if spec == "v2":
        from .._parser_v2 import from_toon as _from_toon_v2
        return _from_toon_v2(source, permissive=permissive)
    return _from_toon(
        source,
        strict=strict,
        permissive=permissive,
        indent=indent,
        expand_paths=expand_paths,
    )
```

- [ ] **Step 2: Update `to_toon` in `api.py`**

Replace the current `to_toon` function:

```python
def to_toon(
    obj: Any,
    *,
    indent: int = 2,
    mode: Literal["auto", "compact", "readable"] = "auto",
    delimiter: Literal["comma", "tab", "pipe"] = "comma",
    key_folding: Literal["off", "safe"] = "off",
    flatten_depth: int | float = float("inf"),
) -> str:
    """Convert a Python object to TOON format string.

    Args:
        obj: Python object compatible with JSON model (dict, list, scalar)
        indent: Spaces per indentation level (default: 2)
        mode: "auto" (default), "compact", or "readable"
        delimiter: "comma" (default), "tab", or "pipe"
        key_folding: "off" (default) or "safe" — fold single-key chains to dotted paths
        flatten_depth: Max depth for key folding (default: inf)

    Returns:
        TOON-formatted string
    """
    return _to_toon(
        obj,
        indent=indent,
        mode=mode,
        delimiter=delimiter,
        key_folding=key_folding,
        flatten_depth=flatten_depth,
    )
```

- [ ] **Step 3: Update `validate_toon` to use new kwargs**

```python
def validate_toon(source: str, *, strict: bool = True) -> tuple[bool, List[ValidationError]]:
    try:
        _from_toon(source, strict=strict)
    except ToonSyntaxError as exc:
        return False, [ValidationError(str(exc), exc.line, exc.column)]
    return True, []
```

- [ ] **Step 4: Run all tests**

```
pytest tests/ -x -q
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```
git add toonpy/api.py
git commit -m "feat(api): update from_toon and to_toon with v3 options; add spec=v2 backward-compat dispatch"
```

---

## Task 4I: Run Full Test Suite

**Files:** (no file changes — validation only)

- [ ] **Step 1: Run all tests with verbose output**

```
pytest tests/ -v --tb=short 2>&1 | tee test_results.txt
```

- [ ] **Step 2: Check spec fixture pass rate**

```
pytest tests/test_spec_fixtures.py -v --tb=short -q 2>&1 | tail -20
```

Expected: All spec fixture tests PASS. If any fail, fix the implementation before proceeding.

- [ ] **Step 3: Check no regressions in existing tests**

```
pytest tests/test_parser.py tests/test_serializer.py tests/test_api.py tests/test_cli.py -v --tb=short
```

Expected: All pass.

- [ ] **Step 4: If any spec fixture fails — diagnose and fix**

For each failing test, look at the fixture `name` and `input`. The test name tells you which fixture file and case. Fix in the relevant parser/serializer method. Re-run after each fix.

---

## Task 4J: Run Post-Implementation Benchmarks

**Files:**
- Create: `benchmark_after.txt`

- [ ] **Step 1: Run all benchmarks and capture output**

```
python benchmark_optimizations.py > benchmark_after.txt 2>&1
python benchmark_serializer.py >> benchmark_after.txt 2>&1
python benchmark_parallel.py >> benchmark_after.txt 2>&1
```

- [ ] **Step 2: Compare against baseline**

```
python -c "
import re

def extract_times(filename):
    times = {}
    with open(filename) as f:
        content = f.read()
    # Look for lines with microseconds or MB/s
    for line in content.splitlines():
        if 'μs' in line or 'MB/s' in line or 'ms' in line:
            print(line.strip())
    return times

print('=== BASELINE ===')
extract_times('benchmark_baseline.txt')
print()
print('=== AFTER v3 ===')
extract_times('benchmark_after.txt')
"
```

- [ ] **Step 3: Verify regression threshold**

Parse throughput on comma-only documents must not regress more than 2% from baseline. If it does, profile with:

```
python -m cProfile -s cumtime benchmark_optimizations.py 2>&1 | head -30
```

Fix the bottleneck before proceeding.

- [ ] **Step 4: Commit benchmark results**

```
git add benchmark_after.txt
git commit -m "chore: capture post-v3 benchmark results"
```

---

## Task 4K: Version Bump and Documentation

**Files:**
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`
- Modify: `docs/spec_summary.md`
- Modify: `docs/assumptions.md`

- [ ] **Step 1: Bump version in `pyproject.toml`**

Change line 7:
```toml
version = "0.6.0"
```

- [ ] **Step 2: Update `docs/spec_summary.md`**

Change the title from `# TOON SPEC v2.0 Summary` to `# TOON SPEC v3.0 Summary` and update the description to reflect v3 features (multiple delimiters, inline arrays, root forms, key folding, path expansion).

Add a new section after the existing content:

```markdown
## v3.0 Additions

- **Multiple delimiters** — headers may declare tab (`[N\t]`) or pipe (`[N|]`) as delimiters; scoped to their block
- **Primitive inline arrays** — `key[N]: v1,v2,v3` for arrays of scalars
- **Root forms** — empty document → `{}`, `[N]...` at column 0 → root array, bare line → root primitive
- **Key folding (encoder)** — `key_folding="safe"` collapses single-key chains: `{"a": {"b": 1}}` → `a.b: 1`
- **Path expansion (decoder)** — `expand_paths="safe"` expands `a.b.c: 1` → `{"a": {"b": {"c": 1}}}`
- **Strict blank-line detection** — blank lines inside array blocks raise ToonSyntaxError in strict mode
- **Indentation validation** — strict mode enforces indentation multiples
- **Numeric normalization** — exponent forms evaluated, -0 → 0
```

- [ ] **Step 3: Update `docs/assumptions.md`**

Replace the spec version reference from v2.0 to v3.0 and update the mode selection section:

```markdown
## Mode Selection

- `from_toon(..., strict=True)` (default) enforces all v3 invariants.
- `from_toon(..., strict=False)` relaxes blank-line and indentation checks.
- `from_toon(..., permissive=True)` additionally relaxes identifier safety and numeric precision.
- `from_toon(..., spec="v2")` uses the exact v2.0 parser, including `@table` syntax.
- `validate_toon(source, strict=...)` exposes the same behavior.
```

- [ ] **Step 4: Add CHANGELOG entry**

Prepend to `CHANGELOG.md`:

```markdown
## [0.6.0] — 2026-05-16

### Added
- Full TOON spec v3.0 compliance
- Multiple delimiters: tab and pipe in array headers, with delimiter scoping
- Primitive inline arrays: `key[N]: v1,v2,v3`
- Root form disambiguation: empty doc → `{}`, `[N]...` → root array, bare line → root primitive
- `expand_paths="safe"` decoder option for dotted-key path expansion with deep-merge
- `key_folding="safe"` encoder option with `flatten_depth` control
- `delimiter="tab"|"pipe"` encoder option
- Strict mode blank-line detection inside array blocks
- Strict mode indentation-multiple validation with configurable `indent` size
- Exponent notation in numbers: `1e6` → `1000000`
- `spec="v2"` backward-compat opt-in to exact v2.0 parser

### Removed
- `@table` legacy syntax (not part of spec); use `spec="v2"` for backward compat

### Fixed
- `-0` and `-0.0` now normalize to `0`
- `1e6`-style numbers now return `int` (`1000000`) not `float`
- Leading zeros (e.g., `05`) now correctly parsed as strings
```

- [ ] **Step 5: Final full test run**

```
pytest tests/ -q
```

Expected: All tests pass, 0 failures.

- [ ] **Step 6: Final commit**

```
git add pyproject.toml CHANGELOG.md docs/spec_summary.md docs/assumptions.md
git commit -m "release: bump to v0.6.0 with full TOON spec v3.0 support"
```

---

## Parallelization Map

Tasks with no dependencies between them can (and should) be dispatched to parallel subagents:

```
Task 0 (baseline benchmark) — MUST run first, no parallel

Phase 1 — run in parallel after Task 0:
  Task 1A  (copy _parser_v2.py)
  Task 1B  (download fixtures)
  Task 1C  (extend utils.py)

Phase 2 — run in parallel after Phase 1:
  Task 2D  (rewrite parser.py)    — depends on 1A (for _parser_v2 reference) + 1C (utils imports)
  Task 2E  (write test fixture runner) — depends on 1B (fixture files)
  Task 2F  (extend serializer.py) — depends on 1C (is_identifier_segment import)

Phase 3 — run in parallel after Phase 2:
  Task 3G  (path expansion module)  — depends on 2D (parser calls it)
  Task 3H  (update api.py)          — depends on 2D + 2F (new kwargs)

Phase 4 — sequential after Phase 3:
  Task 4I  (run full test suite)
  Task 4J  (run benchmarks)
  Task 4K  (version bump + docs)
```
