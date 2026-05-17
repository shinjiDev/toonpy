# TOON SPEC v3.0 Summary

This document condenses the public rules from **TOON SPEC v3.0** so contributors can quickly cross-reference the grammar implemented in `toonpy`. The full specification is at https://github.com/toon-format/spec/blob/main/SPEC.md.

## Core Concepts

- **Indentation-based hierarchy** – indentation (spaces only) expresses structural nesting. Equal indentation denotes sibling entries. Tabs are forbidden for indentation.
- **Key-value objects** – objects are encoded as `key: value`. Unquoted keys are plain identifiers (`[A-Za-z_][A-Za-z0-9_]*`, no hyphens). Dotted paths (`a.b.c`) allowed unquoted. Quoted keys support any characters.
- **Arrays (list format)** – introduced by a header `key[N]:` followed by `- item` lines at the next indent level.
- **Primitive inline arrays** – `key[N]: v1,v2,v3` — compact single-line form for scalar-only arrays.
- **Tabular arrays** – `key[N]{field1,field2}:` with comma-separated rows. Delimiter in brackets selects row separator: `[N\t]{f1\tf2}:` for tab, `[N|]{f1|f2}:` for pipe.
- **Root forms** – a document may be: an object (key: value entries), an array (`[N]:` header), or a single primitive.
- **Scalars** – strings use JSON-compatible escapes; unquoted tokens are valid raw strings when they contain no unsafe characters. Numbers follow JSON grammar. `true`, `false`, `null` map to native booleans/None.
- **Comments** – line comments start with `#` or `//`. Block comments use `/* ... */` and may nest.
- **Blank lines** – skipped in non-strict mode; in strict mode, blank lines inside a structure raise an error.
- **Path expansion** – dotted keys (`a.b: v`) can be expanded to nested objects via `from_toon(expand_paths="safe"|"lax")`.

## Delimiters

v3 supports three delimiters for tabular and inline arrays:

| Name   | Character | Bracket form | Header example               |
|--------|-----------|--------------|------------------------------|
| comma  | `,`       | (none)       | `users[3]{id,name}:`         |
| tab    | `\t`      | `\t`         | `users[3\t]{id\tname}:`      |
| pipe   | `\|`      | `\|`         | `users[3\|]{id\|name}:`      |

## Simplified Grammar

```
document      = object / root-array / primitive
object        = (kv-entry / array-header / blank)*
kv-entry      = key ":" SP? (scalar / block)
array-header  = key? "[" N delim? "]" ("{" fields "}")? ":" inline?
key           = identifier / dotted-path / quoted-string
identifier    = ALPHA *(ALPHA / DIGIT / "_")
dotted-path   = identifier ("." identifier)+
scalar        = string / number / "true" / "false" / "null" / raw-token
```

## Error Handling

- Syntax violations carry line/column information.
- Unterminated strings/comments are fatal errors.
- Mixed indentation (tabs/spaces or inconsistent widths) is rejected in strict mode.
- In strict mode: blank lines inside structures, row count mismatches, and delimiter mismatches are errors.
- Permissive mode (`permissive=True`) relaxes unquoted-string-with-spaces checks.

## Backward Compatibility

Pass `spec="v2"` to `from_toon()` / `to_toon()` to use the v2 parser/serializer. This routes to `toonpy._parser_v2` which is a verbatim copy of the pre-v3 parser.

Refer to `docs/assumptions.md` for any clarifications or local decisions recorded by the toonpy maintainers.
