"""
Serializer that converts Python objects into TOON text.
"""

from __future__ import annotations

import json
from typing import Any, Literal, Mapping, Sequence

import re as _re
from .utils import TabularSchema, format_key, string_needs_quotes, tabular_schema

# Dotted-path key: segments joined by '.', each segment matches identifier chars (no hyphens)
_DOTTED_KEY_RE = _re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def _format_dotted_key(key: str) -> str:
    """Format a (potentially dotted) key for TOON output.

    Dotted keys like 'a.b.c' are emitted unquoted if every segment is a safe
    identifier (no hyphens, no special chars). Otherwise falls back to format_key.
    """
    if _DOTTED_KEY_RE.match(key):
        return key
    return format_key(key)

mode_type = Literal["auto", "compact", "readable"]

__all__ = ["to_toon"]


class ToonSerializer:
    """Serializer that converts Python objects to TOON format text.

    Handles objects, arrays, scalars, and automatically detects tabular arrays
    for efficient serialization according to TOON SPEC v3.0.
    """

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
        # Pre-compute delimiter chars for performance
        self._delim_char = {"comma": ",", "tab": "\t", "pipe": "|"}.get(delimiter, ",")
        self._delim_bracket = {"comma": "", "tab": "\t", "pipe": "|"}.get(delimiter, "")

    def dumps(self, obj: Any) -> str:
        """Serialize a Python object to TOON format string.

        Args:
            obj: Python object (dict, list, scalar) compatible with JSON model

        Returns:
            TOON-formatted string with trailing newline
        """
        lines: list[str] = []
        self._write_value(obj, 0, lines)
        # Optimization: use join once instead of multiple concatenations
        if not lines:
            return "\n"
        return "\n".join(lines) + "\n"

    def _get_indent(self, level: int) -> str:
        """Get indentation string for given level, using cache.

        Args:
            level: Indentation level

        Returns:
            String of spaces for indentation
        """
        if level <= self._max_cached_indent:
            if level not in self._indent_cache:
                self._indent_cache[level] = " " * (level * self.indent)
            return self._indent_cache[level]
        return " " * (level * self.indent)

    def _write_value(self, obj: Any, level: int, lines: list[str]) -> None:
        """Write a value to the output lines, dispatching by type.

        Args:
            obj: Value to serialize (object, array, or scalar)
            level: Current indentation level (number of spaces)
            lines: List of output lines to append to
        """
        # Optimization: Check for empty containers first (common case)
        if not obj:
            indent_str = self._get_indent(level)
            if isinstance(obj, Mapping):
                lines.append(indent_str + "{}")
                return
            if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
                lines.append(indent_str + "[]")
                return
            # Empty string - fall through to scalar formatting

        # Non-empty or scalar values
        if isinstance(obj, Mapping):
            self._write_object(obj, level, lines)
        elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
            self._write_array(obj, level, lines)
        else:
            indent_str = self._get_indent(level)
            lines.append(indent_str + self._format_scalar(obj))

    def _write_object(self, mapping: Mapping[str, Any], level: int, lines: list[str]) -> None:
        """Write an object (dict) to output lines.

        Detects tabular arrays and uses spec-compliant key[N]{fields}: syntax.
        Otherwise writes key-value pairs with appropriate indentation.

        Args:
            mapping: Dictionary to serialize
            level: Current indentation level
            lines: List of output lines to append to
        """
        indent_str = self._get_indent(level)
        for key, value in mapping.items():
            # Key folding: try to collapse single-key chain into dotted path
            if self.key_folding == "safe":
                folded = self._try_fold(str(key), value, mapping, self.flatten_depth)
                if folded is not None:
                    folded_key_str, value = folded
                    key_repr = _format_dotted_key(folded_key_str)
                else:
                    key_repr = format_key(str(key))
            else:
                key_repr = format_key(str(key))

            # Check for primitive inline array: key[N]: v1,v2,v3
            if (isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))
                    and self._maybe_primitive_inline(value)):
                cells = self._delim_char.join(self._format_cell(v) for v in value)
                lines.append(indent_str + f"{key_repr}[{len(value)}]{self._delim_bracket}: {cells}")
                continue

            # Check if value is a tabular array
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) and value:
                schema = self._maybe_tabular(value)
                if schema and all(isinstance(item, Mapping) for item in value):
                    self._write_table_as_key(key_repr, value, schema, level, lines)
                    continue
            prefix = indent_str + f"{key_repr}:"
            inline_container = self._inline_container_repr(value)
            if inline_container is not None:
                lines.append(f"{prefix} {inline_container}")
                continue
            if self._is_inline(value):
                lines.append(f"{prefix} {self._format_scalar(value)}")
            else:
                lines.append(prefix)
                self._write_value(value, level + self.indent, lines)

    def _maybe_primitive_inline(self, seq: Sequence[Any]) -> bool:
        """Return True if seq should be serialized as an inline primitive array.

        Conditions: non-empty, all items are scalars (not Mapping, not non-string Sequence),
        and none contain newlines.
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

    def _write_array(self, seq: Sequence[Any], level: int, lines: list[str]) -> None:
        """Write an array (list) to output lines.

        Uses tabular format if detected, otherwise writes list items with "-" prefix.

        Args:
            seq: Sequence to serialize
            level: Current indentation level
            lines: List of output lines to append to
        """
        # Root-level primitive inline array: [N]: v1,v2,v3
        if self._maybe_primitive_inline(seq):
            delim_char = self._delim_char
            bracket = self._delim_bracket
            cells = delim_char.join(self._format_cell(v) for v in seq)
            indent_str = self._get_indent(level)
            lines.append(indent_str + f"[{len(seq)}]{bracket}: {cells}")
            return

        schema = self._maybe_tabular(seq)
        if schema:
            self._write_table(seq, schema, level, lines)
            return

        indent_str = self._get_indent(level)
        prefix = indent_str + "-"
        for item in seq:
            inline_container = self._inline_container_repr(item)
            if inline_container is not None:
                lines.append(f"{prefix} {inline_container}")
                continue
            if self._is_inline(item):
                lines.append(f"{prefix} {self._format_scalar(item)}")
            else:
                lines.append(prefix)
                self._write_value(item, level + self.indent, lines)

    def _write_table_as_key(
        self,
        key: str,
        seq: Sequence[Mapping[str, Any]],
        schema: TabularSchema,
        level: int,
        lines: list[str],
    ) -> None:
        """Write a table using TOON SPEC v3.0 syntax: key[N<delim>]{field1<delim>field2}:"""
        key_formatted = format_key(key)
        fields = self._delim_char.join(format_key(k) for k in schema.keys)
        header = f"{key_formatted}[{len(seq)}]{self._delim_bracket}{{{fields}}}:"
        indent_str = self._get_indent(level)
        lines.append(indent_str + header)
        inner_indent = self._get_indent(level + 1)
        for row in seq:
            cells = self._delim_char.join(self._format_cell(row.get(k)) for k in schema.keys)
            lines.append(inner_indent + cells)

    def _write_table(
        self,
        seq: Sequence[Mapping[str, Any]],
        schema: TabularSchema,
        level: int,
        lines: list[str],
    ) -> None:
        """Write table using legacy @table syntax (for root-level arrays only).

        Note: This is kept for backward compatibility but should not be used
        for object values. Object values should use _write_table_as_key instead.

        Args:
            seq: Sequence of uniform objects
            schema: TabularSchema with field names
            level: Current indentation level
            lines: List of output lines to append to
        """
        header = ", ".join(format_key(key) for key in schema.keys)
        indent_str = self._get_indent(level)
        lines.append(indent_str + f"@table {header}")
        inner_indent = self._get_indent(level + 1)
        for row in seq:
            cells = []
            for key in schema.keys:
                value = row.get(key)
                cells.append(self._format_cell(value))
            # Optimized: join once
            row_str = " | ".join(cells)
            lines.append(inner_indent + f"| {row_str} |")

    def _maybe_tabular(self, seq: Sequence[Any]) -> TabularSchema | None:
        """Determine if a sequence should be serialized as a table.

        Checks if all items are uniform objects (same keys) and evaluates
        token savings based on the current mode.

        Args:
            seq: Sequence to evaluate

        Returns:
            TabularSchema if table format should be used, None otherwise
        """
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
        """Convert sequence to compact JSON string for size comparison.

        Args:
            seq: Sequence to linearize

        Returns:
            Compact JSON string (no extra whitespace)
        """
        from json import dumps

        return dumps(seq, separators=(",", ":"))

    def _is_inline(self, value: Any) -> bool:
        """Check if a value can be written inline (on same line as key).

        Objects and arrays require block format. Multiline strings also
        require block format.

        Args:
            value: Value to check

        Returns:
            True if value can be written inline, False if block format needed
        """
        if isinstance(value, Mapping):
            return False
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return False
        if isinstance(value, str) and "\n" in value:
            return False
        return True

    def _format_cell(self, value: Any) -> str:
        """Format a table cell value for comma-separated output.

        Values containing commas, pipes, or requiring quotes are properly
        escaped. Safe strings can remain unquoted.

        Args:
            value: Cell value to format

        Returns:
            Formatted string ready for table row
        """
        # Handle empty containers first ([] and {})
        inline = self._inline_container_repr(value)
        if inline is not None:
            return inline

        if isinstance(value, str):
            # If string contains comma, pipe, or needs quotes, use quoted format
            if "," in value or "|" in value or string_needs_quotes(value):
                return self._format_scalar(value)
            # Safe unquoted string
            return value
        # Non-string values use standard scalar formatting
        return self._format_scalar(value)

    def _format_scalar(self, value: Any, *, force_string: bool = False) -> str:
        """Format a scalar value for TOON output.

        Handles null, booleans, numbers, and strings. Uses JSON-compatible
        escaping for strings when needed.

        Args:
            value: Scalar value to format
            force_string: If True, convert non-strings to quoted strings

        Returns:
            Formatted string representation
        """
        if value is None and not force_string:
            return "null"
        if value is True and not force_string:
            return "true"
        if value is False and not force_string:
            return "false"
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
        if isinstance(value, str):
            if not force_string and not string_needs_quotes(value):
                return value
            return json.dumps(value)
        if force_string:
            return json.dumps(str(value))
        return self._format_scalar(str(value), force_string=True)

    def _try_fold(
        self,
        key: str,
        value: Any,
        siblings: Mapping,
        depth_remaining: float,
    ) -> tuple[str, Any] | None:
        """Try to fold 'key → {single_key: child}' into 'key.single_key'.

        Returns (folded_key_str, terminal_value) or None if folding is not safe.
        """
        from .utils import is_identifier_segment
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

    @staticmethod
    def _inline_container_repr(value: Any) -> str | None:
        """Get inline representation for empty containers.

        Empty objects and arrays can be written inline as {} or [].

        Args:
            value: Value to check

        Returns:
            "{}" for empty dict, "[]" for empty list, None otherwise
        """
        # Optimization: Check emptiness first (cheaper than isinstance for non-empty)
        if not value:
            if isinstance(value, Mapping):
                return "{}"
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                return "[]"
        return None


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
