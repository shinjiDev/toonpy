# toonpy

`toonpy` is a production-grade Python library and CLI that converts data between JSON and TOON (Token-Oriented Object Notation) while fully conforming to **TOON SPEC v2.0**. It provides a robust lexer/parser, an opinionated serializer with automatic tabular detection, validation utilities, streaming helpers, and ergonomic tooling for developers adopting TOON in modern data workflows.

## Features

- ✅ Lossless conversion between JSON-compatible Python objects and TOON text
- ✅ Lexer + LL(1) parser with indentation tracking, comment support, and ABNF-backed grammar
- ✅ Automatic detection of uniform-object arrays and emission of TOON tabular mode
- ✅ CLI entry point `toonpy` for translation, formatting, and round-tripping files
- ✅ Validation API, streaming helpers, and optional token-savings estimator (`tiktoken`)
- ✅ Comprehensive docs, examples, notebook walkthrough, and CI-ready test suite

## Installation

```bash
pip install .
```

or install with optional extras:

```bash
pip install .[tests]
pip install .[examples]
```

Python 3.9+ is required.

## Usage

### Python API

```python
from toontools import to_toon, from_toon

data = {"crew": [{"id": 1, "name": "Luz"}, {"id": 2, "name": "Amity"}]}
toon_text = to_toon(data, mode="auto")
round_trip = from_toon(toon_text)
assert round_trip == data
```

### CLI

```
toonpy to --in data.json --out data.toon --mode readable
toonpy from --in data.toon --out data.json
toonpy fmt --in data.toon --out data.toon --indent 2
```

Exit code `0` signals success; parse/IO errors emit descriptive diagnostics and non-zero statuses.

### Validation & Suggestions

```python
from toontools import validate_toon, suggest_tabular

ok, issues = validate_toon(toon_text)
estimate = suggest_tabular(data["crew"])
```

## Documentation

- `docs/spec_summary.md` – concise TOON SPEC v2.0 overview with ABNF notes
- `docs/examples.md` – JSON⇄TOON examples
- `docs/heuristics.md` – explanation of tabular heuristics
- `docs/assumptions.md` – documented gaps/assumptions + strict vs. permissive behavior

## Tests & CI

```
pytest
```

Property tests rely on `hypothesis`. CI runs via GitHub Actions (`.github/workflows/ci.yml`).

## Contributing

Issues and pull requests are welcome. Please run formatting, tests, and keep additions aligned with TOON SPEC v2.0.

## License

MIT © ToonPy contributors

