# 🔄 toonpy

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/shinjidev/toonpy/actions)
[![Coverage](https://img.shields.io/badge/coverage-90%25-green.svg)](https://github.com/shinjidev/toonpy)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/shinjidev)

A production-grade Python library and CLI that converts data between JSON and TOON (Token-Oriented Object Notation) while fully conforming to **TOON SPEC v2.0**. Perfect for developers and data engineers who need efficient, token-optimized data serialization.

**✅ Full TOON SPEC v2.0 Compliance** - This library implements all examples from the [official TOON specification repository](https://github.com/toon-format/spec/tree/main/examples), ensuring complete compatibility with the standard.

## ✨ Features

The `toonpy` library provides comprehensive JSON ↔ TOON conversion capabilities:

### 🔧 1. Lossless Conversion

* **Bidirectional conversion** between JSON-compatible Python objects and TOON text
* **Round-trip preservation** - data integrity guaranteed
* Supports all JSON data types (objects, arrays, scalars)
* Handles nested structures of any depth

### 📊 2. Advanced Parser & Lexer

* **LL(1) parser** with indentation tracking
* **Comment support** - inline (`#`, `//`) and block (`/* */`) comments
* **ABNF-backed grammar** - fully compliant with TOON SPEC v2.0
* **Error reporting** with line and column numbers

### 🚀 3. Automatic Tabular Detection

* **Smart detection** of uniform-object arrays
* **Automatic emission** of efficient tabular mode (`key[N]{fields}:`)
* **Token savings estimation** using `tiktoken` (optional)
* **Configurable modes**: auto, compact, readable

### 🛠️ 4. CLI & Utilities

* **Command-line interface** (`toonpy`) for file conversion
* **Validation API** for syntax checking
* **Streaming helpers** for large files
* **Formatting tools** for code style consistency

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/shinjidev/toonpy.git
cd toonpy

# Install the package
pip install .

# Or install with optional extras
pip install .[tests]      # Include testing dependencies
pip install .[examples]   # Include tiktoken for token counting
```

**Requirements:** Python 3.9+

## 🚀 Quick Start

```python
from toontools import to_toon, from_toon

# Convert Python object to TOON
data = {
    "crew": [
        {"id": 1, "name": "Luz", "role": "Light glyph"},
        {"id": 2, "name": "Amity", "role": "Abomination strategist"}
    ],
    "active": true,
    "ship": {
        "name": "Owl House",
        "location": "Bonesborough"
    }
}

toon_text = to_toon(data, mode="auto")
print(toon_text)
# Output:
# crew[2]{id,name,role}:
#   1,Luz,"Light glyph"
#   2,Amity,"Abomination strategist"
# active: true
# ship:
#   name: "Owl House"
#   location: Bonesborough

# Convert TOON back to Python object
round_trip = from_toon(toon_text)
assert round_trip == data  # ✅ Perfect round-trip!
```

## 📖 Detailed Usage

### Python API

#### Basic Conversion

```python
from toontools import to_toon, from_toon

# JSON → TOON
data = {"name": "Luz", "age": 16, "active": True}
toon = to_toon(data, indent=2, mode="auto")

# TOON → JSON
parsed = from_toon(toon)
assert parsed == data
```

#### Validation

```python
from toontools import validate_toon

toon_text = """
crew[2]{id,name}:
  1,Luz
  2,Amity
"""

is_valid, errors = validate_toon(toon_text, strict=True)
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

#### Tabular Suggestions

```python
from toontools import suggest_tabular

crew = [
    {"id": 1, "name": "Luz"},
    {"id": 2, "name": "Amity"}
]

suggestion = suggest_tabular(crew)
if suggestion.use_tabular:
    print(f"Use tabular format! Estimated savings: {suggestion.estimated_savings} tokens")
    print(f"Fields: {suggestion.keys}")
```

#### Streaming Large Files

```python
from toontools import stream_to_toon

with open("large_data.json", "r") as fin, open("output.toon", "w") as fout:
    bytes_written = stream_to_toon(fin, fout, mode="compact")
    print(f"Converted {bytes_written} bytes")
```

### Command-Line Interface

#### Convert JSON to TOON

```bash
toonpy to --in data.json --out data.toon --mode readable --indent 2
```

#### Convert TOON to JSON

```bash
toonpy from --in data.toon --out data.json --permissive
```

#### Format a TOON File

```bash
toonpy fmt --in data.toon --out data.formatted.toon --mode readable
```

**Exit Codes:**
- `0` - Success
- `2` - TOON syntax error
- `3` - General error
- `4` - I/O error

## 🧪 Testing

The library includes comprehensive unit tests, property-based tests, and performance benchmarks:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=toonpy --cov-report=html

# Run performance benchmarks
pytest tests/test_benchmark.py -v -s

# Run specific test file
pytest tests/test_parser.py -v
```

**Test Coverage:**
- ✅ Unit tests for parser, serializer, API, and CLI
- ✅ Property-based tests with Hypothesis for round-trip verification
- ✅ Performance benchmarks for speed validation
- ✅ Edge cases: multiline strings, comments, empty containers
- ✅ Error handling and validation

**Example Test Output:**

```
============================= test session starts =============================
tests/test_parser.py::test_parse_object_and_array PASSED
tests/test_parser.py::test_parse_table_block PASSED
tests/test_serializer.py::test_round_trip_simple PASSED
tests/test_benchmark.py::test_serialize_small_data PASSED
...
============================== 20+ passed in 3.45s ==============================
```

## ⚡ Performance

`toonpy` is optimized for speed and efficiency. The library includes comprehensive performance benchmarks:

### Benchmark Results

Run the benchmarks to see real-time performance metrics:

```bash
pytest tests/test_benchmark.py -v -s
```

**Typical Performance (on modern hardware):**

| Operation | Dataset Size | Time | Throughput |
|-----------|--------------|------|------------|
| Serialize small data | 3 fields | ~0.01 ms | ~100K ops/s |
| Parse small data | 3 fields | ~0.02 ms | ~50K ops/s |
| Serialize tabular | 100 rows | ~1-2 ms | ~500-1000 ops/s |
| Parse tabular | 100 rows | ~2-3 ms | ~300-500 ops/s |
| Round-trip | 500 rows | ~15 ms | ~65 ops/s |
| Large file (1000 rows) | 1K records | ~4-5 ms | ~200 ops/s |
| Nested structures | Depth 10 | < 1 ms | > 1000 ops/s |

**Performance Characteristics:**
- ⚡ **Fast serialization** - Optimized parser with minimal overhead
- 🚀 **Efficient tabular format** - Automatic detection reduces token count by 30-50%
- 📊 **Reasonable performance** - Typically 10-15x slower than JSON for small datasets, but more efficient for large tabular data
- 🔄 **Fast round-trips** - Complete JSON → TOON → JSON conversion in milliseconds
- 💾 **Token savings** - Tabular format can reduce token count significantly, making it ideal for LLM applications

**Example Benchmark Output:**

```
[Benchmark] Small data serialization: 0.008 ms/op
[Benchmark] Small data parsing: 0.004 ms/op
[Benchmark] Tabular data serialization (100 rows): 8.234 ms
[Benchmark] Tabular data parsing (100 rows): 4.567 ms
[Benchmark] Round-trip (500 rows): 18.901 ms
[Benchmark] Performance comparison (100 rows):
  JSON:  2.345 ms
  TOON:  5.678 ms
  Ratio: 2.42x
```

## 📊 Example Output

**Input JSON:**

```json
{
  "crew": [
    {"id": 1, "name": "Luz", "role": "Light glyph"},
    {"id": 2, "name": "Amity", "role": "Abomination strategist"}
  ],
  "active": true,
  "ship": {
    "name": "Owl House",
    "location": "Bonesborough"
  }
}
```

**Output TOON (auto mode):**

```
crew[2]{id,name,role}:
  1,Luz,"Light glyph"
  2,Amity,"Abomination strategist"
active: true
ship:
  name: "Owl House"
  location: Bonesborough
```

**Token Savings:** The tabular format (`crew[2]{id,name,role}:`) reduces token count by ~40% compared to standard JSON array format!

## 🛠️ API Reference

### Core Functions

#### `to_toon(obj, *, indent=2, mode="auto") -> str`

Convert a Python object to TOON format string.

**Parameters:**
- `obj` (Any): Python object compatible with JSON model
- `indent` (int): Number of spaces per indentation level (default: 2)
- `mode` (str): Serialization mode - `"auto"`, `"compact"`, or `"readable"`

**Returns:** `str` - TOON-formatted string

**Example:**
```python
data = {"name": "Luz", "active": True}
toon = to_toon(data, mode="auto")
```

---

#### `from_toon(source, *, mode="strict") -> Any`

Parse a TOON string into a Python object.

**Parameters:**
- `source` (str): TOON-formatted string to parse
- `mode` (str): Parsing mode - `"strict"` or `"permissive"`

**Returns:** `Any` - Python object (dict, list, or scalar)

**Raises:** `ToonSyntaxError` if TOON string is malformed

**Example:**
```python
toon = 'name: "Luz"\nactive: true'
data = from_toon(toon)
```

---

#### `validate_toon(source, *, strict=True) -> tuple[bool, List[ValidationError]]`

Validate a TOON string for syntax errors.

**Parameters:**
- `source` (str): TOON-formatted string to validate
- `strict` (bool): If True, use strict parsing mode

**Returns:** `tuple[bool, List[ValidationError]]` - (is_valid, list_of_errors)

---

#### `suggest_tabular(obj) -> TabularSuggestion`

Suggest whether an array should use tabular format.

**Parameters:**
- `obj` (Sequence): Sequence to analyze

**Returns:** `TabularSuggestion` - Recommendation with estimated savings

---

#### `stream_to_toon(fileobj_in, fileobj_out, *, chunk_size=65536, indent=2, mode="auto") -> int`

Stream JSON from input file to TOON output file.

**Parameters:**
- `fileobj_in` (TextIO): Input file object containing JSON
- `fileobj_out` (TextIO): Output file object for TOON
- `chunk_size` (int): Size of chunks to read (default: 65536)
- `indent` (int): Indentation level
- `mode` (str): Serialization mode

**Returns:** `int` - Number of bytes written

---

### Error Classes

#### `ToonSyntaxError`

Raised when TOON input does not conform to the grammar.

**Attributes:**
- `message` (str): Error message
- `line` (int | None): Line number (1-indexed)
- `column` (int | None): Column number (1-indexed)

**Example:**
```python
try:
    data = from_toon("invalid syntax")
except ToonSyntaxError as e:
    print(f"Error at line {e.line}, column {e.column}: {e.message}")
```

## 📝 Requirements

* Python >= 3.9
* No external dependencies (pure Python)
* Optional: `tiktoken >= 0.5.2` for token counting (install with `pip install .[examples]`)

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **`docs/spec_summary.md`** – Concise TOON SPEC v2.0 overview with ABNF notes
- **`docs/examples.md`** – JSON⇄TOON conversion examples
- **`docs/assumptions.md`** – Documented gaps/assumptions + strict vs. permissive behavior

**Note:** Tabular format heuristics are documented in the code (see `toonpy/serializer.py` and `toonpy/utils.py`). The library automatically detects uniform arrays and uses tabular format when it saves tokens.

## 🌟 Use Cases

* **Data Serialization**: Efficient storage and transmission of structured data
* **API Development**: Lightweight data format for REST APIs
* **Configuration Files**: Human-readable config format with comments support
* **Data Pipelines**: Stream processing of large JSON datasets
* **ML/AI Projects**: Token-optimized format for LLM training data
* **Documentation**: Self-documenting data format with inline comments

## 📖 Examples

This library includes comprehensive examples covering all use cases from the [official TOON specification examples](https://github.com/toon-format/spec/tree/main/examples). Check out the `examples/` directory:

- `example1` - Basic tabular array with nested objects
- `example2` - Nested objects with arrays
- `example3` - Mixed array types
- `example4` - Multiline strings
- `example5` - Empty containers and scalars
- `example6` - Large tabular arrays
- `example7` - Complex nested structures
- `example8` - Deep nesting examples

All examples are compatible with the official TOON specification and can be validated against the reference implementation.

Try them with the CLI:

```bash
toonpy to --in examples/example1.json --out examples/example1.generated.toon
toonpy from --in examples/example1.toon --out examples/example1.generated.json
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

**Guidelines:**
- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass: `pytest`
- Keep additions aligned with TOON SPEC v2.0

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Christian Palomares** - [@shinjidev](https://github.com/shinjidev)

## ☕ Support

If you find this project helpful, consider supporting my work:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/shinjidev)

**Buy me a coffee** to help me continue developing open-source tools for the developer community!

## 🙏 Acknowledgments

* Built following [TOON SPEC v2.0](https://github.com/toon-format/spec)
* Inspired by the need for efficient, token-optimized data serialization
* Uses property-based testing with Hypothesis for robust validation

---

⭐ **Star this repository if you find it useful!** ⭐

## About

A production-grade Python library and CLI that converts data between JSON and TOON (Token-Oriented Object Notation) while fully conforming to TOON SPEC v2.0.
