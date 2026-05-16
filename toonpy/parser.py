"""
Lexer and parser for TOON (Token-Oriented Object Notation) v3.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import json
import re
from typing import List, NamedTuple, Sequence, Tuple

from .errors import ToonSyntaxError
from .utils import guess_number, is_safe_identifier, split_row_v3

__all__ = ["from_toon"]

COMMENT_PREFIXES = ("#", "//")
# TABLE_PREFIX removed — @table is not part of v3 spec

# Sentinel used by lexer to mark blank lines in strict mode
_BLANK_SENTINEL = "\x00BLANK"

class HeaderSpec(NamedTuple):
    """Parsed result of a TOON array header line."""
    key: str | None        # None for root-level headers like [N]{fields}:
    length: int            # declared array length N
    fields: list[str]      # field names; empty list = primitive inline or list format
    delimiter: str         # active delimiter: "," "\t" or "|"
    inline_rest: str = ""  # text after the header's terminal colon (for inline arrays)

_LITERAL_CACHE = {
    "true": True, "True": True, "TRUE": True,
    "false": False, "False": False, "FALSE": False,
    "null": None, "None": None, "NULL": None,
}

# Matches all header forms:
#   optionally-quoted-key [N<delim?>] {fields}? :
#   or keyless [N<delim?>] {fields}? :
# Groups: quoted_key, unquoted_key, N, delim_char, fields_str, rest_after_colon
_HEADER_RE = re.compile(
    r'^(?:("(?:[^"\\]|\\.)*")|([A-Za-z_][A-Za-z0-9_.]*)|)'  # optional key
    r'\[(\d+)([|\t]?)\]'                                       # [N<delim?>]
    r'(?:\{([^}]*)\})?'                                        # optional {fields}
    r':(.*)$'                                                  # : and rest of line
)


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
    """Lexer that tokenizes TOON source into lines with indentation tracking."""

    def __init__(self, source: str, *, strict: bool = True, indent_size: int = 2) -> None:
        self.source = source.replace("\r\n", "\n").replace("\r", "\n") if "\r" in source else source
        self.strict = strict
        self.indent_size = indent_size

    def iter_lines(self) -> List[Line]:
        text = self._remove_block_comments(self.source)
        lines: List[Line] = []
        for idx, raw in enumerate(text.split("\n"), start=1):
            stripped = self._strip_inline_comment(raw)
            is_blank = not stripped.strip()
            if is_blank:
                if self.strict:
                    # Emit sentinel so array parsers can detect and error.
                    lines.append(Line(indent=-1, content=_BLANK_SENTINEL, line_no=idx))
                continue
            leading = len(stripped) - len(stripped.lstrip(" \t"))
            prefix = stripped[:leading]
            if "\t" in prefix:
                raise ToonSyntaxError("Tabs are not allowed for indentation", idx, 1)
            indent = len(prefix)
            if self.strict and indent > 0 and indent % self.indent_size != 0:
                raise ToonSyntaxError(
                    f"Indentation ({indent} spaces) is not a multiple of indent size ({self.indent_size})",
                    idx, 1,
                )
            content = stripped[leading:].rstrip()
            lines.append(Line(indent=indent, content=content, line_no=idx))
        return lines

    @staticmethod
    def _remove_block_comments(text: str) -> str:
        """Remove block comments (/* ... */) from source, preserving structure."""
        if "/*" not in text:
            return text

        result = StringIO()
        i = 0
        depth = 0
        text_len = len(text)

        while i < text_len:
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
                result.write('\n' if text[i] == '\n' else ' ')
            else:
                result.write(text[i])

            i += 1

        if depth != 0:
            raise ToonSyntaxError("Unterminated block comment")

        return result.getvalue()

    @staticmethod
    def _strip_inline_comment(line: str) -> str:
        """Remove inline comments (# or //) from a line, respecting strings."""
        buf: List[str] = []
        in_string = False
        i = 0
        line_len = len(line)

        while i < line_len:
            ch = line[i]

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
                if ch == "/" and i + 1 < line_len and line[i + 1] == "/":
                    break

            buf.append(ch)
            i += 1

        return "".join(buf).rstrip()


class ToonParser:
    """Parser that converts TOON v3 text into Python objects."""

    def __init__(
        self,
        source: str,
        *,
        strict: bool = True,
        permissive: bool = False,
        indent: int = 2,
        expand_paths: str = "off",
    ) -> None:
        self.strict = strict
        self.permissive = permissive
        self.expand_paths = expand_paths
        self._stored_indent = indent
        self.lines = ToonLexer(source, strict=strict, indent_size=indent).iter_lines()
        # Delimiter stack: fast path — if _delimiter_stack[-1] == "," use existing split logic
        self._delimiter_stack: list[str] = [","]

    def parse(self) -> object:
        # Skip blank sentinels to find real content
        real_lines = [l for l in self.lines if l.content != _BLANK_SENTINEL]
        if not real_lines:
            return {}  # empty document → empty object (v3 spec §5)

        first = real_lines[0]

        # Root array: first non-blank line is a keyless header [N]...
        header = self._parse_header_syntax(first.content)
        if header is not None and header.key is None:
            idx = self.lines.index(first)
            value, next_idx = self._dispatch_header(idx, header, indent=0)
            while next_idx < len(self.lines) and self.lines[next_idx].content == _BLANK_SENTINEL:
                next_idx += 1
            if next_idx != len(self.lines):
                extra = self.lines[next_idx]
                raise ToonSyntaxError("Unexpected content after root array", extra.line_no, 1)
            return value

        # Root object: line has a key: value pair
        if ":" in first.content:
            key, _ = self._split_key_value(first.content)
            if key is not None:
                idx = self.lines.index(first)
                value, next_idx = self._parse_object(idx, first.indent)
                while next_idx < len(self.lines) and self.lines[next_idx].content == _BLANK_SENTINEL:
                    next_idx += 1
                if next_idx != len(self.lines):
                    extra = self.lines[next_idx]
                    raise ToonSyntaxError("Unexpected content after document", extra.line_no, 1)
                if self.expand_paths != "off" and isinstance(value, dict):
                    from ._path_expansion import expand_paths as _ep
                    value = _ep(value, strict=self.strict)
                return value

        # Root primitive: entire line is the value
        if len(real_lines) == 1 or not self.strict:
            return self._parse_root_primitive(first)

        raise ToonSyntaxError(
            "Two primitives at root depth are not allowed in strict mode",
            real_lines[1].line_no, 1,
        )

    def _parse_root_primitive(self, line: Line) -> object:
        """Parse a root-level primitive (the entire line is the value).

        At root level, any single-line value is valid — including raw strings
        with spaces, Unicode, emoji, etc. Numbers and literals are recognized first.
        """
        content = line.content
        if content in _LITERAL_CACHE:
            return _LITERAL_CACHE[content]
        if content.startswith('"'):
            return self._parse_string_literal(content, line)
        if content and (content[0].isdigit() or content[0] == '-'):
            n = guess_number(content)
            if n is not None:
                return n
        # v3: root-level raw strings are always valid (spaces, unicode, emoji, etc.)
        return content

    def _parse_header_syntax(self, content: str) -> HeaderSpec | None:
        """Parse a TOON v3 array header line.

        Recognises all forms:
          key[N]:               → primitive inline (fields=[])
          key[N]{f1,f2}:        → tabular (comma)
          key[N|]{f1|f2}:       → tabular (pipe)
          key[N\\t]{f1\\tf2}:   → tabular (tab)
          [N]:                  → root list array (key=None)
          [N]{fields}:          → root tabular array (key=None)
        Quoted keys ("my-key") are supported.
        Returns None if the line is not a header.
        """
        m = _HEADER_RE.match(content.strip())
        if m is None:
            return None
        quoted_key, unquoted_key, n_str, delim_char, fields_str, rest = m.groups()
        if quoted_key is not None:
            try:
                key: str | None = json.loads(quoted_key)
            except Exception:
                return None
        elif unquoted_key is not None:
            key = unquoted_key
        else:
            key = None  # root-level header

        length = int(n_str)
        delimiter = delim_char if delim_char else ","

        if fields_str is not None:
            if fields_str.strip():
                # Use split_row_v3 to respect quoted field names containing delimiters
                raw_fields = split_row_v3(fields_str, delimiter)
                parsed_fields: list[str] = []
                for f in raw_fields:
                    f = f.strip()
                    if not f:
                        continue
                    if f.startswith('"'):
                        try:
                            f = json.loads(f)
                        except Exception:
                            pass
                    parsed_fields.append(f)
                fields = parsed_fields
            else:
                fields = []
            # Strict: field delimiter must match bracket delimiter
            if self.strict and fields_str and delimiter == "," and "\t" in fields_str:
                raise ToonSyntaxError("Delimiter mismatch between brackets and field list", None, None)
        else:
            fields = []

        # Capture the inline rest (text after the header's terminal colon)
        inline_rest = rest.strip() if rest else ""
        return HeaderSpec(key=key, length=length, fields=fields, delimiter=delimiter, inline_rest=inline_rest)

    def _dispatch_header(
        self, index: int, header: HeaderSpec, indent: int
    ) -> tuple[object, int]:
        """Route a parsed header to the correct array parser."""
        line = self.lines[index]
        # Use the inline_rest captured by _parse_header_syntax (avoids rfind issues)
        inline_rest = header.inline_rest

        if header.fields:
            # Tabular array
            self._delimiter_stack.append(header.delimiter)
            result, next_idx = self._parse_table_rows(
                index, header.fields, header.length, indent, header.delimiter
            )
            self._delimiter_stack.pop()
            return result, next_idx

        if inline_rest:
            # Primitive inline array: 'key[N]: v1,v2,v3'
            return self._parse_inline_array(
                inline_rest, header.length, header.delimiter, line, index
            )

        # List format array: 'key[N]:' followed by '- ' items
        if header.length == 0:
            return [], index + 1

        self._delimiter_stack.append(header.delimiter)
        result, next_idx = self._parse_list_items(
            index + 1, indent + self._stored_indent, header.length, line
        )
        self._delimiter_stack.pop()
        return result, next_idx

    def _parse_inline_array(
        self, inline_str: str, expected: int, delimiter: str, line: Line, line_index: int
    ) -> tuple[list, int]:
        """Parse 'key[N]: v1,v2,v3' — values after the colon, comma/tab/pipe separated."""
        if expected == 0:
            if inline_str:
                raise ToonSyntaxError(
                    "Array declared length 0 but has inline values", line.line_no, 1
                )
            return [], line_index + 1

        raw_cells = split_row_v3(inline_str, delimiter)
        if self.strict and len(raw_cells) != expected:
            raise ToonSyntaxError(
                f"Inline array declared {expected} items, got {len(raw_cells)}",
                line.line_no, 1,
            )
        values = [self._parse_token(cell.strip(), line) for cell in raw_cells]
        return values, line_index + 1

    def _parse_list_items(
        self, start: int, indent: int, expected: int, header_line: Line
    ) -> tuple[list, int]:
        """Parse '- ' delimited list items at given indent level.

        expected=-1 means no count validation (called without a declared header).
        """
        values: list = []
        index = start

        while index < len(self.lines):
            line = self.lines[index]

            # Blank sentinels inside arrays
            if line.content == _BLANK_SENTINEL:
                if self.strict:
                    # Check if there's another array item after this blank
                    # If not, this is a trailing blank — allowed even in strict mode
                    lookahead = index + 1
                    while lookahead < len(self.lines) and self.lines[lookahead].content == _BLANK_SENTINEL:
                        lookahead += 1
                    if lookahead < len(self.lines):
                        next_real = self.lines[lookahead]
                        if next_real.indent == indent and self._is_array_line(next_real.content):
                            raise ToonSyntaxError(
                                "Blank line inside array is not allowed in strict mode",
                                line.line_no, 1,
                            )
                index += 1
                continue

            if line.indent != indent or not self._is_array_line(line.content):
                break

            rest = line.content[2:] if line.content.startswith("- ") else line.content[1:]

            # Bare '-' → empty object {}
            if not rest.strip():
                values.append({})
                index += 1
                continue

            rest = rest.strip()

            # Check if rest is a nested keyless array header: '[N]...'
            nested_header = self._parse_header_syntax(rest)
            if nested_header is not None and nested_header.key is None:
                inner, next_idx = self._dispatch_header_from_rest(
                    index, nested_header, line, outer_indent=indent
                )
                values.append(inner)
                index = next_idx
                continue

            # Check if rest is a keyed header: 'key[N]{fields}:' as first field of object
            keyed_header = self._parse_header_syntax(rest)
            if keyed_header is not None and keyed_header.key is not None:
                obj, next_idx = self._parse_object_item_with_header(
                    index, keyed_header, line, indent
                )
                values.append(obj)
                index = next_idx
                continue

            # Regular object-as-list-item: '- key: value'
            inline_key_text, inline_value_text = self._split_key_value(rest)
            if inline_key_text is not None:
                obj_item: dict = {}
                key = self._parse_key(inline_key_text, line)
                if inline_value_text == "":
                    child_index = index + 1
                    while child_index < len(self.lines) and self.lines[child_index].content == _BLANK_SENTINEL:
                        child_index += 1
                    if child_index >= len(self.lines) or self.lines[child_index].indent <= indent:
                        raise ToonSyntaxError("Expected block for inline object entry", line.line_no, 1)
                    value, next_idx = self._parse_value(child_index)
                    obj_item[key] = value
                    index = next_idx
                else:
                    obj_item[key] = self._parse_token(inline_value_text, line)
                    index += 1

                # Continue reading sibling fields at indent + _stored_indent
                child_indent = indent + self._stored_indent
                while index < len(self.lines):
                    sib = self.lines[index]
                    if sib.content == _BLANK_SENTINEL:
                        # Blank lines between object fields are allowed (like _parse_object)
                        index += 1
                        continue
                    if sib.indent != child_indent:
                        break
                    sib_header = self._parse_header_syntax(sib.content)
                    if sib_header and sib_header.key:
                        sib_val, next_idx = self._dispatch_header(index, sib_header, child_indent)
                        obj_item[sib_header.key] = sib_val
                        index = next_idx
                        continue
                    sib_key_text, sib_val_text = self._split_key_value(sib.content)
                    if sib_key_text is None:
                        break
                    sib_key = self._parse_key(sib_key_text, sib)
                    if sib_val_text == "":
                        grandchild = index + 1
                        while grandchild < len(self.lines) and self.lines[grandchild].content == _BLANK_SENTINEL:
                            grandchild += 1
                        if grandchild >= len(self.lines) or self.lines[grandchild].indent <= child_indent:
                            raise ToonSyntaxError("Expected block for sibling key", sib.line_no, 1)
                        sib_val_parsed, next_idx = self._parse_value(grandchild)
                        obj_item[sib_key] = sib_val_parsed
                        index = next_idx
                    else:
                        obj_item[sib_key] = self._parse_token(sib_val_text, sib)
                        index += 1
                values.append(obj_item)
                continue

            # Scalar item: '- text' or '- 42'
            value, next_idx = self._parse_inline_value(index, rest)
            values.append(value)
            index = next_idx

        # expected=-1 means no count validation
        if expected >= 0 and self.strict and len(values) != expected:
            raise ToonSyntaxError(
                f"Array declared {expected} items, found {len(values)}",
                header_line.line_no, 1,
            )
        return values, index

    def _dispatch_header_from_rest(
        self, index: int, header: HeaderSpec, line: Line, outer_indent: int
    ) -> tuple[object, int]:
        """Handle a nested keyless header that appears on a '- ' item line.
        e.g., '  - [2]: 1,2' or '  - [2]{id,name}:' + rows
        """
        # Use the inline_rest from the header (avoids rfind colon issues with values containing ':')
        rest_after_colon = header.inline_rest

        if header.fields:
            # Tabular nested: stop at outer_indent+2 (sibling level)
            self._delimiter_stack.append(header.delimiter)
            result, next_idx = self._parse_table_rows(
                index, header.fields, header.length, outer_indent + self._stored_indent, header.delimiter
            )
            self._delimiter_stack.pop()
            return result, next_idx

        if rest_after_colon:
            return self._parse_inline_array(
                rest_after_colon, header.length, header.delimiter, line, index
            )

        if header.length == 0:
            return [], index + 1

        self._delimiter_stack.append(header.delimiter)
        result, next_idx = self._parse_list_items(
            index + 1, outer_indent + self._stored_indent, header.length, line
        )
        self._delimiter_stack.pop()
        return result, next_idx

    def _parse_object_item_with_header(
        self, index: int, header: HeaderSpec, line: Line, outer_indent: int
    ) -> tuple[dict, int]:
        """Handle '- key[N]{fields}:' as first field of a list-item object.
        Per spec §10: tabular rows at depth+2, sibling fields at depth+1.
        """
        obj: dict = {}
        # The header's array value; stop level = outer_indent + _stored_indent (sibling level)
        array_val, next_idx = self._dispatch_header(index, header, outer_indent + self._stored_indent)
        obj[header.key] = array_val
        child_indent = outer_indent + self._stored_indent
        index = next_idx
        while index < len(self.lines):
            sib = self.lines[index]
            if sib.content == _BLANK_SENTINEL:
                # Blank lines between object fields are allowed
                index += 1
                continue
            if sib.indent != child_indent:
                break
            sib_key_text, sib_val_text = self._split_key_value(sib.content)
            if sib_key_text is None:
                break
            sib_key = self._parse_key(sib_key_text, sib)
            if sib_val_text == "":
                grandchild = index + 1
                while grandchild < len(self.lines) and self.lines[grandchild].content == _BLANK_SENTINEL:
                    grandchild += 1
                sib_val_parsed, next_idx2 = self._parse_value(grandchild)
                obj[sib_key] = sib_val_parsed
                index = next_idx2
            else:
                obj[sib_key] = self._parse_token(sib_val_text, sib)
                index += 1
        return obj, index

    def _parse_table_rows(
        self, start: int, fields: list[str], expected_length: int, indent: int, delimiter: str
    ) -> tuple[list[dict], int]:
        """Parse tabular rows following a key[N]{fields}: header."""
        rows: list[dict] = []
        index = start + 1
        header_line = self.lines[start]

        while index < len(self.lines):
            line = self.lines[index]

            if line.content == _BLANK_SENTINEL:
                if self.strict:
                    # Only error if there's another table row after this blank
                    # Trailing blanks are allowed even in strict mode
                    lookahead = index + 1
                    while lookahead < len(self.lines) and self.lines[lookahead].content == _BLANK_SENTINEL:
                        lookahead += 1
                    if lookahead < len(self.lines) and self.lines[lookahead].indent > indent:
                        raise ToonSyntaxError(
                            "Blank line inside tabular array is not allowed in strict mode",
                            line.line_no, 1,
                        )
                index += 1
                continue

            if line.indent <= indent:
                break

            raw_cells = split_row_v3(line.content.strip(), delimiter)
            if self.strict and len(raw_cells) != len(fields):
                raise ToonSyntaxError(
                    f"Tabular row has {len(raw_cells)} values, expected {len(fields)}",
                    line.line_no, 1,
                )
            row = {k: self._parse_token(cell.strip(), line) for k, cell in zip(fields, raw_cells)}
            rows.append(row)
            index += 1

        if self.strict and len(rows) != expected_length:
            raise ToonSyntaxError(
                f"Table declares {expected_length} rows, found {len(rows)}",
                header_line.line_no, 1,
            )
        return rows, index

    def _parse_object(self, start: int, indent: int) -> tuple[object, int]:
        result: dict[str, object] = {}
        index = start
        while index < len(self.lines):
            line = self.lines[index]

            # Skip blank sentinels — allowed between object fields
            if line.content == _BLANK_SENTINEL:
                index += 1
                continue

            if line.indent != indent:
                break

            # Array header: key[N]{fields}: or key[N]:
            header = self._parse_header_syntax(line.content)
            if header is not None and header.key is not None:
                value, next_idx = self._dispatch_header(index, header, indent)
                result[header.key] = value
                index = next_idx
                continue

            key_text, value_text = self._split_key_value(line.content)
            if key_text is None:
                break
            key = self._parse_key(key_text, line)

            if value_text == "":
                child_index = index + 1
                while child_index < len(self.lines) and self.lines[child_index].content == _BLANK_SENTINEL:
                    child_index += 1
                if child_index >= len(self.lines) or self.lines[child_index].indent <= indent:
                    # Empty value with no following child block → empty object
                    result[key] = {}
                    index = child_index if child_index < len(self.lines) else len(self.lines)
                    continue
                child_line = self.lines[child_index]
                # In strict mode: bare identifiers without ':' are not valid as block values.
                # Valid non-key:value block content: quoted strings, numbers, literals,
                # empty containers, arrays (- ...), headers (key[N]:), multiline strings.
                if (self.strict
                        and not self._is_array_line(child_line.content)
                        and self._parse_header_syntax(child_line.content) is None
                        and child_line.content not in _LITERAL_CACHE
                        and child_line.content not in ("[]", "{}")
                        and not child_line.content.startswith('"')
                        and child_line.content != _BLANK_SENTINEL):
                    cl = child_line.content
                    # Exclude numbers and negative numbers
                    is_num_like = (cl and (cl[0].isdigit() or (cl[0] == '-' and len(cl) > 1)))
                    if not is_num_like:
                        _key_val, _ = self._split_key_value(child_line.content)
                        if _key_val is None:
                            raise ToonSyntaxError(
                                "Missing colon in key-value context", child_line.line_no, 1
                            )
                value, next_idx = self._parse_value(child_index)
                index = next_idx
            else:
                value, next_idx = self._parse_inline_value(index, value_text)
                index = next_idx

            result[key] = value
        return result, index

    def _parse_value(self, index: int) -> tuple[object, int]:
        line = self.lines[index]
        if line.content == _BLANK_SENTINEL:
            raise ToonSyntaxError("Unexpected blank line", line.line_no, 1)
        header = self._parse_header_syntax(line.content)
        if header is not None and header.key is not None:
            return self._dispatch_header(index, header, line.indent)
        if self._is_array_line(line.content):
            return self._parse_list_items(index, line.indent, expected=-1, header_line=line)
        key, value = self._split_key_value(line.content)
        if key is not None:
            return self._parse_object(index, line.indent)
        return self._parse_root_primitive(line), index + 1

    def _parse_inline_value(self, index: int, token: str) -> Tuple[object, int]:
        """Parse an inline value (on same line as key)."""
        line = self.lines[index]
        if token == '"""':
            text, next_index = self._consume_multiline_string(index + 1)
            return text, next_index
        return self._parse_token(token, line), index + 1

    def _parse_scalar_line(self, index: int) -> Tuple[object, int]:
        """Parse a scalar value from a single line."""
        line = self.lines[index]
        return self._parse_token(line.content, line), index + 1

    def _parse_token(self, token: str, line: Line) -> object:
        """Parse a single token into a Python value."""
        token = token.strip()
        if not token:
            # v3: empty token in array context → empty string
            return ""

        if token in _LITERAL_CACHE:
            return _LITERAL_CACHE[token]

        if token == "[]":
            return []
        if token == "{}":
            return {}

        first_char = token[0]
        if first_char == "\"":
            if token.startswith('"""'):
                if token.endswith('"""') and len(token) >= 6:
                    return token[3:-3]
                raise ToonSyntaxError("Unterminated multiline string", line.line_no, 1)
            return self._parse_string_literal(token, line)

        if first_char.isdigit() or (first_char == '-' and len(token) > 1):
            number = guess_number(token)
            if number is not None:
                return number

        # v3: unquoted tokens without spaces are valid raw strings.
        # This includes Unicode chars, leading-zero numbers (as strings), commas, etc.
        # Tokens WITH spaces are only valid when permissive or as root primitives
        # (root primitives bypass _parse_token entirely via _parse_root_primitive).
        if ' ' not in token:
            return token

        if self.permissive:
            return token

        raise ToonSyntaxError("Invalid unquoted string literal", line.line_no, 1)

    def _parse_key(self, token: str, line: Line) -> str:
        """Parse a key (object key or table field name).

        In v3, unquoted keys can contain dots, brackets, underscores and hyphens
        in addition to alphanumeric chars. Quoted keys support any characters.
        """
        if token and token[0] == "\"":
            return self._parse_string_literal(token, line)
        # v3: allow any non-empty token as a key (already validated by _split_key_value
        # which only splits on unquoted colons). Reject only empty keys.
        if not token:
            raise ToonSyntaxError("Empty key", line.line_no, 1)
        return token

    def _parse_string_literal(self, token: str, line: Line) -> str:
        """Parse a quoted string literal using JSON-compatible rules.

        v3 extension: literal control characters (tab, etc.) inside quoted
        strings are accepted (they're escaped for JSON parsing).
        """
        try:
            return json.loads(token)
        except json.JSONDecodeError as exc:
            # v3: if the error is about a control character, escape it and retry
            if "control character" in exc.msg or "Invalid control" in exc.msg:
                # Escape literal control characters within the quoted string
                escaped = token[0]  # opening quote
                for ch in token[1:-1]:  # content between quotes
                    if ord(ch) < 0x20:
                        escaped += f"\\u{ord(ch):04x}"
                    else:
                        escaped += ch
                escaped += token[-1]  # closing quote
                try:
                    return json.loads(escaped)
                except json.JSONDecodeError:
                    pass
            raise ToonSyntaxError(f"Invalid string literal: {exc.msg}", line.line_no, exc.colno) from None

    def _consume_multiline_string(self, index: int) -> Tuple[str, int]:
        """Consume a multiline string (triple-quoted) starting at given index."""
        parts: List[str] = []
        while index < len(self.lines):
            line = self.lines[index]
            # Skip blank sentinels inside multiline strings
            if line.content == _BLANK_SENTINEL:
                parts.append("")
                index += 1
                continue
            end = line.content.find('"""')
            if end != -1:
                snippet = line.content[:end]
                if snippet:
                    parts.append(snippet)
                suffix = line.content[end + 3:].strip()
                if suffix:
                    raise ToonSyntaxError("Unexpected content after multiline terminator", line.line_no, end + 3)
                return "\n".join(parts), index + 1
            parts.append(line.content)
            index += 1
        raise ToonSyntaxError("Unterminated multiline string", self.lines[index - 1].line_no, 1)

    @staticmethod
    def _split_key_value(text: str) -> Tuple[str | None, str]:
        """Split a line into key and value parts at the first colon."""
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
                value = text[idx + 1:].strip()
                if key:
                    return key, value
        return None, ""

    @staticmethod
    def _is_array_line(content: str) -> bool:
        """Check if a line represents an array item (starts with "-")."""
        return content == "-" or content.startswith("- ")


def from_toon(
    source: str,
    *,
    strict: bool = True,
    permissive: bool = False,
    indent: int = 2,
    expand_paths: str = "off",
) -> object:
    """Parse a TOON v3 string into a Python object."""
    return ToonParser(
        source, strict=strict, permissive=permissive,
        indent=indent, expand_paths=expand_paths,
    ).parse()
