"""
Serializer that converts Python objects into TOON text.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Literal, Mapping, Sequence

import re as _re
from .utils import TabularSchema, _value_needs_quotes, format_key, tabular_schema

# Dotted-path key: segments joined by '.', each segment matches identifier chars (no hyphens)
_DOTTED_KEY_RE = _re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def _format_dotted_key(key: str) -> str:
    """Format a key for TOON output, allowing dotted-path identifiers unquoted."""
    if _DOTTED_KEY_RE.match(key):
        return key
    return format_key(key)


mode_type = Literal["auto", "compact", "readable"]

__all__ = ["to_toon"]


class ToonSerializer:
    """Serializer that converts Python objects to TOON format text."""

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
        # Accept both string names ("tab") and raw chars ("\t") for delimiter
        _name_to_char = {"comma": ",", "tab": "\t", "pipe": "|"}
        char = _name_to_char.get(delimiter, delimiter)
        self._delim_char = char if char in (",", "\t", "|") else ","
        self._delim_bracket = "" if self._delim_char == "," else self._delim_char

    def dumps(self, obj: Any) -> str:
        lines: list[str] = []
        self._write_value(obj, 0, lines)
        if not lines:
            return "\n"
        return "\n".join(lines) + "\n"

    def _get_indent(self, level: int) -> str:
        if level <= self._max_cached_indent:
            if level not in self._indent_cache:
                self._indent_cache[level] = " " * (level * self.indent)
            return self._indent_cache[level]
        return " " * (level * self.indent)

    def _write_value(self, obj: Any, level: int, lines: list[str]) -> None:
        """Root dispatcher. Empty mapping → no output. Empty seq → [0]: header."""
        if not obj:
            if isinstance(obj, Mapping):
                return  # root empty dict → empty string
            if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
                indent_str = self._get_indent(level)
                lines.append(indent_str + f"[0]{self._delim_bracket}:")
                return
            # empty string falls through to scalar

        if isinstance(obj, Mapping):
            self._write_object(obj, level, lines)
        elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
            self._write_array(obj, level, lines)
        else:
            indent_str = self._get_indent(level)
            lines.append(indent_str + self._format_scalar(obj))

    def _write_object(
        self,
        mapping: Mapping[str, Any],
        level: int,
        lines: list[str],
        _fold_depth: float | None = None,
    ) -> None:
        """Write an object. _fold_depth tracks remaining key-folding budget."""
        from .utils import is_identifier_segment

        if self.key_folding == "safe":
            if _fold_depth is None:
                _fold_depth = self.flatten_depth - 1
        else:
            _fold_depth = 0

        indent_str = self._get_indent(level)
        for key, value in mapping.items():
            if _fold_depth > 0:
                folded = self._try_fold(str(key), value, mapping, _fold_depth)
                if folded is not None:
                    folded_key_str, value = folded
                    key_repr = _format_dotted_key(folded_key_str)
                    child_fold_depth = _fold_depth - folded_key_str.count(".")
                else:
                    key_repr = _format_dotted_key(str(key))
                    # If a sibling literal key shares this key as a prefix, suppress
                    # inner folding to prevent generating paths that collide with it
                    prefix = str(key) + "."
                    if any(k.startswith(prefix) for k in mapping):
                        child_fold_depth = 0
                    else:
                        child_fold_depth = _fold_depth
            else:
                key_repr = _format_dotted_key(str(key))
                child_fold_depth = 0

            self._write_kv(key_repr, value, indent_str, level, child_fold_depth, lines)

    def _write_kv(
        self,
        key_repr: str,
        value: Any,
        line_prefix: str,
        level: int,
        fold_depth: float,
        lines: list[str],
    ) -> None:
        """Write a key-value pair with a custom line prefix."""
        br = self._delim_bracket

        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            n = len(value)
            if not value:
                lines.append(f"{line_prefix}{key_repr}[0{br}]:")
                return
            if self._maybe_primitive_inline(value):
                cells = self._delim_char.join(self._format_cell(v) for v in value)
                lines.append(f"{line_prefix}{key_repr}[{n}{br}]: {cells}")
                return
            schema = self._tabular_schema_if_eligible(value)
            if schema:
                fields = self._delim_char.join(format_key(k) for k in schema.keys)
                lines.append(f"{line_prefix}{key_repr}[{n}{br}]{{{fields}}}:")
                inner_indent = self._get_indent(level + 1)
                for row in value:
                    row_cells = self._delim_char.join(
                        self._format_cell(row.get(k)) for k in schema.keys
                    )
                    lines.append(inner_indent + row_cells)
                return
            lines.append(f"{line_prefix}{key_repr}[{n}{br}]:")
            self._write_list_items(value, level + 1, lines)
            return

        if isinstance(value, Mapping):
            lines.append(f"{line_prefix}{key_repr}:")
            if value:
                self._write_object(value, level + 1, lines, fold_depth)
            return

        # Scalar — delimiter-aware for strings
        lines.append(f"{line_prefix}{key_repr}: {self._format_val(value)}")

    def _write_array(self, seq: Sequence[Any], level: int, lines: list[str]) -> None:
        """Write root-level array with [N]: header."""
        n = len(seq)
        br = self._delim_bracket
        indent_str = self._get_indent(level)

        if not seq:
            lines.append(indent_str + f"[0{br}]:")
            return

        if self._maybe_primitive_inline(seq):
            cells = self._delim_char.join(self._format_cell(v) for v in seq)
            lines.append(indent_str + f"[{n}{br}]: {cells}")
            return

        schema = self._tabular_schema_if_eligible(seq)
        if schema:
            fields = self._delim_char.join(format_key(k) for k in schema.keys)
            lines.append(indent_str + f"[{n}{br}]{{{fields}}}:")
            inner_indent = self._get_indent(level + 1)
            for row in seq:
                row_cells = self._delim_char.join(
                    self._format_cell(row.get(k)) for k in schema.keys
                )
                lines.append(inner_indent + row_cells)
            return

        lines.append(indent_str + f"[{n}{br}]:")
        self._write_list_items(seq, level + 1, lines)

    def _write_list_items(self, seq: Sequence[Any], level: int, lines: list[str]) -> None:
        """Write items of an array with - prefix."""
        dash = self._get_indent(level) + "-"
        for item in seq:
            if isinstance(item, Mapping):
                if not item:
                    lines.append(dash)  # bare hyphen for empty object
                else:
                    self._write_mapping_as_list_item(item, dash, level, lines)
            elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
                self._write_seq_as_list_item(item, dash, level, lines)
            else:
                lines.append(f"{dash} {self._format_val(item)}")

    def _write_mapping_as_list_item(
        self, mapping: Mapping[str, Any], dash: str, level: int, lines: list[str]
    ) -> None:
        """Write dict as list item: first key on dash line, rest at level+1."""
        inner_indent = self._get_indent(level + 1)
        first = True
        for key, value in mapping.items():
            key_repr = _format_dotted_key(str(key))
            prefix = (dash + " ") if first else inner_indent
            first = False
            self._write_kv(key_repr, value, prefix, level + 1, 0, lines)

    def _write_seq_as_list_item(
        self, value: Sequence[Any], dash: str, level: int, lines: list[str]
    ) -> None:
        """Write array as list item: - [N]: ... format."""
        n = len(value)
        br = self._delim_bracket
        if not value:
            lines.append(f"{dash} [0{br}]:")
            return
        if self._maybe_primitive_inline(value):
            cells = self._delim_char.join(self._format_cell(v) for v in value)
            lines.append(f"{dash} [{n}{br}]: {cells}")
            return
        schema = self._tabular_schema_if_eligible(value)
        if schema:
            fields = self._delim_char.join(format_key(k) for k in schema.keys)
            lines.append(f"{dash} [{n}{br}]{{{fields}}}:")
            inner_indent = self._get_indent(level + 2)
            for row in value:
                row_cells = self._delim_char.join(
                    self._format_cell(row.get(k)) for k in schema.keys
                )
                lines.append(inner_indent + row_cells)
            return
        lines.append(f"{dash} [{n}{br}]:")
        self._write_list_items(value, level + 1, lines)

    def _tabular_schema_if_eligible(self, seq: Sequence[Any]) -> TabularSchema | None:
        """Return tabular schema only if all rows are dicts with all-primitive values."""
        if not seq or not all(type(item) is dict for item in seq):
            return None
        # Only use tabular when all field values are primitive scalars
        for row in seq:
            for v in row.values():
                if isinstance(v, (dict, list)):
                    return None
        return self._maybe_tabular(seq)

    def _maybe_primitive_inline(self, seq: Sequence[Any]) -> bool:
        """Return True if seq should be serialized as an inline primitive array."""
        if not seq:
            return False
        for item in seq:
            if isinstance(item, (dict, list)):
                return False
            if isinstance(item, str) and "\n" in item:
                return False
        return True

    def _maybe_tabular(self, seq: Sequence[Any]) -> TabularSchema | None:
        """Determine if a sequence should be serialized as a table."""
        if not seq:
            return None
        if not all(type(item) is dict for item in seq):
            return None
        schema = tabular_schema(seq)  # type: ignore[arg-type]
        if not schema:
            return None
        if self.mode == "readable":
            return schema if schema.savings > 10 else None
        if self.mode == "compact":
            return schema
        # auto: schema.savings is already (json_linear_len - approx_table_len)
        # toon_estimate < baseline iff savings > 0 — no need to recompute json length
        return schema if schema.savings > 0 else None

    def _format_cell(self, value: Any) -> str:
        """Format a table/array cell, quoting if it contains the active delimiter or ':'."""
        if not value and isinstance(value, (list, dict)):
            if isinstance(value, Mapping):
                return "{}"
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                return "[]"

        if isinstance(value, str):
            # Quote if: inherently unsafe, contains current delimiter, colon, or space
            if _value_needs_quotes(value) or self._delim_char in value or ":" in value or " " in value:
                return json.dumps(value, ensure_ascii=False)
            return value
        return self._format_scalar(value)

    def _format_val(self, value: Any) -> str:
        """Format a scalar for object values and list item scalars, delimiter-aware.

        Spaces in unquoted strings are only valid at root level; object values
        and list items use _parse_token which rejects spaces unless quoted.
        """
        if isinstance(value, str):
            if _value_needs_quotes(value) or self._delim_char in value or " " in value:
                return json.dumps(value, ensure_ascii=False)
            return value
        return self._format_scalar(value)

    def _format_scalar(self, value: Any, *, force_string: bool = False) -> str:
        """Format a scalar value for TOON output."""
        if value is None and not force_string:
            return "null"
        if value is True and not force_string:
            return "true"
        if value is False and not force_string:
            return "false"
        if isinstance(value, (int, float)) and not force_string:
            if isinstance(value, float):
                if value == 0.0:
                    return "0"
                int_val = int(value)
                if int_val == value:
                    return str(int_val)
                # Use decimal notation instead of scientific (e.g. 1e-6 → 0.000001)
                return format(Decimal(repr(value)), "f")
            return str(value)
        if isinstance(value, str):
            if not force_string and not _value_needs_quotes(value):
                return value
            return json.dumps(value, ensure_ascii=False)
        if force_string:
            return json.dumps(str(value), ensure_ascii=False)
        return self._format_scalar(str(value), force_string=True)

    def _try_fold(
        self,
        key: str,
        value: Any,
        siblings: Mapping,
        depth_remaining: float,
    ) -> tuple[str, Any] | None:
        """Try to fold 'key → {single_key: child}' into 'key.single_key'."""
        from .utils import is_identifier_segment

        if depth_remaining <= 0:
            return None
        # Parent key must be a valid identifier segment
        if not is_identifier_segment(key):
            return None
        if not isinstance(value, Mapping) or len(value) != 1:
            return None
        child_key = next(iter(value))
        child_val = value[child_key]
        if not is_identifier_segment(child_key):
            return None
        folded = f"{key}.{child_key}"
        # Recurse before checking collision (need final key to check against siblings)
        deeper = self._try_fold(child_key, child_val, {}, depth_remaining - 1)
        if deeper is not None:
            deeper_key, deeper_val = deeper
            final = f"{key}.{deeper_key}"
            if final in siblings:
                return None
            return final, deeper_val
        if folded in siblings:
            return None
        return folded, child_val


def to_toon(
    obj: Any,
    *,
    indent: int = 2,
    mode: mode_type = "auto",
    delimiter: str = "comma",
    key_folding: str = "off",
    flatten_depth: float = float("inf"),
) -> str:
    """Convert a Python object to TOON format string."""
    return ToonSerializer(
        indent=indent, mode=mode, delimiter=delimiter,
        key_folding=key_folding, flatten_depth=flatten_depth,
    ).dumps(obj)
