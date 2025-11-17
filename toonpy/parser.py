"""
Lexer and parser for TOON (Token-Oriented Object Notation).
"""

from __future__ import annotations

from dataclasses import dataclass
import json
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


@dataclass(slots=True)
class Line:
    indent: int
    content: str
    line_no: int


class ToonLexer:
    def __init__(self, source: str) -> None:
        self.source = source.replace("\r\n", "\n").replace("\r", "\n")

    def iter_lines(self) -> List[Line]:
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
        result: List[str] = []
        i = 0
        depth = 0
        while i < len(text):
            if text.startswith("/*", i):
                depth += 1
                i += 2
                continue
            if depth > 0:
                if text.startswith("*/", i):
                    depth -= 1
                    i += 2
                    continue
                result.append("\n" if text[i] == "\n" else " ")
                i += 1
                continue
            result.append(text[i])
            i += 1
        if depth != 0:
            raise ToonSyntaxError("Unterminated block comment")
        return "".join(result)

    @staticmethod
    def _strip_inline_comment(line: str) -> str:
        buf: List[str] = []
        in_string = False
        escape = False
        i = 0
        while i < len(line):
            ch = line[i]
            if escape:
                buf.append(ch)
                escape = False
                i += 1
                continue
            if ch == "\\":
                buf.append(ch)
                escape = True
                i += 1
                continue
            if ch == "\"":
                buf.append(ch)
                in_string = not in_string
                i += 1
                continue
            if not in_string:
                if ch == "#" and not in_string:
                    break
                if ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                    break
            buf.append(ch)
            i += 1
        return "".join(buf).rstrip()


class ToonParser:
    def __init__(self, source: str, *, permissive: bool = False) -> None:
        self.lines = ToonLexer(source).iter_lines()
        self.permissive = permissive

    def parse(self) -> object:
        if not self.lines:
            raise ToonSyntaxError("Empty TOON document")
        value, next_index = self._parse_value(0)
        if next_index != len(self.lines):
            extra = self.lines[next_index]
            raise ToonSyntaxError("Unexpected content after end of document", extra.line_no, 1)
        return value

    def _parse_value(self, index: int) -> Tuple[object, int]:
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
        result: dict[str, object] = {}
        index = start
        while index < len(self.lines):
            line = self.lines[index]
            if line.indent != indent:
                break
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
        line = self.lines[index]
        if token == '"""':
            text, next_index = self._consume_multiline_string(index + 1)
            return text, next_index
        return self._parse_token(token, line), index + 1

    def _parse_array(self, start: int, indent: int) -> Tuple[object, int]:
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

    def _parse_table(self, start: int, indent: int) -> Tuple[List[dict[str, object]], int]:
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
            row: dict[str, object] = {}
            for key, token in zip(header, values):
                row[key] = self._parse_token(token, line)
            rows.append(row)
            index += 1
        return rows, index

    def _parse_scalar_line(self, index: int) -> Tuple[object, int]:
        line = self.lines[index]
        return self._parse_token(line.content, line), index + 1

    def _parse_token(self, token: str, line: Line) -> object:
        token = token.strip()
        if token == "":
            raise ToonSyntaxError("Empty value", line.line_no, 1)
        if token == "[]":
            return []
        if token == "{}":
            return {}
        if token.startswith('"""'):
            if token.endswith('"""') and len(token) >= 6:
                return token[3:-3]
            raise ToonSyntaxError("Unterminated multiline string", line.line_no, 1)
        if token.startswith("\""):
            return self._parse_string_literal(token, line)
        lowered = token.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered == "null":
            return None
        number = guess_number(token)
        if number is not None:
            return number
        if is_safe_identifier(token):
            return token
        if self.permissive:
            return token
        raise ToonSyntaxError("Invalid unquoted string literal", line.line_no, 1)

    def _parse_key(self, token: str, line: Line) -> str:
        token = token.strip()
        if token.startswith("\""):
            return self._parse_string_literal(token, line)
        if not is_safe_identifier(token):
            if self.permissive:
                return token
            raise ToonSyntaxError("Keys must be safe identifiers or quoted strings", line.line_no, 1)
        return token

    def _parse_string_literal(self, token: str, line: Line) -> str:
        try:
            return json.loads(token)
        except json.JSONDecodeError as exc:
            raise ToonSyntaxError(f"Invalid string literal: {exc.msg}", line.line_no, exc.colno) from None

    def _consume_multiline_string(self, index: int) -> Tuple[str, int]:
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
        if "," in text:
            parts = [part.strip() for part in text.split(",") if part.strip()]
        else:
            parts = [part for part in text.split() if part]
        if not parts:
            raise ToonSyntaxError("Empty table header")
        return parts

    @staticmethod
    def _is_array_line(content: str) -> bool:
        return content == "-" or content.startswith("- ")


def from_toon(source: str, *, permissive: bool = False) -> object:
    return ToonParser(source, permissive=permissive).parse()

