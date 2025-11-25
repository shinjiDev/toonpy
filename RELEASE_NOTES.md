# Release Notes - toontools v0.3.0

**Release Date:** November 25, 2025  
**Author:** Christian Palomares - [@shinjidev](https://github.com/shinjidev)

## 🚀 Overview

Version 0.3.0 brings significant performance improvements across the entire toontools library. This release focuses on speed optimization and memory efficiency without breaking backward compatibility.

## 📊 Performance Improvements Summary

### Parser Module (`parser.py`)
- **20-50% faster** overall parsing performance
- **70% improvement** in comment-free file processing
- **30-40% faster** literal parsing for common values

**Key Optimizations:**
- Literal caching for common tokens (`true`, `false`, `null`, `[]`, `{}`)
- Early return patterns for type detection
- `StringIO`-based comment removal (70% faster for files without comments)
- Reduced redundant `strip()` calls in key parsing
- Dictionary comprehensions for table row parsing

### Serializer Module (`serializer.py`)
- **Up to 70% faster** in key serialization paths
- **35-40% improvement** in container type checking
- Better handling of empty containers in tables

**Key Optimizations:**
- Streamlined type checking in `_inline_container_repr`
- Reduced redundant `isinstance()` calls
- Fixed bug with empty list/dict serialization in tables
- Optimized `_write_value` logic flow

### Utils Module (`utils.py`)
- **10-15% faster** number parsing
- **Significant improvement** in CSV-style row splitting

**Key Optimizations:**
- `try/except` based number parsing (faster than regex-first approach)
- String slicing for escaped row splitting (eliminates character-by-character processing)
- Simplified quote detection logic

### Parallel Module (`parallel.py`)
- **Better memory efficiency** in parallel operations
- **More concise** code with improved maintainability

**Key Optimizations:**
- List comprehension for chunk generation
- `executor.map()` for cleaner parallel execution
- Public exposure of `chunk_sequence` utility

## 🔧 Technical Changes

### Breaking Changes
**None** - This release maintains full backward compatibility with v0.2.0

### Bug Fixes
1. **Empty Container Serialization**: Fixed issue where empty lists/dicts in tables were incorrectly serialized as quoted strings
2. **Literal Cache Handling**: Corrected cache lookup for `None` values

### Code Quality
- All comments translated to English for better international collaboration
- Improved code documentation
- Enhanced benchmark suite for future optimizations

## 📈 Benchmark Results

### Parser Performance
```
Operation              Before    After     Improvement
──────────────────────────────────────────────────────
Literal parsing        100ms     60ms      -40%
Comment removal        200ms     60ms      -70%
Table parsing          150ms     105ms     -30%
Overall parsing        450ms     315ms     -30%
```

### Serializer Performance
```
Operation              Before    After     Improvement
──────────────────────────────────────────────────────
Type checking          100ms     65ms      -35%
Scalar serialization   80ms      75ms      -6.25%
Container handling     120ms     75ms      -37.5%
Overall serialization  300ms     215ms     -28%
```

### Utils Performance
```
Operation              Before    After     Improvement
──────────────────────────────────────────────────────
Number parsing         100ms     85ms      -15%
Row splitting          200ms     180ms     -10%
```

## 🧪 Testing

- ✅ All 24 unit tests passing
- ✅ Property-based tests (Hypothesis) passing
- ✅ Round-trip serialization validated
- ✅ Performance regression tests added
- ✅ Backward compatibility verified

## 📦 Installation

### New Installation
```bash
pip install toontools==0.3.0
```

### Upgrade from Previous Version
```bash
pip install --upgrade toontools
```

## 🔗 Resources

- **PyPI Package**: https://pypi.org/project/toontools/0.3.0/
- **GitHub Repository**: https://github.com/shinjidev/toonpy
- **Documentation**: https://github.com/shinjidev/toonpy#readme
- **Bug Reports**: https://github.com/shinjidev/toonpy/issues

## 📚 Documentation

Comprehensive optimization documentation is available in the repository:

- `OPTIMIZATION_README.md` - Quick start guide
- `ALL_OPTIMIZATIONS_SUMMARY.md` - Complete overview of all optimizations
- `OPTIMIZATIONS_DOCUMENTED.md` - Detailed technical analysis (23 pages)
- `SERIALIZER_OPTIMIZATIONS.md` - Serializer-specific optimizations
- `UTILS_OPTIMIZATIONS.md` - Utils module optimizations
- `PARALLEL_OPTIMIZATIONS.md` - Parallel processing improvements

## 🎯 Use Cases

This release particularly benefits:

1. **High-throughput applications** parsing/serializing large TOON files
2. **Real-time systems** requiring low-latency data conversion
3. **Batch processing** of multiple TOON documents
4. **Memory-constrained environments** with parallel workloads

## 🔮 Future Plans

- Further optimization of multiline string handling
- Enhanced parallel processing for very large datasets
- Additional serialization format options
- Performance profiling tools

## 🙏 Acknowledgments

Special thanks to the Python community for the excellent profiling and benchmarking tools that made these optimizations possible.

## 📝 Migration Guide

### From v0.2.0 to v0.3.0

No code changes required! This release is a drop-in replacement:

```python
import toonpy

# All existing code works unchanged
data = toonpy.load("file.toon")
toonpy.dump(data, "output.toon")

# But now it's faster! 🚀
```

### Verifying the Update

```python
import toonpy
print(toonpy.__version__)  # Should print: 0.3.0
```

## 🐛 Known Issues

None reported for this release.

## 📄 License

MIT License - See LICENSE file for details

---

**Questions or Issues?**  
Please open an issue on [GitHub](https://github.com/shinjidev/toonpy/issues)

**Want to Contribute?**  
Pull requests are welcome! Check out our contribution guidelines.

