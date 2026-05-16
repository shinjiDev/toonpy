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
    # "options" does not exist in the spec repo (404) — intentionally excluded
    "key-folding",
]


def _load_params(category: str, names: list[str]) -> list[tuple[str, dict]]:
    """Build parametrize list from cached fixture files (skips missing files)."""
    params = []
    for name in names:
        path = FIXTURES_DIR / category / f"{name}.json"
        if not path.exists():
            continue
        try:
            cases = json.loads(path.read_text(encoding="utf-8"))["tests"]
        except Exception:
            continue
        for case in cases:
            params.append((f"{name}::{case['name']}", case))
    return params


def _decode_params() -> list[tuple[str, dict]]:
    return _load_params("decode", DECODE_FIXTURES)


def _encode_params() -> list[tuple[str, dict]]:
    return _load_params("encode", ENCODE_FIXTURES)


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


_DECODE_PARAMS = _decode_params()
_ENCODE_PARAMS = _encode_params()


@pytest.mark.parametrize("name,case", _DECODE_PARAMS, ids=[p[0] for p in _DECODE_PARAMS])
def test_decode_fixture(name: str, case: dict) -> None:
    source: str = case["input"]
    options = _options_to_kwargs(case.get("options", {}))
    should_error: bool = case.get("shouldError", False)

    if should_error:
        with pytest.raises(ToonSyntaxError):
            from_toon(source, **options)
        return

    result = from_toon(source, **options)
    assert result == case["expected"], (
        f"\nTest: {name}\nInput: {source!r}\nExpected: {case['expected']!r}\nGot: {result!r}"
    )


@pytest.mark.parametrize("name,case", _ENCODE_PARAMS, ids=[p[0] for p in _ENCODE_PARAMS])
def test_encode_fixture(name: str, case: dict) -> None:
    obj = case["input"]
    options = _options_to_kwargs(case.get("options", {}))
    should_error: bool = case.get("shouldError", False)
    expected: str = case.get("expected", "")

    if should_error:
        with pytest.raises((ToonSyntaxError, ValueError)):
            to_toon(obj, **options)
        return

    result = to_toon(obj, **options).strip()
    assert result == expected.strip(), (
        f"\nTest: {name}\nInput: {obj!r}\nExpected:\n{expected}\nGot:\n{result}"
    )
