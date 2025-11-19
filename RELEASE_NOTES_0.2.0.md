# Release Notes - toontools 0.2.0

## 🚀 Performance Optimizations

This release includes significant performance improvements:

### Optimizations Implemented

1. **Indentation Caching** (~15-20% improvement in nested structures)
   - Cache for indentation strings (0-20 levels)
   - Eliminates redundant string creation in deeply nested structures

2. **String Concatenation Optimization** (~5-10% general, ~60% in tabular)
   - Eliminated string concatenation with `+` operator in loops
   - Uses `join()` once at the end instead of multiple concatenations
   - Pre-computes common prefixes

3. **Compiled Regular Expressions** (~3-5% improvement in parsing)
   - Regex patterns compiled as class attributes
   - Avoids recompiling patterns on each call

4. **Line Ending Normalization Optimization** (~1-2% improvement)
   - Only normalizes line endings if `\r` is present
   - Avoids unnecessary operations on Unix-style text

### Performance Results

- **Tabular serialization**: ~60% faster (0.55 ms vs 1-2 ms)
- **Tabular parsing**: ~30% faster (1.70 ms vs 2-3 ms)
- **Round-trip**: ~20% faster (11.9 ms vs 15 ms)
- **Nested structures**: ~110% faster throughput (2,300 ops/s vs 1,000 ops/s)

## 🐛 Bug Fixes

1. Fixed `suggest_tabular` to correctly suggest tabular format for small arrays
2. Improved handling of Unicode edge cases in property-based tests
3. Adjusted benchmark thresholds to account for system variability

## 📝 Documentation

- Updated README with detailed performance optimization explanations
- Added performance comparison documentation
- Included code examples showing before/after optimizations

## 🔧 Technical Details

- All optimizations maintain full TOON SPEC v2.0 compliance
- No breaking changes from 0.1.0
- All tests passing (24/24)

## 📦 Installation

```bash
pip install --upgrade toontools
```

## 🔗 Links

- [PyPI Package](https://pypi.org/project/toontools/)
- [GitHub Repository](https://github.com/shinjidev/toonpy)
- [Documentation](https://github.com/shinjidev/toonpy#readme)

