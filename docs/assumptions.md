# Assumptions & Modes

While TOON SPEC v2.0 defines the wire format precisely, a few behaviors remain implementation-defined. `toonpy` documents its choices here and exposes **strict** and **permissive** parsing modes to accommodate legacy data.

## Key Items

| Area | Strict Behavior | Permissive Behavior | Rationale |
| ---- | ----------------| ------------------- | ----------|
| Identifier keys | Must match `[A-Za-z_][A-Za-z0-9_-]*` or be quoted | Any UTF-8 string accepted | Stops accidental colon usage from silently producing malformed structures |
| Numbers | Must follow JSON number grammar | Fallback to string tokens | Allows legacy hex/leading-zero numbers |
| Table rows | Exact column count required | Extra columns ignored | Simplifies ingestion of hand-authored tables |
| Mixed indentation | Error on tabs or inconsistent dedent | Tabs converted to 4 spaces | Aligns with historical editor behavior |

## Multiline Strings

The upstream spec allows triple-quoted multiline strings. `toonpy` requires the opening line to end with `"""` and the closing sentinel to appear alone (ignoring whitespace). Content is captured verbatim with newline preservation.

## Mode Selection

- `from_toon(..., mode="strict")` (default) enforces all invariants.
- `from_toon(..., mode="permissive")` toggles the relaxed settings above.
- `validate_toon(source, strict=...)` exposes the same behavior for tooling.

If the official specification clarifies any of the above in future revisions, this document should be updated and strict mode tightened accordingly.

