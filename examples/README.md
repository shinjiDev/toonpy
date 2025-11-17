# Examples

- `example1.json` – canonical JSON input
- `example1.toon` – serialized output using `toonpy`

Try the CLI:

```
toonpy to --in examples/example1.json --out examples/example1.generated.toon --mode readable
toonpy from --in examples/example1.toon --out examples/example1.generated.json
```

Both commands should produce files identical to the originals (modulo whitespace).

