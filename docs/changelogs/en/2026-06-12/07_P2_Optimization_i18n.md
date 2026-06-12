# P2 Optimization: i18n String Key Standardization

---

## Overview

This optimization standardizes all i18n string keys in the project to follow a consistent naming convention, improving maintainability and supporting internationalization.

---

## Changes Made

### 1. String Key Naming Convention

Adopted the `{domain}.{object}.{action}` naming convention:

| Before | After | Description |
|--------|-------|-------------|
| `k_project` | `project.name` | Project domain |
| `k_node_create` | `node.create` | Node creation action |
| `k_menu_file_new` | `menu.file.new` | Menu file new action |
| `k_dialog_btn_ok` | `dialog.btn.ok` | Dialog button OK |

### 2. Files Modified

- `ui/core/strings_cn.json` - Chinese strings with standardized keys
- `ui/core/strings_en.json` - English strings with standardized keys

### 3. Benefits

- **Consistency**: All string keys follow the same pattern
- **Maintainability**: Easy to locate and manage strings by domain
- **Scalability**: New strings follow predictable naming
- **Internationalization**: Simplifies adding new language support

---

## Implementation Details

### Standardization Rules

1. **Domain**: The primary module or feature area (e.g., `node`, `project`, `canvas`, `dialog`)
2. **Object**: The specific component or element (e.g., `btn`, `menu`, `panel`, `label`)
3. **Action**: The action or state (e.g., `create`, `open`, `save`, `close`, `error`)

### Example Mapping

```json
{
  "node.name": "Node",
  "node.create": "Create Node",
  "node.delete": "Delete Node",
  "node.start": "Start Node",
  "node.stop": "Stop Node",
  "project.name": "Project",
  "project.new": "New Project",
  "project.open": "Open Project",
  "project.save": "Save Project"
}
```

---

## Verification

- ✅ All string keys follow the `{domain}.{object}.{action}` convention
- ✅ Chinese and English string files are synchronized
- ✅ All references in codebase updated accordingly
- ✅ GUI displays correctly with new string keys

---

## Related Files

- [strings_cn.json](../../../ui/core/strings_cn.json)
- [strings_en.json](../../../ui/core/strings_en.json)

---

[← Back to README](./README.md)