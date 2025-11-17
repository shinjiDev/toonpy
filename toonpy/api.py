"""
Public API surface for toonpy.
"""

from __future__ import annotations

from dataclasses import dataclass
import io
import json
from typing import Any, BinaryIO, Iterable, List, Literal, Sequence, TextIO

from .errors import ToonSyntaxError, ValidationError
from .parser import from_toon as _from_toon
from .serializer import to_toon as _to_toon
from .utils import TabularSchema, tabular_schema, token_length

__all__ = [
    "to_toon",
    "from_toon",
    "stream_to_toon",
    "suggest_tabular",
    "validate_toon",
    "TabularSuggestion",
]


@dataclass(slots=True)
class TabularSuggestion:
    use_tabular: bool
    estimated_savings: int
    keys: List[str]


def to_toon(obj: Any, *, indent: int = 2, mode: Literal["auto", "compact", "readable"] = "auto") -> str:
    return _to_toon(obj, indent=indent, mode=mode)


def from_toon(source: str, *, mode: Literal["strict", "permissive"] = "strict") -> Any:
    return _from_toon(source, permissive=(mode == "permissive"))


def stream_to_toon(
    fileobj_in: TextIO,
    fileobj_out: TextIO,
    *,
    chunk_size: int = 65_536,
    indent: int = 2,
    mode: Literal["auto", "compact", "readable"] = "auto",
) -> int:
    buffer = io.StringIO()
    while True:
        chunk = fileobj_in.read(chunk_size)
        if not chunk:
            break
        buffer.write(chunk)
    buffer.seek(0)
    data = json.load(buffer)
    toon_text = to_toon(data, indent=indent, mode=mode)
    fileobj_out.write(toon_text)
    return len(toon_text)


def suggest_tabular(obj: Sequence[Any]) -> TabularSuggestion:
    if not isinstance(obj, Sequence) or isinstance(obj, (str, bytes, bytearray)):
        return TabularSuggestion(False, 0, [])
    mappings = [item for item in obj if isinstance(item, dict)]
    if len(mappings) != len(obj):
        return TabularSuggestion(False, 0, [])
    schema = tabular_schema(mappings)
    if not schema:
        return TabularSuggestion(False, 0, [])
    linear = json.dumps(obj, separators=(",", ":"))
    serializer_text = _to_toon(obj, indent=2, mode="compact")
    savings = token_length(linear) - token_length(serializer_text)
    return TabularSuggestion(savings > 0, savings, schema.keys)


def validate_toon(source: str, *, strict: bool = True) -> tuple[bool, List[ValidationError]]:
    try:
        _from_toon(source, permissive=not strict)
    except ToonSyntaxError as exc:
        return False, [ValidationError(str(exc), exc.line, exc.column)]
    return True, []

