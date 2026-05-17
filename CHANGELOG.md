# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-05-17

### Added
- **TOON spec v3.0 full support** — v3 is now the default parser
- Multiple delimiters: tab (`\t`) and pipe (`|`) in addition to comma, configurable via `from_toon(delimiter=...)` / `to_toon(delimiter=...)`
- Primitive inline arrays: `key[N]: v1,v2,v3` format
- Root form disambiguation: root arrays (`[N]:`), root objects, and root primitives all correctly parsed
- Blank-line sentinels in strict mode
- Key folding in serializer: `to_toon(key_folding="safe", flatten_depth=N)` collapses single-key chains into dotted paths
- Path expansion in parser: `from_toon(expand_paths="safe"|"lax")` expands dotted keys into nested objects
- `spec="v2"` backward-compat option in `from_toon()` and `to_toon()` to opt in to v2 parsing
- Official spec fixture test suite: all fixtures from `toon-format/spec` pass (358/358)

### Changed
- `@table` format removed from v3 parser (use `key[N]{fields}:` instead)
- `guess_number` now handles exponent notation (`1e6`), `-0` normalization, and leading-zero → string coercion
- `format_key` now follows v3 key rules (no hyphens in unquoted keys)
- `tabular_schema` detection uses key-set comparison (order-independent)
- Parser performance improved +117% on simple objects, +123% on tabular arrays vs v2 baseline

### Fixed
- Strings containing `:`, `\t`, or `\r` are now correctly quoted in serializer output
- Hyphenated keys (`my-key`) now always quoted in serializer output
- Delimiter characters and spaces properly escaped in cell and value contexts

## [0.3.0] - 2025-11-25

### Added
- Literal caching system for common tokens in parser
- Early return patterns for faster type detection
- `chunk_sequence` now publicly accessible in parallel module
- Comprehensive benchmark suite for performance regression testing
- Detailed optimization documentation (multiple markdown files)

### Changed
- **Parser**: Refactored `_remove_block_comments` to use `StringIO` (70% faster for comment-free files)
- **Parser**: Optimized `_parse_token` with literal cache (30-40% improvement)
- **Parser**: Moved regex patterns to module level for one-time compilation
- **Parser**: Dictionary comprehension for table row parsing
- **Serializer**: Streamlined type checking in `_inline_container_repr` (35-40% faster)
- **Serializer**: Reduced redundant `isinstance()` calls in `_write_value`
- **Utils**: Number parsing now uses `try/except` with regex fallback (10-15% faster)
- **Utils**: String slicing for `split_escaped_row` instead of character-by-character building
- **Parallel**: Replaced `submit()`/`result()` pattern with `executor.map()` for better memory efficiency
- **Parallel**: List comprehension for chunk generation
- All code comments translated to English

### Fixed
- Empty lists and dicts in tables now serialize correctly as `[]` and `{}` instead of quoted strings
- Literal cache now properly handles `None` values for "null" tokens
- Removed redundant `.strip()` calls in `_parse_key`

### Performance
- **Overall parser**: 20-50% faster across different workloads
- **Overall serializer**: Up to 70% faster in key paths
- **Comment removal**: 70% improvement for files without block comments
- **Number parsing**: 10-15% faster
- **Type checking**: 35-40% reduction in overhead
- **Memory usage**: Improved efficiency in parallel operations

### Documentation
- Added `RELEASE_NOTES.md` with comprehensive v0.3.0 overview
- Added `OPTIMIZATION_README.md` as entry point to optimization docs
- Added `ALL_OPTIMIZATIONS_SUMMARY.md` for complete optimization overview
- Added `OPTIMIZATIONS_DOCUMENTED.md` with 23-page technical analysis
- Added `SERIALIZER_OPTIMIZATIONS.md` for serializer-specific changes
- Added `UTILS_OPTIMIZATIONS.md` for utils module changes
- Added `PARALLEL_OPTIMIZATIONS.md` for parallel processing improvements
- Added `PROJECT_STATUS_REVIEW.md` documenting compatibility review
- Updated author attribution to Christian Palomares in all docs

## [0.2.0] - 2025-11-XX

### Added
- Parallel serialization support via `parallel.py` module
- ThreadPoolExecutor and ProcessPoolExecutor support
- Enhanced API for streaming large datasets
- Table suggestion utilities

### Changed
- Improved error messages with better line number reporting
- Enhanced CLI with formatting options
- Better validation for TOON syntax

### Fixed
- Various edge cases in parser
- Multiline string handling improvements

## [0.1.0] - 2025-XX-XX

### Added
- Initial release
- TOON parser implementation
- TOON serializer implementation
- CLI tool (`toonpy`)
- Basic API functions (`load`, `dump`, `loads`, `dumps`)
- Support for objects, arrays, tables, and multiline strings
- Comprehensive test suite
- Property-based testing with Hypothesis

---

## Version Comparison

### Performance Evolution

| Metric                  | v0.1.0 | v0.2.0 | v0.3.0 | Total Improvement |
|-------------------------|--------|--------|--------|-------------------|
| Parser Speed            | 100%   | 105%   | 140%   | +40%              |
| Serializer Speed        | 100%   | 110%   | 155%   | +55%              |
| Memory Efficiency       | 100%   | 105%   | 120%   | +20%              |
| Comment Processing      | 100%   | 100%   | 233%   | +133%             |

### Feature Evolution

| Feature                 | v0.1.0 | v0.2.0 | v0.3.0 |
|-------------------------|--------|--------|--------|
| Basic Parsing           | ✅     | ✅     | ✅     |
| Serialization           | ✅     | ✅     | ✅     |
| Tables                  | ✅     | ✅     | ✅     |
| Multiline Strings       | ✅     | ✅     | ✅     |
| Parallel Processing     | ❌     | ✅     | ✅     |
| Streaming API           | ❌     | ✅     | ✅     |
| Performance Optimized   | ❌     | ❌     | ✅     |
| Comprehensive Docs      | ❌     | ❌     | ✅     |

---

## Upgrade Guide

### From 0.2.0 to 0.3.0
- **Breaking Changes**: None
- **Action Required**: None
- **Recommendation**: Simply upgrade with `pip install --upgrade toontools`
- All existing code will work unchanged and run faster

### From 0.1.0 to 0.3.0
- **Breaking Changes**: None (except if using internal/private APIs)
- **Action Required**: Review parallel processing API if using custom executors
- **Recommendation**: Upgrade directly to 0.3.0 for best performance

---

## Links

- **PyPI**: https://pypi.org/project/toontools/
- **Repository**: https://github.com/shinjidev/toonpy
- **Issues**: https://github.com/shinjidev/toonpy/issues
- **Changelog**: https://github.com/shinjidev/toonpy/blob/main/CHANGELOG.md

