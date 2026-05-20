# 🔄 toonpy

[![PyPI version](https://badge.fury.io/py/toontools.svg)](https://badge.fury.io/py/toontools)
[![Latest Release](https://img.shields.io/github/v/release/shinjidev/toonpy)](https://github.com/shinjidev/toonpy/releases)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI downloads](https://img.shields.io/pypi/dm/toontools.svg)](https://pypi.org/project/toontools/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/shinjidev/toonpy/actions)
[![Coverage](https://img.shields.io/badge/coverage-90%25-green.svg)](https://github.com/shinjidev/toonpy)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/shinjidev)

A production-grade Python library and CLI that converts data between JSON, YAML, TOML, and TOON (Token-Oriented Object Notation) while fully conforming to **TOON SPEC v3.0**. Perfect for developers and data engineers who need efficient, token-optimized data serialization.

**📦 Current Version: 1.0.0** — Full TOON spec v3.0 support with multiple delimiters, key folding, path expansion, and significant performance gains. See [What's New in v1.0.0](#-whats-new-in-v100).

**✅ Full TOON SPEC v3.0 Compliance** — 358/358 official spec fixtures pass. TOON v2 documents are supported via the `spec="v2"` option.

> **Upgrading from v0.5.x?** v3 is fully backward-compatible for most documents. See [Backward Compatibility](#-backward-compatibility) for details.
>
> **v2 documentation:** See [README_v2.md](README_v2.md) for the legacy v2-focused reference.

---

## 🚀 What's New in v1.0.0

**TOON SPEC v3.0 Release** (May 2026) — Full implementation of TOON spec v3.0 with major new features and the largest performance jump yet.

### New Language Features

| Feature | Description |
|---------|-------------|
| **Multiple delimiters** | Tab (`\t`) and pipe (`\|`) in addition to comma for tabular and inline arrays |
| **Primitive inline arrays** | `key[N]: v1,v2,v3` — compact single-line form for scalar arrays |
| **Root form disambiguation** | Root arrays (`[N]:`), root objects, and root primitives all parsed correctly |
| **Blank-line sentinels** | Blank lines inside structures raise errors in strict mode |
| **v3 key rules** | Unquoted keys are pure identifiers (`[A-Za-z_][A-Za-z0-9_]*`); hyphens always quoted |

### New Serializer Options

| Option | Values | Description |
|--------|--------|-------------|
| `delimiter` | `"comma"` (default), `"tab"`, `"pipe"` | Row separator for tabular arrays |
| `key_folding` | `"off"` (default), `"safe"`, `"lax"` | Collapse single-key chains into dotted paths |
| `flatten_depth` | integer (default: `inf`) | Maximum nesting depth for key folding |

### New Parser Options

| Option | Values | Description |
|--------|--------|-------------|
| `strict` | `True` (default) | Enforce all v3 invariants |
| `permissive` | `False` (default) | Relax unquoted-string-with-spaces check |
| `expand_paths` | `"off"` (default), `"safe"`, `"lax"` | Expand dotted keys into nested objects |
| `spec` | `"v3"` (default), `"v2"` | Route to v2 parser for legacy documents |

### Performance Gains vs v0.5.x baseline

Parser throughput more than doubled vs the previous release; serializer gains range from +38% to +83%. See [Performance](#-performance).

**Previous Releases:** [v0.5.0](README_v2.md#-whats-new-in-v050) (TOML support) · [v0.4.0](README_v2.md) (YAML support) · [CHANGELOG.md](CHANGELOG.md) for full history.

---

## ✨ Features

### Core

- **Lossless round-trip** — all JSON data types preserved across TOON ↔ JSON ↔ YAML ↔ TOML
- **TOON SPEC v3.0** — full compliance, 358/358 spec fixtures pass
- **Three delimiters** — comma (default), tab, pipe for tabular and inline arrays
- **Key folding** — collapse single-key chains into dotted paths (`a.b.c: v`)
- **Path expansion** — expand dotted keys into nested objects on parse
- **Strict / permissive modes** — configurable conformance level
- **Backward compatibility** — `spec="v2"` routes to the pre-v3 parser

### Parser

- LL(1) parser with indentation tracking
- Comment support — inline (`#`, `//`) and block (`/* */`, nestable)
- Error reporting with line and column numbers
- Root form disambiguation — objects, arrays, or single primitives at root level
- Blank-line sentinels in strict mode

### Serializer

- Automatic tabular detection — emits `key[N]{fields}:` when it saves characters
- Primitive inline arrays — emits `key[N]: v1,v2,v3` for scalar-only arrays
- Key folding — produces dotted paths for deeply nested single-key chains
- Three delimiter modes — comma, tab, pipe
- Configurable indentation and serialization modes (`auto`, `compact`, `readable`)

### Tooling

- **CLI** (`toonpy`) for file conversion and validation
- **Streaming helpers** for large files
- **YAML support** (optional, requires PyYAML)
- **TOML support** (optional, requires tomli/tomli-w)
- **Token savings estimation** (optional, requires tiktoken)

---

## 📦 Installation

```bash
pip install toontools
```

With optional extras:

```bash
pip install toontools[yaml]          # YAML ↔ TOON support (requires PyYAML)
pip install toontools[toml]          # TOML ↔ TOON support (requires tomli, tomli-w)
pip install toontools[tests]         # Testing dependencies
pip install toontools[examples]      # tiktoken for token counting
```

**Requirements:** Python 3.9+, zero core dependencies.

---

## 🚀 Quick Start

```python
import toonpy

data = {
    "crew": [
        {"id": 1, "name": "Luz", "role": "Light glyph"},
        {"id": 2, "name": "Amity", "role": "Abomination strategist"},
    ],
    "active": True,
    "ship": {"name": "Owl House", "location": "Bonesborough"},
}

toon = toonpy.to_toon(data)
print(toon)
# crew[2]{id,name,role}:
#   1,Luz,"Light glyph"
#   2,Amity,"Abomination strategist"
# active: true
# ship:
#   name: "Owl House"
#   location: Bonesborough

parsed = toonpy.from_toon(toon)
assert parsed == data  # perfect round-trip
```

---

## 📖 API Reference

### `to_toon(obj, *, indent=2, mode="auto", delimiter="comma", key_folding="off", flatten_depth=inf) -> str`

Convert a Python object to a TOON string.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `obj` | Any | — | Python object (JSON-compatible) |
| `indent` | int | `2` | Spaces per indentation level |
| `mode` | str | `"auto"` | `"auto"` · `"compact"` · `"readable"` |
| `delimiter` | str | `"comma"` | Row separator: `"comma"` · `"tab"` · `"pipe"` |
| `key_folding` | str | `"off"` | `"off"` · `"safe"` · `"lax"` — collapse single-key chains into dotted paths |
| `flatten_depth` | int | `inf` | Max nesting depth for key folding |

```python
from toonpy import to_toon

# Default (comma delimiter, no key folding)
toon = to_toon(data)

# Tab-delimited tabular arrays
toon = to_toon(data, delimiter="tab")

# Pipe-delimited + key folding
toon = to_toon(data, delimiter="pipe", key_folding="safe")

# Compact output, no tabular promotion
toon = to_toon(data, mode="compact")
```

---

### `from_toon(source, *, strict=True, permissive=False, indent=2, expand_paths="off", delimiter="comma", spec="v3") -> Any`

Parse a TOON string into a Python object.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | str | — | TOON-formatted string |
| `strict` | bool | `True` | Enforce all v3 invariants (blank-line sentinels, row count, etc.) |
| `permissive` | bool | `False` | Allow unquoted strings with spaces |
| `expand_paths` | str | `"off"` | `"off"` · `"safe"` · `"lax"` — expand dotted keys into nested objects |
| `spec` | str | `"v3"` | `"v3"` (default) or `"v2"` to use the legacy parser |

```python
from toonpy import from_toon

# Default strict v3 parsing
data = from_toon(toon)

# Permissive: allow unquoted strings with spaces
data = from_toon(toon, permissive=True)

# Expand dotted keys: "a.b.c: 1" → {"a": {"b": {"c": 1}}}
data = from_toon(toon, expand_paths="safe")

# Parse a v2 document
data = from_toon(legacy_toon, spec="v2")
```

**Raises:** `ToonSyntaxError` with `line` and `column` attributes on malformed input.

---

### `validate_toon(source, *, strict=True) -> tuple[bool, list[ValidationError]]`

```python
from toonpy import validate_toon

ok, errors = validate_toon(toon_text)
for e in errors:
    print(f"line {e.line}: {e.message}")
```

---

### `suggest_tabular(obj) -> TabularSuggestion`

```python
from toonpy import suggest_tabular

s = suggest_tabular(rows)
if s.use_tabular:
    print(f"Tabular saves ~{s.estimated_savings} chars. Fields: {s.keys}")
```

---

### `stream_to_toon(fin, fout, *, chunk_size=65536, indent=2, mode="auto") -> int`

Stream JSON from an input file to TOON output. Returns bytes written.

```python
from toonpy import stream_to_toon

with open("large.json") as fin, open("large.toon", "w") as fout:
    stream_to_toon(fin, fout)
```

---

### YAML Functions (optional — requires `pip install toontools[yaml]`)

```python
from toonpy import to_toon_from_yaml, to_yaml_from_toon, stream_yaml_to_toon

toon = to_toon_from_yaml(yaml_str, mode="auto")
yaml = to_yaml_from_toon(toon_str)

with open("data.yaml") as fin, open("out.toon", "w") as fout:
    stream_yaml_to_toon(fin, fout)
```

---

### TOML Functions (optional — requires `pip install toontools[toml]`)

```python
from toonpy import to_toon_from_toml, to_toml_from_toon, stream_toml_to_toon

toon = to_toon_from_toml(toml_str, mode="auto")
toml = to_toml_from_toon(toon_str)

with open("config.toml") as fin, open("out.toon", "w") as fout:
    stream_toml_to_toon(fin, fout)
```

---

## 🆕 v3.0 Features in Depth

### Multiple Delimiters

Tab and pipe are available as alternatives to the default comma; choose based on your data and output context.

```
# comma (default)
users[3]{id,name,role}:
  1,Luz,Human
  2,Eda,Witch
  3,King,Titan

# pipe
users[3|]{id|name|role}:
  1|Luz|Human
  2|Eda|Witch
  3|King|Titan

# tab
users[3\t]{id\tname\trole}:
  1\tLuz\tHuman
  2\tEda\tWitch
  3\tKing\tTitan
```

---

### Primitive Inline Arrays

Compact single-line form for scalar-only arrays; the serializer emits this automatically.

```
tags[3]: python,serialization,toon
scores[5]: 98,87,92,76,100
```

---

### Key Folding (Serializer)

```python
data = {"config": {"server": {"host": "localhost"}}}

to_toon(data, key_folding="safe")
# config.server.host: localhost

to_toon(data, key_folding="safe", flatten_depth=1)
# config:
#   server.host: localhost
```

- `"safe"` — only folds plain identifier segments; refuses ambiguous cases
- `"lax"` — folds any segment, last-write-wins on conflicts

---

### Path Expansion (Parser)

```python
toon = "config.server.host: localhost"

from_toon(toon)
# {"config.server.host": "localhost"}   # default: no expansion

from_toon(toon, expand_paths="safe")
# {"config": {"server": {"host": "localhost"}}}
```

- `"safe"` — only expands plain identifiers; conflicts raise `ToonSyntaxError`
- `"lax"` — expands all dotted keys; last-write-wins on conflicts

---

### Strict Mode

In strict mode (default), these raise `ToonSyntaxError`:

- Blank lines inside structures
- Row count ≠ declared N in tabular arrays
- Delimiter mismatch between header bracket and row separator
- Mixed indentation (tabs and spaces)

Pass `strict=False` or `permissive=True` to relax these checks.

---

## ↩️ Backward Compatibility

### v3 is the default

`from_toon()` and `to_toon()` now default to TOON spec v3.0.

### Most v2 documents parse without changes

The only v2 construct that will fail in v3 strict mode is `@table` (the pipe-bordered table format). All other v2 syntax is valid v3.

### Opt in to the v2 parser

```python
# Parse a document using the pre-v3 parser
data = from_toon(legacy_toon, spec="v2")

# Serialize using v2 rules
toon = to_toon(data, spec="v2")
```

The v2 parser (`toonpy._parser_v2`) is a verbatim copy of the pre-v3 parser and is fully maintained.

### API changes

| Old (≤0.5.x) | New (1.0.0+) | Notes |
|---|---|---|
| `from_toon(src, mode="strict")` | `from_toon(src, strict=True)` | `mode` kwarg removed; use `strict`/`permissive` |
| `from_toon(src, mode="permissive")` | `from_toon(src, permissive=True)` | |
| `to_toon(obj, mode="auto")` | `to_toon(obj, mode="auto")` | unchanged |

---

## 🖥️ CLI Reference

```bash
# JSON → TOON
toonpy to --in data.json --out data.toon --mode auto --indent 2

# TOON → JSON
toonpy from --in data.toon --out data.json

# Permissive parsing
toonpy from --in data.toon --out data.json --permissive

# Use v2 parser for legacy documents
toonpy from --in legacy.toon --out data.json --spec v2

# Format / round-trip a TOON file
toonpy fmt --in data.toon --out data.formatted.toon --mode readable

# YAML ↔ TOON  (requires pip install toontools[yaml])
toonpy yaml-to-toon --in data.yaml --out data.toon
toonpy toon-to-yaml --in data.toon --out data.yaml

# TOML ↔ TOON  (requires pip install toontools[toml])
toonpy toml-to-toon --in config.toml --out config.toon
toonpy toon-to-toml --in data.toon --out data.toml
```

**Exit codes:** `0` success · `2` syntax error · `3` general error · `4` I/O error

---

## ⚡ Performance

v1.0.0 is the fastest release yet, with parser throughput more than doubled vs the v0.5.x baseline:

| Operation | v1.0.0 | v0.5.x baseline | Improvement |
|-----------|--------|-------------|-------------|
| Parser — simple object (4 KVs) | **135,924 docs/sec** | ~62,500 | +117% |
| Parser — tabular array 3×3 | **93,085 docs/sec** | ~41,667 | +123% |
| Serializer — simple object | **134,248 docs/sec** | 97,325 | +38% |
| Serializer — with array | **132,248 docs/sec** | 72,308 | +83% |
| Serializer — with table | **80,033 docs/sec** | 46,450 | +72% |
| Serializer — complex nested | **56,608 docs/sec** | 32,678 | +73% |
| Serializer — many booleans | **101,461 docs/sec** | 68,481 | +48% |

Key optimizations in v1.0.0:

- **Parser**: `_parse_header_syntax` (regex) skipped via `"[" not in line` fast path — eliminates the regex for ~99% of KV lines
- **Parser**: `_split_key_value` uses `str.find(":")` fast path for unquoted keys instead of full character walking
- **Parser**: `_parse_object` and `_parse_table_rows` cache `self.lines` and `len(lines)` to avoid repeated attribute lookups
- **Serializer**: `type(item) is dict` replaces `isinstance(x, typing.Mapping)` — avoids slow ABC machinery
- **Serializer**: `_maybe_tabular` auto mode no longer calls `json.dumps` for the savings estimate — O(n) key-length arithmetic instead
- **Utils**: `tabular_schema` savings calculation is O(n) arithmetic, no serialization

Run the benchmarks:

```bash
python benchmark_before.py     # v2 baseline numbers
python benchmark_after.py      # v1.0.0 numbers
```

---

## 🧪 Testing

```bash
# Run all tests (includes 358 official spec fixtures)
pytest

# With coverage
pytest --cov=toonpy --cov-report=html

# Spec fixture tests only
pytest tests/test_spec_fixtures.py -v

# Parser / serializer unit tests
pytest tests/test_parser.py tests/test_serializer.py -v
```

**Test coverage:**
- ✅ 358/358 official TOON spec v3.0 fixtures
- ✅ Parser unit tests (strict, permissive, path expansion, all delimiters)
- ✅ Serializer unit tests (key folding, inline arrays, delimiter modes)
- ✅ API tests (backward compatibility, `spec="v2"` dispatch)
- ✅ Property-based round-trip tests (Hypothesis)
- ✅ YAML and TOML integration tests

---


## 📚 Documentation

| File | Description |
|------|-------------|
| [docs/spec_summary.md](docs/spec_summary.md) | TOON SPEC v3.0 grammar reference |
| [docs/assumptions.md](docs/assumptions.md) | Implementation decisions and strict/permissive behavior |
| [CHANGELOG.md](CHANGELOG.md) | Full version history |
| [README_v2.md](README_v2.md) | Legacy v2-focused documentation |

---


## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Add tests for your changes
4. Ensure all tests pass: `pytest`
5. Open a Pull Request

Please keep changes aligned with TOON SPEC v3.0. For spec questions, refer to [docs/assumptions.md](docs/assumptions.md).

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

## 👨‍💻 Author

**Christian Palomares** — [@shinjidev](https://github.com/shinjidev)

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/shinjidev)

---

*Built on [TOON SPEC v3.0](https://github.com/toon-format/spec) · Property-based testing with [Hypothesis](https://hypothesis.readthedocs.io/).*

⭐ **Star this repository if you find it useful!** ⭐
