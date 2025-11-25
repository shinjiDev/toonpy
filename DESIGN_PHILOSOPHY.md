# Design Philosophy & Architecture Decisions

**Project:** toontools  
**Author:** Christian Palomares - [@shinjidev](https://github.com/shinjidev)  
**Version:** 0.3.0+

---

## 🎯 Core Design Principles

### 1. **Zero-Dependency Core**

**Decision:** The base toontools package has ZERO external dependencies.

```toml
[project]
dependencies = []  # No required dependencies
```

**Rationale:**
- **Fast installs** - No need to download/compile external packages
- **Minimal footprint** - Perfect for Docker, Lambda, edge computing
- **Reliability** - No risk of dependency conflicts or breaking changes
- **Pure Python** - Works everywhere Python works

**Impact:**
- Base installation: ~60 KB
- Install time: < 1 second
- Compatible with restricted environments

---

### 2. **Optional Features Pattern**

**Decision:** Additional format support is provided via optional dependencies.

```toml
[project.optional-dependencies]
yaml = ["PyYAML>=6.0"]
tests = ["pytest>=7", "hypothesis>=6"]
examples = ["tiktoken>=0.5.2"]
```

**Rationale:**
- **User choice** - Install only what you need
- **Graceful degradation** - Core works without extras
- **Clear errors** - Helpful messages when optional feature is missing
- **Common pattern** - Used by FastAPI, Pydantic, Pandas, Requests

**Implementation:**
```python
# Optional feature detection
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Conditional exports
if HAS_YAML:
    __all__.extend(["to_yaml_from_toon", "to_toon_from_yaml"])
```

---

### 3. **Performance First**

**Decision:** Optimize for speed and memory efficiency.

**Key Optimizations:**
- Literal caching for common tokens
- StringIO for efficient string building
- Early returns to avoid unnecessary processing
- try/except for fast-path number parsing
- List comprehensions over explicit loops

**Results:**
- v0.3.0: 20-70% faster than v0.2.0
- TOON serialization: 3-5x slower than JSON (competitive)
- YAML conversion: 10-30x faster than pure YAML
- Memory efficient streaming for large files

**See:** `OPTIMIZATION_PROJECT_SUMMARY.md` for detailed analysis

---

### 4. **Reuse Over Reinvention**

**Decision:** Leverage existing, optimized components when adding features.

**Example - YAML Support:**
```python
def to_toon_from_yaml(yaml_str):
    data = yaml.safe_load(yaml_str)      # PyYAML handles YAML
    return to_toon(data)                  # Reuse existing TOON serializer

def to_yaml_from_toon(toon_str):
    data = from_toon(toon_str)            # Reuse existing TOON parser
    return yaml.dump(data)                # PyYAML handles YAML
```

**Benefits:**
- Minimal code duplication
- Consistent behavior across formats
- Leverages battle-tested libraries
- Easy to maintain and extend

---

## 🏗️ Architecture Patterns

### Core Components

```
toontools/
├── toonpy/
│   ├── parser.py       # TOON → Python (core, no deps)
│   ├── serializer.py   # Python → TOON (core, no deps)
│   ├── api.py          # Public API + format adapters
│   ├── cli.py          # Command-line interface
│   ├── utils.py        # Shared utilities (core, no deps)
│   └── parallel.py     # Optional parallelization
```

### Dependency Graph

```
Core (0 deps)
├── parser.py
├── serializer.py
└── utils.py
    ↓
API Layer
└── api.py (adapters for formats)
    ↓
Optional Features
├── YAML (requires PyYAML)
├── Token counting (requires tiktoken)
└── Tests (requires pytest, hypothesis)
```

---

## 📊 Design Decisions - Format Support

### Why Optional Dependencies for Formats?

| Decision | Reason | Benefit |
|----------|--------|---------|
| **JSON: Built-in** | stdlib `json` module | No dependency needed |
| **YAML: Optional** | PyYAML not in stdlib | Keep core lightweight |
| **TOML: Future optional** | tomllib in 3.11+ only | Backward compat for 3.9-3.10 |
| **CSV: Future built-in** | stdlib `csv` module | Can be core feature |

---

## 🎓 Lessons from Other Projects

### Successful Patterns We Follow

#### FastAPI - Optional Dependencies
```toml
[project.optional-dependencies]
all = ["uvicorn[standard]", "jinja2", ...]
```
- Core is minimal
- Full features opt-in
- Clear dependency groups

#### Requests - Security Extras
```toml
[project.optional-dependencies]
security = ["cryptography", "pyOpenSSL"]
```
- HTTPS works without extras
- Advanced security opt-in
- Graceful degradation

#### Pandas - Optional Engines
```toml
[project.optional-dependencies]
all = ["numpy", "pytz", ...]
```
- Core DataFrame operations
- I/O engines optional
- Performance extras available

---

## 🔮 Future Format Support Strategy

### Decision Matrix for New Formats

| Format | Include in Core? | Rationale |
|--------|------------------|-----------|
| **CSV** | Yes (future) | stdlib `csv`, natural fit for tabular |
| **TOML** | Optional | tomllib only in 3.11+, need tomli for 3.9-3.10 |
| **XML** | Optional | Large dependency, specific use case |
| **MessagePack** | Optional | Binary format, niche use case |
| **Protobuf** | Optional | Complex, schema-based, specific use case |

### Criteria for Optional vs Core

**Include in Core if:**
- ✅ No external dependencies needed
- ✅ Used by >50% of users
- ✅ Small code footprint
- ✅ Aligns with TOON philosophy

**Make Optional if:**
- ⚠️ Requires external dependency
- ⚠️ Used by <20% of users
- ⚠️ Large dependency size
- ⚠️ Specific use case only

---

## 🛠️ Implementation Guidelines

### Adding New Format Support

**Template for Optional Format:**

```python
# 1. Check availability
try:
    import format_lib
    HAS_FORMAT = True
except ImportError:
    HAS_FORMAT = False

# 2. Implement adapters
if HAS_FORMAT:
    def to_toon_from_format(format_str):
        data = format_lib.loads(format_str)
        return to_toon(data)
    
    def to_format_from_toon(toon_str):
        data = from_toon(toon_str)
        return format_lib.dumps(data)

# 3. Add to pyproject.toml
[project.optional-dependencies]
format = ["format-lib>=1.0"]

# 4. Update __all__ conditionally
if HAS_FORMAT:
    __all__.extend(["to_toon_from_format", "to_format_from_toon"])
```

**Required Documentation:**
- README: Brief mention + install command
- Docstrings: Clear ImportError messages
- Tests: Skip if dependency not available
- Benchmarks: Optional performance tests

---

## 📝 Code Quality Standards

### 1. **Pure Python Core**
- No C extensions in core
- Portable across platforms
- Easy to debug and maintain

### 2. **Type Hints**
- Full type annotations (Python 3.9+ syntax)
- Helps IDEs and linters
- Self-documenting code

### 3. **Comprehensive Testing**
- 100% core functionality tested
- Property-based testing (Hypothesis)
- Performance regression tests
- Optional features tested when available

### 4. **Performance Benchmarks**
- All optimizations benchmarked
- Before/after comparisons
- Real-world usage scenarios
- Documented in markdown

### 5. **Clear Documentation**
- Inline comments in English
- Comprehensive docstrings
- README examples
- Optimization documentation

---

## 🎯 Design Trade-offs

### Accepted Trade-offs

| Trade-off | Decision | Rationale |
|-----------|----------|-----------|
| **Speed vs Size** | Optimize for speed | Users value performance |
| **Features vs Simplicity** | Minimal core + optional | Serve both simple and advanced use cases |
| **Compatibility vs Modern** | Support 3.9+ | Balance adoption and modern features |
| **One Format vs Many** | Core + optional formats | Don't force unused features |

### Rejected Alternatives

**❌ Include all formats by default**
- Would add 5+ dependencies
- Slower installs
- Larger Docker images
- Most users don't need all formats

**❌ Separate packages for each format**
- Too fragmented
- Complex installation
- Harder to maintain
- Poor user experience

**❌ Plugin system**
- Over-engineered for this use case
- Added complexity
- Discovery problems
- Not needed yet

---

## 📈 Success Metrics

### Design Goals Met

- ✅ **Zero dependencies** - Core has 0 deps
- ✅ **Fast installs** - <1 second for core
- ✅ **High performance** - 20-70% improvements in v0.3.0
- ✅ **Optional features** - YAML working perfectly
- ✅ **Clear documentation** - Multiple detailed docs
- ✅ **100% test coverage** - All tests passing

### User Benefits

- ✅ **Fast adoption** - Quick to install and try
- ✅ **Flexible** - Install only what you need
- ✅ **Production-ready** - Optimized and tested
- ✅ **Well-documented** - Easy to understand
- ✅ **Extensible** - Easy to add more formats

---

## 🔄 Evolution Strategy

### Version Philosophy

**Semantic Versioning:**
- **Major (X.0.0)** - Breaking API changes
- **Minor (0.X.0)** - New features, backward compatible
- **Patch (0.0.X)** - Bug fixes, optimizations

**Current Path:**
- v0.1.0 - Initial release
- v0.2.0 - Parallel support
- v0.3.0 - Performance + YAML support
- v0.4.0 - TOML support (future)
- v0.5.0 - CSV support (future)
- v1.0.0 - Stable API, production grade

---

## 🤝 Contributing Guidelines

### Design Principles for Contributors

1. **Keep core dependency-free**
   - If it needs a dependency, make it optional

2. **Optimize for common case**
   - 80% of users should get 100% of performance

3. **Test everything**
   - Core: 100% coverage required
   - Optional: Test when dependency available

4. **Document decisions**
   - Why, not just what
   - Trade-offs considered
   - Benchmarks provided

5. **Follow existing patterns**
   - Look at YAML support as template
   - Reuse utilities
   - Consistent naming

---

## 📚 References

### Inspiration

- **FastAPI** - Optional dependencies pattern
- **Requests** - Simple API, optional extras
- **Pandas** - Performance focus, optional engines
- **Click** - Zero-dependency CLI
- **Rich** - Pure Python, optional extras

### Related Documents

- `OPTIMIZATION_PROJECT_SUMMARY.md` - Performance details
- `YAML_SUPPORT_SUMMARY.md` - YAML implementation
- `README.md` - User documentation
- `CHANGELOG.md` - Version history

---

## ✅ Summary

**toontools follows these core principles:**

1. **Zero-dependency core** - Fast, lightweight, reliable
2. **Optional features** - Install what you need
3. **Performance first** - Optimized and benchmarked
4. **Reuse over reinvent** - Leverage existing tools
5. **Clear documentation** - Explain decisions and trade-offs

This philosophy ensures toontools remains:
- ⚡ Fast to install
- 🪶 Lightweight
- 🚀 High performance  
- 🔧 Flexible
- 📚 Well-documented
- 🤝 Easy to contribute to

---

*This document explains the "why" behind design decisions. For implementation details, see the source code and other documentation files.*

