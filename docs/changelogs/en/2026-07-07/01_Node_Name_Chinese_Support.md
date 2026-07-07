# Node Name Chinese Support

## Overview

Node names now support Chinese and other Unicode characters, allowing users to name node folders with more intuitive Chinese names.

## Problem Analysis

Previously, node name validation used regex `^[a-zA-Z0-9_-]+$`, which only allowed letters, numbers, underscores, and hyphens, directly blocking Chinese naming.

After analysis, node names are essentially equivalent to folder names, and all operations ultimately fall onto file paths. Modern Windows file systems fully support Chinese paths, JSON configurations use UTF-8 encoding which fully supports Chinese, and Qt UI also supports Chinese rendering. Therefore, only the name validation rules need to be modified to support Chinese.

## Solution

### Validation Rule Change

**Old Rule**: `^[a-zA-Z0-9_-]+$` — Only letters, numbers, underscores, hyphens

**New Rule**: `^[^\\/:*?"<>|]+$` — Exclude Windows file system reserved characters

### Supported Characters

- ✅ Chinese and other Unicode characters (e.g., Japanese, Korean, special symbols)
- ✅ English, numbers, underscores, hyphens, spaces
- ❌ Forbidden: `\ / : * ? " < > |` (Windows file system reserved characters)
- Length limit: 64 characters

### Unified Validation Architecture

Previously, there were three independent name validation logics that could lead to inconsistencies:
1. `node_list_panel.py` — Rename validation
2. `node_creator_manager.py` — Creation validation
3. `validators.py` — Generic validator

Now all validations use `NodeNameValidator` to ensure consistent rules across all entry points.

## Modified Files

### Core Validation Logic

| File | Change |
|------|--------|
| `ui/core/validators.py` | Updated `ALLOWED_CHARS` regex to `^[^\\/:*?"<>|]+$`, removed redundant checks |

### Validation Entry Unification

| File | Change |
|------|--------|
| `ui/panels/node_list_panel.py` | Rename function now uses `NodeNameValidator.validate()` |
| `ui/creators/node_creator_manager.py` | Creation function now uses `NodeNameValidator.validate()`, removed duplicate empty value check |

### Internationalization Text

| File | Change |
|------|--------|
| `ui/core/strings_cn.json` | Updated error message to reflect new naming rules |
| `ui/core/strings_en.json` | Updated error message to reflect new naming rules |

## Compatibility

- **Windows**: Full Chinese path and file name support
- **Linux/Mac**: Chinese path support depends on system language environment
- **JSON Configuration**: UTF-8 encoding, full Chinese support
- **Qt UI**: Full Chinese rendering support

## Notes

1. Chinese node names on Linux/Mac may require proper system language environment configuration
2. Node names directly become folder names, so file system reserved characters are forbidden
3. Avoid using excessively long node names (64 character limit)
