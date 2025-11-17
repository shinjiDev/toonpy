# Examples

This directory contains various examples demonstrating JSON ↔ TOON conversion.

## Example Files

- **example1** – Basic tabular array with nested objects
- **example2** – Nested objects with arrays (non-tabular)
- **example3** – Mixed arrays: tabular objects and simple list
- **example4** – Multiline strings with triple quotes
- **example5** – Empty containers and scalar values
- **example6** – Large tabular array with multiple fields
- **example7** – Complex nested structures with mixed types
- **example8** – Deep nesting with tabular reviews

## Usage

Convert JSON to TOON:

```bash
toonpy to --in examples/example1.json --out examples/example1.generated.toon --mode readable
```

Convert TOON to JSON:

```bash
toonpy from --in examples/example1.toon --out examples/example1.generated.json
```

Format a TOON file:

```bash
toonpy fmt --in examples/example1.toon --out examples/example1.formatted.toon --mode readable
```

## Round-trip Testing

All examples should round-trip correctly:

```bash
# Convert JSON → TOON → JSON
toonpy to --in examples/example1.json --out /tmp/test.toon
toonpy from --in /tmp/test.toon --out /tmp/test.json

# Compare (should be identical, modulo formatting)
diff examples/example1.json /tmp/test.json
```

## Example Descriptions

### example1
Basic example with tabular array syntax (`crew[2]{id,name,role}:`) and nested objects.

### example2
Shows nested objects with non-tabular arrays (glyphs array uses standard list format).

### example3
Demonstrates mixed array types: tabular objects (`items[2]{name,power}:`) and simple string list.

### example4
Illustrates multiline strings using triple-quoted syntax (`"""..."""`).

### example5
Shows empty containers (`[]` and `{}`) and various scalar types (boolean, float, integer).

### example6
Large tabular array with 4 fields per row, demonstrating efficiency of tabular format.

### example7
Complex nested structures with arrays of different types and deep nesting.

### example8
Product catalog example with deeply nested objects and tabular reviews array.

