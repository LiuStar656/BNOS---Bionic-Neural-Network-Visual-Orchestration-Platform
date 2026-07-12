# 09 Composite Node Dialog Style Unification

## Overview

Replaced 6 `QMessageBox` calls in composite node code with `themed_message()`, unifying dialog styling. Resolved the visual disconnect of native Windows white dialogs in BNOS's dark theme.

---

## I. Problem

Composite node confirm/error dialogs used `QMessageBox.question()` / `QMessageBox.warning()` directly, invoking native Windows white system dialogs that clash with BNOS's dark rounded borderless style.

---

## II. Changes

| File | Location | Before | After |
|------|------|--------|--------|
| `composite_node_item.py` | `_decompress` confirm | `QMessageBox.question(...)` | `themed_message(..., "question")` |
| Same | `_decompress` fail | `QMessageBox.warning(...)` | `themed_message(..., "error")` |
| Same | `_start` fail | `QMessageBox.warning(...)` | `themed_message(..., "error")` |
| `composite_node.py` | Collapse blocked | `QMessageBox.warning(...)` | `themed_message(..., "warning")` |
| Same | Env creation fail | `QMessageBox.warning(...)` | `themed_message(..., "error")` |
| `canvas_menus.py` | Launch fail | `QMessageBox.warning(...)` | `themed_message(..., "error")` |

---

## III. Visual Comparison

```
Before (QMessageBox):            After (themed_message):
┌─────────────────────┐        ┌───────────────────────┐
│  ❌ (Windows native) │        │  Confirm Decompression │
│  Restore to 3...?   │        │  Restore to 3 nodes?   │
│  [Yes]  [No]        │        │  [No]    [Yes]         │
│  ← White system →    │        │  ← Dark/round/tint →   │
└─────────────────────┘        └───────────────────────┘
```

Also reused existing i18n standard keys (`k_title_error`, `k_composite_decompress_confirm_title`, etc.), ensuring consistent CN/EN modes.
