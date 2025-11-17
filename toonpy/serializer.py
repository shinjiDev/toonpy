"""
Serializer that converts Python objects into TOON text.
"""

from __future__ import annotations

import json
from typing import Any, Literal, Mapping, Sequence

from .utils import TabularSchema, format_key, string_needs_quotes, tabular_schema

Mode = Literal["auto", "compact", "readable"]

__all__ = ["to_toon"]


class ToonSerializer:
    def __init__(self, *, indent: int = 2, mode: Mode = "auto") -> None:
        self.indent = indent
        self.mode = mode

    def dumps(self, obj: Any) -> str:
        lines: list[str] = []
        self._write_value(obj, 0, lines)
        return "\n".join(lines).rstrip() + "\n"

    def _write_value(self, obj: Any, level: int, lines: list[str]) -> None:
        if isinstance(obj, Mapping):
            if not obj:
                lines.append(" " * level + "{}")
                return
            self._write_object(obj, level, lines)
        elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
            if not obj:
                lines.append(" " * level + "[]")
                return
            self._write_array(obj, level, lines)
        else:
            lines.append(" " * level + self._format_scalar(obj))

    def _write_object(self, mapping: Mapping[str, Any], level: int, lines: list[str]) -> None:
        for key, value in mapping.items():
            key_repr = format_key(str(key))
            prefix = " " * level + f"{key_repr}:"
            inline_container = self._inline_container_repr(value)
            if inline_container is not None:
                lines.append(f"{prefix} {inline_container}")
                continue
            if self._is_inline(value):
                lines.append(f"{prefix} {self._format_scalar(value)}")
            else:
                lines.append(prefix)
                self._write_value(value, level + self.indent, lines)

    def _write_array(self, seq: Sequence[Any], level: int, lines: list[str]) -> None:
        schema = self._maybe_tabular(seq)
        if schema:
            self._write_table(seq, schema, level, lines)
            return
        for item in seq:
            prefix = " " * level + "-"
            inline_container = self._inline_container_repr(item)
            if inline_container is not None:
                lines.append(f"{prefix} {inline_container}")
                continue
            if self._is_inline(item):
                lines.append(f"{prefix} {self._format_scalar(item)}")
            else:
                lines.append(prefix)
                self._write_value(item, level + self.indent, lines)

    def _write_table(
        self,
        seq: Sequence[Mapping[str, Any]],
        schema: TabularSchema,
        level: int,
        lines: list[str],
    ) -> None:
        header = ", ".join(format_key(key) for key in schema.keys)
        lines.append(" " * level + f"@table {header}")
        inner_indent = " " * (level + self.indent)
        for row in seq:
            cells = []
            for key in schema.keys:
                value = row.get(key)
                cells.append(self._format_cell(value))
            lines.append(f"{inner_indent}| " + " | ".join(cells) + " |")

    def _maybe_tabular(self, seq: Sequence[Any]) -> TabularSchema | None:
        if not seq:
            return None
        if not all(isinstance(item, Mapping) for item in seq):
            return None
        schema = tabular_schema(seq)  # type: ignore[arg-type]
        if not schema:
            return None
        if self.mode == "readable":
            return schema if schema.savings > 10 else None
        if self.mode == "compact":
            return schema
        baseline = len(self._linearize(seq))
        if schema.savings <= 0:
            return None
        toon_estimate = baseline - schema.savings
        return schema if toon_estimate < baseline else None

    def _linearize(self, seq: Sequence[Any]) -> str:
        from json import dumps

        return dumps(seq, separators=(",", ":"))

    def _is_inline(self, value: Any) -> bool:
        if isinstance(value, Mapping):
            return False
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return False
        if isinstance(value, str) and "\n" in value:
            return False
        return True

    def _format_cell(self, value: Any) -> str:
        if isinstance(value, str) and not string_needs_quotes(value) and "|" not in value and "," not in value:
            return value
        return self._format_scalar(value)

    def _format_scalar(self, value: Any, *, force_string: bool = False) -> str:
        if value is None and not force_string:
            return "null"
        if value is True and not force_string:
            return "true"
        if value is False and not force_string:
            return "false"
        if isinstance(value, (int, float)) and not force_string:
            return repr(value)
        if isinstance(value, str):
            if not force_string and not string_needs_quotes(value):
                return value
            return json.dumps(value)
        if force_string:
            return json.dumps(str(value))
        return self._format_scalar(str(value), force_string=True)

    @staticmethod
    def _inline_container_repr(value: Any) -> str | None:
        if isinstance(value, Mapping) and not value:
            return "{}"
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) and not value:
            return "[]"
        return None


def to_toon(obj: Any, *, indent: int = 2, mode: Mode = "auto") -> str:
    return ToonSerializer(indent=indent, mode=mode).dumps(obj)

