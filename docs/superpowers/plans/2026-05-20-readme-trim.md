# README Trim & Clarity Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce README.md from ~617 lines to ~340 lines by fixing version naming ambiguity, removing duplicate/redundant sections, and condensing verbose subsections — with zero information loss.

**Architecture:** Three sequential edits to `README.md`. Tasks must run in order (1 → 2 → 3) since they all modify the same file. No new files created. No code changes.

**Tech Stack:** Plain text editing only. Verify with `(Get-Content README.md).Count` (PowerShell) or `wc -l README.md` (Bash).

**Spec:** `docs/superpowers/specs/2026-05-20-readme-trim-design.md`

---

### Task 1: Fix Performance Table Naming and Remove Duplicate

**Files:**
- Modify: `README.md` (lines 56–68 and lines 449–476)

This task fixes three things in the performance-related content:
1. Removes the duplicate benchmark table from the "What's New" section and replaces it with a summary sentence
2. Renames the section heading from "Performance Gains vs v2 Baseline" to "Performance Gains vs v0.5.x baseline"
3. Renames "v2 Baseline" → "v0.5.x baseline" in the Performance section (column header + intro sentence)

- [ ] **Step 1: Replace the "What's New" performance subsection**

Open `README.md` and find this block (around line 56):

```
### Performance Gains vs v2 Baseline

| Operation | v1.0.0 | v2 Baseline | Gain |
|-----------|--------|-------------|------|
| Parser — simple object (4 KVs) | 135,924 docs/sec | ~62,500 | **+117%** |
| Parser — tabular array 3×3 | 93,085 docs/sec | ~41,667 | **+123%** |
| Serializer — simple object | 134,248 docs/sec | 97,325 | **+38%** |
| Serializer — with array | 132,248 docs/sec | 72,308 | **+83%** |
| Serializer — with table | 80,033 docs/sec | 46,450 | **+72%** |
| Serializer — complex nested | 56,608 docs/sec | 32,678 | **+73%** |
| Serializer — many booleans | 101,461 docs/sec | 68,481 | **+48%** |
```

Replace with:

```
### Performance Gains vs v0.5.x baseline

Parser throughput more than doubled vs the previous release; serializer gains range from +38% to +83%. See [Performance](#-performance).
```

- [ ] **Step 2: Fix the Performance section intro sentence**

Find this line in the Performance section (around line 449):

```
v1.0.0 is the fastest release yet, with parser throughput more than doubled vs the v2 baseline:
```

Replace with:

```
v1.0.0 is the fastest release yet, with parser throughput more than doubled vs the v0.5.x baseline:
```

- [ ] **Step 3: Rename the column header in the Performance table**

Find this table header line in the Performance section:

```
| Operation | v1.0.0 | v2 Baseline | Improvement |
```

Replace with:

```
| Operation | v1.0.0 | v0.5.x baseline | Improvement |
```

- [ ] **Step 4: Verify**

Run:
```powershell
(Get-Content README.md).Count
```

Expected: around 605 lines (removed ~12 lines from the table).

Also confirm "v2 Baseline" no longer appears anywhere except as `spec="v2"` references:
```powershell
Select-String -Path README.md -Pattern "v2 Baseline"
```
Expected: no matches.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs(readme): fix performance table naming and remove duplicate table"
```

---

### Task 2: Remove Redundant Sections

**Files:**
- Modify: `README.md`

**Important:** Work bottom-to-top within this task so earlier removals don't shift line numbers for later ones.

Remove three sections in this order: Acknowledgments first (bottom of file), then Use Cases, then TOON Format Overview.

- [ ] **Step 1: Collapse Acknowledgments to one line**

Find this block near the bottom of the file:

```
## 🙏 Acknowledgments

- Built following [TOON SPEC v3.0](https://github.com/toon-format/spec)
- Property-based testing with [Hypothesis](https://hypothesis.readthedocs.io/)
- Inspired by the need for efficient, token-optimized data serialization for LLM applications

---
```

Replace with:

```
*Built on [TOON SPEC v3.0](https://github.com/toon-format/spec) · Property-based testing with [Hypothesis](https://hypothesis.readthedocs.io/).*
```

- [ ] **Step 2: Remove the Use Cases section**

Find this block:

```
## 🌟 Use Cases

- **LLM/AI Projects** — token-optimized tabular format reduces prompt size by 30–50%
- **Data serialization** — compact, human-readable alternative to JSON/YAML
- **Configuration files** — comment support, dotted paths, readable structure
- **Data pipelines** — streaming helpers for large files
- **REST APIs** — lightweight format with zero-dependency parser

---
```

Delete it entirely (remove the heading, all bullets, and the trailing `---`).

- [ ] **Step 3: Remove the TOON Format Overview section**

Find this entire block (from the `##` heading through the closing `---`):

```
## 📊 TOON Format Overview

TOON (Token-Oriented Object Notation) is an indentation-based format optimized for token efficiency in LLM applications.

**Key/value object:**
```
name: Luz
age: 16
active: true
```

**Array (list format):**
```
crew[3]:
  - Luz
  - Amity
  - Willow
```

**Tabular array (most compact for uniform objects):**
```
crew[3]{id,name,role}:
  1,Luz,Human
  2,Eda,Witch
  3,King,Titan
```

**Primitive inline array:**
```
tags[3]: python,serialization,toon
```

**Nested object:**
```
ship:
  name: "Owl House"
  location: Bonesborough
```

**Multiline string:**
```
bio: """
  Luz is a human teen from the real world
  who stumbled upon the Boiling Isles.
"""
```

**Comments:**
```
# line comment
// also a line comment
/* block comment */
```

For the full grammar, see [docs/spec_summary.md](docs/spec_summary.md) and the [official TOON spec](https://github.com/toon-format/spec/blob/main/SPEC.md).

---
```

Delete it entirely.

- [ ] **Step 4: Verify**

```powershell
(Get-Content README.md).Count
```

Expected: around 530 lines (removed ~75 lines total across the three sections).

Confirm removed sections are gone:
```powershell
Select-String -Path README.md -Pattern "TOON Format Overview|Use Cases|Acknowledgments"
```
Expected: no matches (or only matches inside other unrelated text — `## 🙏 Acknowledgments` heading gone).

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs(readme): remove redundant Format Overview, Use Cases, and Acknowledgments sections"
```

---

### Task 3: Condense v3.0 Features in Depth

**Files:**
- Modify: `README.md`

Remove the introductory prose sentence from each of four subsections (Multiple Delimiters, Primitive Inline Arrays, Key Folding, Path Expansion). Keep all code blocks, all bullet-point reference lines, and the Strict Mode subsection entirely unchanged.

- [ ] **Step 1: Remove Multiple Delimiters intro sentence**

Find:

```
### Multiple Delimiters

v3 supports comma (default), tab, and pipe as row separators in tabular arrays:

```

Replace with:

```
### Multiple Delimiters

```

Also find and remove the trailing prose line after the code block:

```
Choose via `to_toon(data, delimiter="pipe")` or `from_toon(toon, delimiter="tab")`.

---
```

Replace with:

```
---
```

- [ ] **Step 2: Remove Primitive Inline Arrays intro and trailing sentences**

Find:

```
### Primitive Inline Arrays

Scalar-only arrays can be written on a single line:

```

Replace with:

```
### Primitive Inline Arrays

```

Find and remove the trailing sentence after the code block:

```
The serializer emits this format automatically when all elements are scalars.

---
```

Replace with:

```
---
```

- [ ] **Step 3: Remove Key Folding intro sentence**

Find:

```
### Key Folding (Serializer)

Collapse single-key chains into dotted paths:

```

Replace with:

```
### Key Folding (Serializer)

```

- [ ] **Step 4: Remove Path Expansion intro sentence**

Find:

```
### Path Expansion (Parser)

Expand dotted keys into nested objects:

```

Replace with:

```
### Path Expansion (Parser)

```

- [ ] **Step 5: Verify**

```powershell
(Get-Content README.md).Count
```

Expected: around 340 lines (roughly half the original 617).

Spot-check that Strict Mode subsection is untouched:
```powershell
Select-String -Path README.md -Pattern "Strict Mode" -Context 0,6
```
Expected: heading + bullet list visible, unchanged.

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs(readme): condense v3.0 Features in Depth subsections"
```
