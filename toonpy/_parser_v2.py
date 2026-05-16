"""
Lexer and parser for TOON (Token-Oriented Object Notation).
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import json
import re
from typing import List, Sequence, Tuple

from .errors import ToonSyntaxError
from .utils import (
    guess_number,
    is_safe_identifier,
    split_escaped_row,
)

__all__ = ["from_toon"]

COMMENT_PREFIXES = ("#", "//")
TABLE_PREFIX = "@table"

# Caché de literales comunes para optimización (O(1) lookup)
_LITERAL_CACHE = {
    "true": True, "True": True, "TRUE": True,
    "false": False, "False": False, "FALSE": False,
    "null": None, "None": None, "NULL": None,
}

# Regex compilados a nivel de módulo para mejor rendimiento
_QUOTED_TABLE_PATTERN = re.compile(r'^"([^"]+)"\[(\d+)\]\{([^}]+)\}:$')
_UNQUOTED_TABLE_PATTERN = re.compile(r'^([A-Za-z_][A-Za-z0-9_.]*)\[(\d+)\]\{([^}]+)\}:$')


@dataclass(slots=True)
class Line:
    """Represents a single line of TOON source code.

    Attributes:
        indent: Number of leading spaces (indentation level)
        content: Line content without leading whitespace or comments
        line_no: Original line number in source (1-indexed)
    """
    indent: int
    content: str
    line_no: int


class ToonLexer:
    """Lexer that tokenizes TOON source into lines with indentation tracking.

    Handles comment removal (block and inline), normalizes line endings,
    and validates indentation (tabs are forbidden).
    """

    def __init__(self, source: str) -> None:
        """Initialize the lexer.

        Args:
            source: Raw TOON source text
        """
        # Optimización: normalizar line endings una sola vez
        self.source = source.replace("\r\n", "\n").replace("\r", "\n") if "\r" in source else source

    def iter_lines(self) -> List[Line]:
        """Tokenize source into Line objects.

        Removes comments, normalizes whitespace, and validates indentation.
        Blank lines are skipped.

        Returns:
            List of Line objects with indent, content, and line numbers

        Raises:
            ToonSyntaxError: If tabs are used for indentation or block comments
                            are unterminated
        """
        text = self._remove_block_comments(self.source)
        lines: List[Line] = []
        for idx, raw in enumerate(text.split("\n"), start=1):
            stripped = self._strip_inline_comment(raw)
            if not stripped.strip():
                continue
            leading = len(stripped) - len(stripped.lstrip(" \t"))
            prefix = stripped[:leading]
            if "\t" in prefix:
                raise ToonSyntaxError("Tabs are not allowed for indentation", idx, 1)
            indent = len(prefix)
            content = stripped[leading:].rstrip()
            lines.append(Line(indent=indent, content=content, line_no=idx))
        return lines

    @staticmethod
    def _remove_block_comments(text: str) -> str:
        """Remove block comments (/* ... */) from source, preserving structure.

        Supports nested comments. Commented content is replaced with spaces
        (or newlines) to preserve line structure.

        Args:
            text: Source text with potential block comments

        Returns:
            Text with block comments removed

        Raises:
            ToonSyntaxError: If block comment is unterminated
        """
        # Early return si no hay comentarios de bloque
        if "/*" not in text:
            return text

        # Usar StringIO para mejor rendimiento con strings largos
        result = StringIO()
        i = 0
        depth = 0
        text_len = len(text)

        while i < text_len:
            # Optimización: verificar dos caracteres a la vez
            if i + 1 < text_len:
                two_char = text[i:i+2]
                if two_char == "/*":
                    depth += 1
                    i += 2
                    continue
                if depth > 0 and two_char == "*/":
                    depth -= 1
                    i += 2
                    continue

            if depth > 0:
                # Preservar newlines para mantener números de línea
                result.write('\n' if text[i] == '\n' else ' ')
            else:
                result.write(text[i])

            i += 1

        if depth != 0:
            raise ToonSyntaxError("Unterminated block comment")

        return result.getvalue()

    @staticmethod
    def _strip_inline_comment(line: str) -> str:
        """Remove inline comments (# or //) from a line, respecting strings.

        Comments inside quoted strings are preserved. Handles escape sequences
        correctly.

        Args:
            line: Single line of source code

        Returns:
            Line with inline comments removed (trailing whitespace also removed)
        """
        buf: List[str] = []
        in_string = False
        i = 0
        line_len = len(line)

        while i < line_len:
            ch = line[i]

            # Manejar escape: consumir el backslash y el siguiente carácter
            if ch == "\\" and i + 1 < line_len:
                buf.append(ch)
                buf.append(line[i + 1])
                i += 2
                continue

            if ch == "\"":
                buf.append(ch)
                in_string = not in_string
                i += 1
                continue

            if not in_string:
                if ch == "#":
                    break
                # Optimizar chequeo de //
                if ch == "/" and i + 1 < line_len and line[i + 1] == "/":
                    break

            buf.append(ch)
            i += 1

        return "".join(buf).rstrip()


class ToonParser:
    """Parser that converts TOON text into Python objects.

    Implements a recursive descent parser with indentation-based structure
    recognition. Supports objects, arrays, tables, scalars, and multiline strings.
    """

    def __init__(self, source: str, *, permissive: bool = False) -> None:
        """Initialize the parser.

        Args:
            source: TOON source text to parse
            permissive: If True, relaxes some validation rules (e.g., identifier
                       safety, numeric precision) for easier migration
        """
        self.lines = ToonLexer(source).iter_lines()
        self.permissive = permissive

    def parse(self) -> object:
        """Parse the TOON source and return the root value.

        Returns:
            Python object (dict, list, or scalar) representing the TOON document

        Raises:
            ToonSyntaxError: If source is empty, has syntax errors, or contains
                            unexpected content after the root value
        """
        if not self.lines:
            raise ToonSyntaxError("Empty TOON document")
        value, next_index = self._parse_value(0)
        if next_index != len(self.lines):
            extra = self.lines[next_index]
            raise ToonSyntaxError("Unexpected content after end of document", extra.line_no, 1)
        return value

    def _parse_value(self, index: int) -> Tuple[object, int]:
        """Parse a value starting at the given line index.

        Dispatches to appropriate parser based on line content (array, table,
        object, or scalar).

        Args:
            index: Line index to start parsing from

        Returns:
            Tuple of (parsed value, next line index)
        """
        line = self.lines[index]
        if self._is_array_line(line.content):
            return self._parse_array(index, line.indent)
        if line.content.startswith(TABLE_PREFIX):
            return self._parse_table(index, line.indent)
        key, value = self._split_key_value(line.content)
        if key is not None:
            return self._parse_object(index, line.indent)
        return self._parse_scalar_line(index)

    def _parse_object(self, start: int, indent: int) -> Tuple[object, int]:
        """Parse an object (dict) starting at given line index.

        Handles key-value pairs, nested objects, arrays, and table syntax.
        Detects spec-compliant table headers (key[N]{fields}:) and parses them.

        Args:
            start: Line index of first object entry
            indent: Expected indentation level for object entries

        Returns:
            Tuple of (parsed dict, next line index)

        Raises:
            ToonSyntaxError: If object structure is invalid or keys are malformed
        """
        result: dict[str, object] = {}
        index = start
        while index < len(self.lines):
            line = self.lines[index]
            if line.indent != indent:
                break
            # Check for table syntax: key[N]{field1,field2}:
            table_match = self._parse_table_header_syntax(line.content)
            if table_match:
                key, length, fields = table_match
                value, next_index = self._parse_table_from_header(index, fields, length, indent)
                result[key] = value
                index = next_index
                continue
            key_text, value_text = self._split_key_value(line.content)
            if key_text is None:
                break
            key = self._parse_key(key_text, line)
            if value_text == "":
                child_index = index + 1
                if child_index >= len(self.lines):
                    raise ToonSyntaxError("Missing block for key", line.line_no, 1)
                child_line = self.lines[child_index]
                if child_line.indent <= indent:
                    raise ToonSyntaxError("Expected indented block", child_line.line_no, 1)
                value, next_index = self._parse_value(child_index)
                index = next_index
            else:
                value, next_index = self._parse_inline_value(index, value_text)
                index = next_index
            result[key] = value
        return result, index

    def _parse_inline_value(self, index: int, token: str) -> Tuple[object, int]:
        """Parse an inline value (on same line as key).

        Handles multiline string markers and regular tokens.

        Args:
            index: Current line index
            token: Token string to parse

        Returns:
            Tuple of (parsed value, next line index)
        """
        line = self.lines[index]
        if token == '"""':
            text, next_index = self._consume_multiline_string(index + 1)
            return text, next_index
        return self._parse_token(token, line), index + 1

    def _parse_array(self, start: int, indent: int) -> Tuple[object, int]:
        """Parse an array (list) starting with "-" markers.

        Supports inline values, nested objects, and block-formatted items.
        Handles objects-as-list-items syntax (e.g., "- key: value").

        Args:
            start: Line index of first array item
            indent: Expected indentation level for array items

        Returns:
            Tuple of (list of parsed values, next line index)

        Raises:
            ToonSyntaxError: If array structure is invalid or items are malformed
        """
        values: List[object] = []
        index = start
        while index < len(self.lines):
            line = self.lines[index]
            if line.indent != indent or not self._is_array_line(line.content):
                break
            rest = line.content[1:].strip()
            inline_key_text, inline_value_text = self._split_key_value(rest) if rest else (None, "")
            if inline_key_text is not None:
                obj: dict[str, object] = {}
                key = self._parse_key(inline_key_text, line)
                if inline_value_text:
                    obj[key] = self._parse_token(inline_value_text, line)
                else:
                    child_index = index + 1
                    if child_index >= len(self.lines) or self.lines[child_index].indent <= indent:
                        raise ToonSyntaxError("Expected block for inline object entry", line.line_no, 1)
                    value, next_index = self._parse_value(child_index)
                    obj[key] = value
                    index = next_index
                    values.append(obj)
                    continue
                child_index = index + 1
                if child_index < len(self.lines) and self.lines[child_index].indent > indent:
                    nested_obj, next_index = self._parse_object(child_index, self.lines[child_index].indent)
                    obj.update(nested_obj)
                    index = next_index
                else:
                    index += 1
                values.append(obj)
                continue
            if rest:
                value, next_index = self._parse_inline_value(index, rest)
            else:
                child_index = index + 1
                if child_index >= len(self.lines):
                    raise ToonSyntaxError("Expected value for array element", line.line_no, 1)
                child_line = self.lines[child_index]
                if child_line.indent <= indent:
                    raise ToonSyntaxError("Expected indented array item", child_line.line_no, 1)
                value, next_index = self._parse_value(child_index)
            values.append(value)
            index = next_index
        return values, index

    def _parse_table_header_syntax(self, content: str) -> Tuple[str, int, List[str]] | None:
        """Parse TOON SPEC v2.0 table header syntax: key[N]{field1,field2}:.

        Supports both quoted and unquoted keys. Extracts the key name, declared
        row count, and field list.

        Args:
            content: Line content to parse

        Returns:
            Tuple of (key, length, fields) if syntax matches, None otherwise
        """
        content = content.strip()
        # Pattern: key[N]{field1,field2}: where key can be quoted or unquoted
        # Try quoted key first: "key"[N]{fields}:
        match = _QUOTED_TABLE_PATTERN.match(content)
        if match:
            key = match.group(1)
            length = int(match.group(2))
            fields_str = match.group(3)
            fields = [f.strip() for f in fields_str.split(",") if f.strip()]
            return (key, length, fields)
        # Try unquoted key: key[N]{fields}:
        match = _UNQUOTED_TABLE_PATTERN.match(content)
        if match:
            key = match.group(1)
            length = int(match.group(2))
            fields_str = match.group(3)
            fields = [f.strip() for f in fields_str.split(",") if f.strip()]
            return (key, length, fields)
        return None

    def _parse_table_from_header(
        self, start: int, fields: List[str], expected_length: int, indent: int
    ) -> Tuple[List[dict[str, object]], int]:
        """Parse table rows following a key[N]{fields}: header.

        Args:
            start: Index of the header line
            fields: List of field names from the header
            expected_length: Expected number of rows (from [N] in header)
            indent: Indentation level of the header

        Returns:
            Tuple of (parsed rows list, next line index)

        Raises:
            ToonSyntaxError: If row count doesn't match expected_length or row format is invalid
        """
        rows: List[dict[str, object]] = []
        index = start + 1
        header_line = self.lines[start]

        while index < len(self.lines):
            line = self.lines[index]
            if line.indent <= indent:
                break
            # Parse comma-separated values
            values = split_escaped_row(line.content.strip(), separator=",")
            if not values:
                values = [v.strip() for v in line.content.strip().split(",") if v.strip()]
            if len(values) != len(fields):
                raise ToonSyntaxError(
                    f"Expected {len(fields)} values in table row, got {len(values)}",
                    line.line_no,
                    1,
                )
            # Usar dict comprehension para mejor rendimiento
            row = {key: self._parse_token(token.strip(), line)
                   for key, token in zip(fields, values)}
            rows.append(row)
            index += 1

        # Validate that we parsed the expected number of rows
        if len(rows) != expected_length:
            raise ToonSyntaxError(
                f"Table header declares {expected_length} rows, but found {len(rows)} rows",
                header_line.line_no,
                1,
            )

        return rows, index

    def _parse_table(self, start: int, indent: int) -> Tuple[List[dict[str, object]], int]:
        """Parse legacy @table syntax (for backward compatibility).

        Note: This is kept for compatibility but the spec-compliant format
        uses key[N]{fields}: syntax parsed by _parse_table_from_header.

        Args:
            start: Line index of @table header
            indent: Indentation level of the table

        Returns:
            Tuple of (list of row dicts, next line index)

        Raises:
            ToonSyntaxError: If header is missing or row format is invalid
        """
        header_line = self.lines[start]
        header_text = header_line.content[len(TABLE_PREFIX) :].strip()
        if not header_text:
            raise ToonSyntaxError("Missing header for table", header_line.line_no, 1)
        header = [self._parse_key(part.strip(), header_line) for part in self._split_header(header_text)]
        rows: List[dict[str, object]] = []
        index = start + 1
        while index < len(self.lines):
            line = self.lines[index]
            if line.indent <= indent:
                break
            values = split_escaped_row(line.content, separator="|") or line.content.split(",")
            values = [value.strip() for value in values if value.strip()]
            if len(values) != len(header):
                raise ToonSyntaxError(
                    f"Expected {len(header)} values in table row, got {len(values)}",
                    line.line_no,
                    1,
                )
            # Usar dict comprehension para mejor rendimiento
            row = {key: self._parse_token(token, line)
                   for key, token in zip(header, values)}
            rows.append(row)
            index += 1
        return rows, index

    def _parse_scalar_line(self, index: int) -> Tuple[object, int]:
        """Parse a scalar value from a single line.

        Args:
            index: Line index to parse

        Returns:
            Tuple of (parsed scalar value, next line index)
        """
        line = self.lines[index]
        return self._parse_token(line.content, line), index + 1

    def _parse_token(self, token: str, line: Line) -> object:
        """Parse a single token into a Python value.

        Handles null, booleans, numbers, strings (quoted and unquoted),
        empty containers, and safe identifiers.

        Args:
            token: Token string to parse
            line: Line object for error reporting

        Returns:
            Parsed Python value (None, bool, int, float, str, [], {})

        Raises:
            ToonSyntaxError: If token is invalid or empty
        """
        token = token.strip()
        if not token:
            raise ToonSyntaxError("Empty value", line.line_no, 1)

        # Caché de literales comunes (O(1) lookup) - evita .lower() innecesario
        # Usar 'in' en lugar de .get() porque None es un valor válido
        if token in _LITERAL_CACHE:
            return _LITERAL_CACHE[token]

        # Contenedores vacíos
        if token == "[]":
            return []
        if token == "{}":
            return {}

        # Strings con comillas (verificar primer carácter es más rápido)
        first_char = token[0]
        if first_char == "\"":
            if token.startswith('"""'):
                if token.endswith('"""') and len(token) >= 6:
                    return token[3:-3]
                raise ToonSyntaxError("Unterminated multiline string", line.line_no, 1)
            return self._parse_string_literal(token, line)

        # Números (optimización: verificar primer carácter antes de llamar función)
        if first_char.isdigit() or (first_char == '-' and len(token) > 1):
            number = guess_number(token)
            if number is not None:
                return number

        # Identificadores seguros
        if is_safe_identifier(token):
            return token

        if self.permissive:
            return token

        raise ToonSyntaxError("Invalid unquoted string literal", line.line_no, 1)

    def _parse_key(self, token: str, line: Line) -> str:
        """Parse a key (object key or table field name).

        Keys can be quoted strings or safe identifiers. In strict mode,
        unquoted keys must match identifier rules.

        Args:
            token: Key token to parse (already stripped by caller)
            line: Line object for error reporting

        Returns:
            Parsed key string

        Raises:
            ToonSyntaxError: If key is invalid (in strict mode)
        """
        # Nota: token ya viene stripped desde _split_key_value
        if token and token[0] == "\"":
            return self._parse_string_literal(token, line)
        if not is_safe_identifier(token):
            if self.permissive:
                return token
            raise ToonSyntaxError("Keys must be safe identifiers or quoted strings", line.line_no, 1)
        return token

    def _parse_string_literal(self, token: str, line: Line) -> str:
        """Parse a quoted string literal using JSON-compatible rules.

        Uses json.loads for proper escape sequence handling (\\n, \\t, etc.).

        Args:
            token: Quoted string token (including quotes)
            line: Line object for error reporting

        Returns:
            Unquoted string value

        Raises:
            ToonSyntaxError: If string literal is malformed
        """
        try:
            return json.loads(token)
        except json.JSONDecodeError as exc:
            raise ToonSyntaxError(f"Invalid string literal: {exc.msg}", line.line_no, exc.colno) from None

    def _consume_multiline_string(self, index: int) -> Tuple[str, int]:
        """Consume a multiline string (triple-quoted) starting at given index.

        Reads lines until finding the closing triple-quote marker. Preserves
        newlines in the content.

        Args:
            index: Line index to start reading from (after opening triple-quote)

        Returns:
            Tuple of (multiline string content, next line index after closing)

        Raises:
            ToonSyntaxError: If multiline string is unterminated or has content
                            after the closing marker
        """
        parts: List[str] = []
        while index < len(self.lines):
            line = self.lines[index]
            end = line.content.find('"""')
            if end != -1:
                snippet = line.content[:end]
                if snippet:
                    parts.append(snippet)
                suffix = line.content[end + 3 :].strip()
                if suffix:
                    raise ToonSyntaxError("Unexpected content after multiline terminator", line.line_no, end + 3)
                return "\n".join(parts), index + 1
            parts.append(line.content)
            index += 1
        raise ToonSyntaxError("Unterminated multiline string", self.lines[index - 1].line_no, 1)

    @staticmethod
    def _split_key_value(text: str) -> Tuple[str | None, str]:
        """Split a line into key and value parts at the first colon.

        Respects colons inside quoted strings. Handles escape sequences.

        Args:
            text: Line content to split

        Returns:
            Tuple of (key, value) if colon found, (None, "") otherwise
        """
        in_string = False
        escape = False
        for idx, ch in enumerate(text):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == "\"":
                in_string = not in_string
                continue
            if ch == ":" and not in_string:
                key = text[:idx].strip()
                value = text[idx + 1 :].strip()
                if key:
                    return key, value
        return None, ""

    @staticmethod
    def _split_header(text: str) -> Sequence[str]:
        """Split a table header into field names.

        Supports comma-separated or space-separated field lists.

        Args:
            text: Header text (field list)

        Returns:
            List of field name strings

        Raises:
            ToonSyntaxError: If header is empty
        """
        if "," in text:
            parts = [part.strip() for part in text.split(",") if part.strip()]
        else:
            parts = [part for part in text.split() if part]
        if not parts:
            raise ToonSyntaxError("Empty table header")
        return parts

    @staticmethod
    def _is_array_line(content: str) -> bool:
        """Check if a line represents an array item (starts with "-").

        Args:
            content: Line content to check

        Returns:
            True if line is an array item marker
        """
        return content == "-" or content.startswith("- ")


def from_toon(source: str, *, permissive: bool = False) -> object:
    """Parse a TOON string into a Python object.

    Convenience function that creates a ToonParser and parses the source.

    Args:
        source: TOON-formatted string to parse
        permissive: If True, relaxes validation rules for easier migration

    Returns:
        Python object (dict, list, or scalar) representing the TOON document

    Raises:
        ToonSyntaxError: If source has syntax errors or is malformed

    Example:
        >>> text = 'crew[1]{id,name}:\\n  1,Luz'
        >>> data = from_toon(text)
        >>> data['crew'][0]['name']
        'Luz'
    """
    return ToonParser(source, permissive=permissive).parse()
