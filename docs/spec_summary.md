# TOON SPEC v2.0 Summary

This document condenses the public rules from **TOON SPEC v2.0** so contributors can quickly cross-reference the grammar implemented in `toonpy`. The full specification is ABNF-based; we mirror the essential productions and call out deviations where the upstream document defers to implementation detail.

## Core Concepts

- **Indentation-based hierarchy** – indentation (spaces only) expresses structural nesting. Equal indentation denotes sibling entries. Tabs are forbidden.
- **Key-value objects** – objects are encoded as `key: value`. Keys accept either safe identifiers (`[A-Za-z_][A-Za-z0-9_-]*`) or quoted strings. Values may be inline scalars or nested blocks.
- **Arrays** – list items begin with `-`. Inline scalars (e.g. `- 42`) are supported; otherwise, a nested block follows on the next indented line.
- **Tabular mode** – uniform arrays of objects (same key set, stable order) can be emitted as tables via `@table key1, key2`. Each row is pipe or comma separated.
- **Scalars** – strings use JSON-compatible escapes; unquoted identifiers are allowed when safe. Numbers follow the JSON grammar. `true`, `false`, `null` map to native booleans/None.
- **Comments** – line comments start with `#` or `//`. Block comments use `/* ... */` and may nest.
- **Whitespace** – trailing whitespace is ignored. Blank lines are skipped. Newlines separate logical statements.

## Simplified ABNF

```
toon-document = wsp* value (newline value)* wsp*
value         = scalar / object / array / table
object        = (object-entry newline)* object-entry
object-entry  = key ":" wsp* (scalar / newline indent value)
key           = identifier / string
array         = (array-entry newline)* array-entry
array-entry   = "-" wsp* (scalar / newline indent value)
table         = "@table" wsp+ key-list newline table-row+
key-list      = key *(list-sep key)
table-row     = indent (row-cell list-sep)+ row-cell
list-sep      = wsp* ("," / "|") wsp*
scalar        = string / number / boolean / null / identifier
identifier    = ALPHA *(ALPHA / DIGIT / "_" / "-")
```

### Notes

- Multiline strings use triple quotes: a line that ends with `"""` opens the literal; the first subsequent line with `"""` closes it.
- Table rows may use either commas or pipes; pipes are preferred for readability. Cells are parsed with JSON string semantics when quoted, otherwise as bare scalars.
- Comments can appear anywhere whitespace is permitted.
- The canonical serializer keeps dictionary insertion order (Python ≥3.7 guarantees this).

## Error Handling

- Syntax violations carry line/column information.
- Unterminated strings/comments are treated as fatal errors.
- Mixed indentation (tabs/spaces or inconsistent widths) is rejected in strict mode.
- Permissive mode relaxes certain checks (identifier safety, numeric precision) to ease migration.

Refer to `docs/assumptions.md` for any clarifications or local decisions recorded by the toonpy maintainers.

