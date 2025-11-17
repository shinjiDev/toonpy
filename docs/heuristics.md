# Tabular Heuristics

`toonpy` attempts to emit tabular arrays whenever doing so saves tokens without harming readability. The heuristics are deterministic and purely structural so that round-trips stay stable.

1. **Uniform schema** – every element must be a mapping with the exact same ordered key set.
2. **Key count** – tables are most effective for ≥2 keys. Single-key arrays remain as lists unless `mode="compact"`.
3. **Savings estimate** – we approximate the serialized cost of both representations:
   - JSON baseline: `json.dumps(seq, separators=(",", ":"))`
   - Tabular estimate: sum of header width and per-row cell widths (quoted when needed)
4. **Mode sensitivity**
   - `mode="compact"` always emits tables for uniform schemas.
   - `mode="readable"` requires the estimated savings to exceed 10 tokens.
   - `mode="auto"` compares the estimates and chooses the cheaper option.

At runtime `suggest_tabular` can optionally use `tiktoken` (when installed) to produce a more realistic token count for models compatible with the `cl100k_base` vocabulary. Otherwise character counts are used as a proxy.

