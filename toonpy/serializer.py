"""
Serializer that converts Python objects into TOON text.
"""

from __future__ import annotations

import json
from typing import Any, Literal, Mapping, Sequence

from .utils import TabularSchema, format_key, string_needs_quotes, tabular_schema

mode_type = Literal["auto", "compact", "readable"]

__all__ = ["to_toon"]


class ToonSerializer:
    """Serializer that converts Python objects to TOON format text.
    
    Handles objects, arrays, scalars, and automatically detects tabular arrays
    for efficient serialization according to TOON SPEC v2.0.
    """
    
    def __init__(self, *, indent: int = 2, mode: mode_type = "auto") -> None:
        """Initialize the serializer.
        
        Args:
            indent: Number of spaces per indentation level (default: 2)
            mode: Serialization mode - "auto" (smart tabular detection),
                  "compact" (always use tables when possible), or "readable"
                  (only use tables when savings > 10 tokens)
        """
        self.indent = indent
        self.mode = mode
        # Cache de indentaciones comunes (0-20 niveles)
        self._indent_cache: dict[int, str] = {}
        self._max_cached_indent = 20

    def dumps(self, obj: Any) -> str:
        """Serialize a Python object to TOON format string.
        
        Args:
            obj: Python object (dict, list, scalar) compatible with JSON model
            
        Returns:
            TOON-formatted string with trailing newline
        """
        lines: list[str] = []
        self._write_value(obj, 0, lines)
        # Optimización: usar join una sola vez en lugar de múltiples concatenaciones
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
        indent_str = self._get_indent(level)
        if isinstance(obj, Mapping):
            if not obj:
                lines.append(indent_str + "{}")
                return
            self._write_object(obj, level, lines)
        elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
            if not obj:
                lines.append(indent_str + "[]")
                return
            self._write_array(obj, level, lines)
        else:
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
            key_repr = format_key(str(key))  # Uses cache internally
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

    def _write_array(self, seq: Sequence[Any], level: int, lines: list[str]) -> None:
        """Write an array (list) to output lines.
        
        Uses tabular format if detected, otherwise writes list items with "-" prefix.
        
        Args:
            seq: Sequence to serialize
            level: Current indentation level
            lines: List of output lines to append to
        """
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
        """Write a table using TOON SPEC v2.0 syntax: key[N]{field1,field2}:.
        
        This is the spec-compliant format for tabular arrays within objects.
        Rows are comma-separated and indented.
        
        Args:
            key: Object key name (will be formatted/quoted if needed)
            seq: Sequence of uniform objects (all have same keys)
            schema: TabularSchema with field names and savings estimate
            level: Current indentation level
            lines: List of output lines to append to
        """
        # Format the key (may add quotes if needed)
        key_formatted = format_key(key)
        fields = ",".join(format_key(k) for k in schema.keys)
        header = f"{key_formatted}[{len(seq)}]{{{fields}}}:"
        indent_str = self._get_indent(level)
        lines.append(indent_str + header)
        inner_indent = self._get_indent(level + 1)
        for row in seq:
            cells = []
            for key in schema.keys:
                value = row.get(key)
                cells.append(self._format_cell(value))
            # Use comma as delimiter per spec - optimizado: join una vez
            row_str = ",".join(cells)
            lines.append(inner_indent + row_str)

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
            # Optimizado: join una vez
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
        """Get inline representation for empty containers.
        
        Empty objects and arrays can be written inline as {} or [].
        
        Args:
            value: Value to check
            
        Returns:
            "{}" for empty dict, "[]" for empty list, None otherwise
        """
        if isinstance(value, Mapping) and not value:
            return "{}"
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) and not value:
            return "[]"
        return None


def to_toon(obj: Any, *, indent: int = 2, mode: mode_type = "auto") -> str:
    """Convert a Python object to TOON format string.
    
    Convenience function that creates a ToonSerializer and serializes the object.
    
    Args:
        obj: Python object compatible with JSON model (dict, list, scalar)
        indent: Number of spaces per indentation level (default: 2)
        mode: Serialization mode - "auto" (smart), "compact", or "readable"
        
    Returns:
        TOON-formatted string
        
    Example:
        >>> data = {"crew": [{"id": 1, "name": "Luz"}]}
        >>> toon = to_toon(data, mode="auto")
        >>> "crew[1]{id,name}:" in toon
        True
    """
    return ToonSerializer(indent=indent, mode=mode).dumps(obj)

