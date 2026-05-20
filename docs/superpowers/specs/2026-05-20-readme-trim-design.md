# README Trim & Clarity Fix — Design Spec

**Date:** 2026-05-20  
**Status:** Approved  
**Target:** `README.md` (617 lines → ~340 lines)

---

## Problem

The README has two distinct issues:

1. **Version naming ambiguity** — "v2 Baseline" in performance tables is ambiguous: "v2" elsewhere in the doc refers to TOON spec v2, but in the performance context it means the library at the v0.5.x era (before TOON spec v3). The performance table also appears twice identically.

2. **Aesthetic length** — At 617 lines, the README feels long relative to the library's surface area. Several sections duplicate content already present elsewhere.

---

## Audience

Mixed: new developers evaluating the library + existing users looking up API details. The README is the only documentation source.

---

## Changes

### Section 1: Naming & Duplication Fixes

**1a. Remove duplicated performance table from "What's New in v1.0.0"**

Lines 58–67 contain the full benchmark table. This is identical to the table in the "Performance" section (lines 451–459). Remove the table from "What's New" and replace with a single summary sentence:

> *Parser throughput more than doubled vs the previous release; serializer gains range from +38% to +83%. See [Performance](#-performance).*

**1b. Rename "v2 Baseline" to "v0.5.x baseline"**

In both the "What's New" section header and the "Performance" section table column, rename:
- Section heading: `Performance Gains vs v2 Baseline` → `Performance Gains vs v0.5.x baseline`
- Table column header: `v2 Baseline` → `v0.5.x baseline`

This disambiguates from "v2" used elsewhere to mean TOON spec v2.

**1c. Fix the Performance section intro sentence**

> `v1.0.0 is the fastest release yet, with parser throughput more than doubled vs the v2 baseline:`

→

> `v1.0.0 is the fastest release yet, with parser throughput more than doubled vs the v0.5.x baseline:`

---

### Section 2: Content Removal

**2a. Remove "TOON Format Overview" section (~55 lines)**

Lines 505–559. Shows 7 syntax examples (object, list, tabular, primitive inline, nested, multiline string, comments). The Quick Start already demonstrates the format with a real working example. This section adds no information not already present.

**2b. Remove "Use Cases" section (~10 lines)**

Lines 574–581. Five marketing bullet points. Adds no technical value for either audience type; the intro paragraph already describes what the library is for.

**2c. Collapse "Acknowledgments" to one line (~5 lines saved)**

Lines 608–613. Replace the full block with a single sentence at the bottom of the Author section:

> *Built on [TOON SPEC v3.0](https://github.com/toon-format/spec) · Property-based testing with [Hypothesis](https://hypothesis.readthedocs.io/).*

---

### Section 3: Condense "v3.0 Features in Depth"

**Target:** ~95 lines → ~35 lines

Lines 289–382. Contains 5 subsections: Multiple Delimiters, Primitive Inline Arrays, Key Folding, Path Expansion, Strict Mode.

**Rule for each subsection (except Strict Mode):**
- Keep the `###` header
- Remove the introductory prose paragraph (it re-states what the Features list already says)
- Keep the code block only
- Keep the trailing `---` separator

**Strict Mode subsection:** Keep as-is. It's a bulleted error list that doesn't appear elsewhere and is genuinely useful reference.

---

## Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Total lines | 617 | ~340 |
| Information lost | — | None |
| New files | — | None |
| Structural changes | — | None |

---

## Out of Scope

- No changes to API Reference, CLI Reference, Installation, Quick Start, Features list, Testing, Backward Compatibility, Contributing, or License sections.
- No new files created.
- No `<details>` / collapsible HTML.
