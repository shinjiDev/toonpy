"""
Helper utilities shared between the parser and serializer.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from typing import List, Mapping, Sequence

SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]*$")
NUMBER_RE = re.compile(r"""
    ^
    -?
    (?:
        0
        |
        [1-9][0-9]*
    )
    (?:
        \.[0-9]+
    )?
    (?:
        [eE][+-]?[0-9]+
    )?
    $
""", re.VERBOSE)

__all__ = [
    "TabularSchema",
    "escape_string",
    "format_key",
    "format_scalar",
    "guess_number",
    "is_safe_identifier",
    "split_escaped_row",
    "string_needs_quotes",
    "tabular_schema",
    "token_length",
]


@dataclass(slots=True)
class TabularSchema:
    keys: List[str]
    savings: int


def is_safe_identifier(token: str) -> bool:
    return bool(SAFE_IDENTIFIER_RE.match(token))


def escape_string(value: str) -> str:
    # Delegate to json for full Unicode escape coverage, then strip quotes.
    return json.dumps(value)[1:-1]


def string_needs_quotes(value: str) -> bool:
    if value == "":
        return True
    if not is_safe_identifier(value):
        return True
    if any(ch.isspace() for ch in value):
        return True
    return False


def format_key(key: str) -> str:
    if string_needs_quotes(key):
        return json.dumps(key)
    return key


def format_scalar(value: object) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            if math.isfinite(value):
                return repr(value)
            raise ValueError("TOON does not support non-finite floats")
        return str(value)
    if isinstance(value, str):
        if "\n" in value:
            escaped = escape_string(value)
            return f'"""{escaped}"""'
        if string_needs_quotes(value):
            return f"\"{escape_string(value)}\""
        return value
    if isinstance(value, Mapping):
        raise TypeError("format_scalar does not accept mappings")
    if isinstance(value, (list, tuple)):
        raise TypeError("format_scalar does not accept sequences")
    return json.dumps(value)


def guess_number(token: str) -> int | float | None:
    if not NUMBER_RE.match(token):
        return None
    if "." in token or "e" in token.lower():
        return float(token)
    return int(token)


def split_escaped_row(line: str, separator: str = "|") -> List[str]:
    parts: List[str] = []
    buf: List[str] = []
    in_string = False
    escape = False
    for ch in line:
        if escape:
            buf.append(ch)
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == "\"":
            in_string = not in_string
            buf.append(ch)
            continue
        if ch == separator and not in_string:
            part = "".join(buf).strip()
            if part.startswith(separator):
                part = part[1:].strip()
            parts.append(part)
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    # Trim empty trailing separators commonly written as "| value |"
    cleaned = [p for p in (part.strip(separator).strip() for part in parts) if p != ""]
    return cleaned or parts


def tabular_schema(rows: Sequence[Mapping[str, object]]) -> TabularSchema | None:
    if not rows:
        return None
    keys = list(rows[0].keys())
    if not keys:
        return None
    for row in rows[1:]:
        if list(row.keys()) != keys:
            return None
    linear = json.dumps(rows, separators=(",", ":"))
    table_rows = len(rows) + 1
    approx_table_len = sum(len(k) + 2 for k in keys) + table_rows * sum(len(str(v)) + 2 for v in rows[0].values())
    savings = len(linear) - approx_table_len
    return TabularSchema(keys=keys, savings=savings)


def token_length(text: str) -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text)

