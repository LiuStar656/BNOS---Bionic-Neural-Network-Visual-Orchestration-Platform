# dialog_utils.py pick Functions UnboundLocalError Fix

## Overview

Fixed the `UnboundLocalError: cannot access local variable 'go_up' where it is not associated with a value` error in three dialog functions: `pick_folder`, `pick_file`, and `pick_save_file`. This bug caused crashes when:

- **Opening a project** (File → Open Project)
- **Exporting a node** (Right-click node → Export as `.bnos`)
- **Exporting a project**

---

## Root Cause Analysis

All three pick functions share the same code structure and the same bug pattern:

```python
def pick_folder(parent, title="Choose Folder"):
    # ... initialization ...
    nav_bar, drive_combo, up_btn, _ = _create_nav_bar(
        parent, drives, lambda idx: load_tree(drive_combo.itemData(idx)), go_up
    )                                                         # ↑ references go_up here
    # ... other code ...
    def go_up():                                              # ← go_up defined later
        """Navigate up one level"""
        current_path = os.path.normpath(tree_view.path)
        parent_dir = os.path.dirname(current_path)
        # ...
```

**Problem**: At the line calling `_create_nav_bar(..., go_up)`, the Python parser has already determined that `go_up` is a local variable of this function (because `def go_up()` appears later), but it hasn't been assigned yet — triggering `UnboundLocalError`. This is distinct from `NameError` (global not found); it's a Python forward-reference specific issue.

**Why it wasn't exposed before**:
- Before PyQt6 migration, certain code paths may have avoided calling `go_up` at this point
- Node creation/export features were primarily tested through shortcuts during development, missing these dialog functions

---

## Fix (Applied Uniformly to All Three Functions)

### 1. Move `go_up` Definition Before `_create_nav_bar` Call

```python
# Define go_up (BEFORE _create_nav_bar call)
def go_up():
    current_path = os.path.normpath(tree_view.path)
    parent_dir = os.path.dirname(current_path)
    if parent_dir and parent_dir != current_path:
        tree_view.set_path(parent_dir)

def sel_path():
    current = tree_view.current_item()
    if current and current.get("type") == "folder":
        path = current["full_path"]
    else:
        path = tree_view.path
    return path

# Now call _create_nav_bar — go_up / sel_path are available
nav_bar, drive_combo, up_btn, _ = _create_nav_bar(
    parent, drives, lambda idx: load_tree(drive_combo.itemData(idx)), go_up
)
```

### 2. Remove Duplicate `go_up` / `sel_path` Definitions (Originally at Function Tail)

Prevents double-definition of same-named functions, keeping code clean.

---

## Changed Files

| File | Changes |
|------|---------|
| [ui/core/utils/dialog_utils.py](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/utils/dialog_utils.py) | `pick_folder`: `go_up` / `sel_path` definitions moved before `_create_nav_bar` |
| [ui/core/utils/dialog_utils.py](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/utils/dialog_utils.py) | `pick_file`: `go_up` / `sel_path` definitions moved before `_create_nav_bar` |
| [ui/core/utils/dialog_utils.py](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/utils/dialog_utils.py) | `pick_save_file`: `go_up` / `sel_path` definitions moved before `_create_nav_bar` |

---

## Verification Results

| Operation | Expected | Result |
|-----------|----------|--------|
| `File → Open Project` | Folder selection dialog opens, paths selectable | ✅ Normal |
| Right-click node → Export node | Save dialog opens, target `.bnos` selectable | ✅ Normal |
| `File → Export Project` | Save dialog opens | ✅ Normal |
| Right-click node → Import node | File selection dialog opens, `.bnos` selectable | ✅ Normal |
| Full compilation | No syntax errors | ✅ 169/169 passed |
| Startup test | Main window, Dock, canvas, IPC, terminal normal | ✅ Passed |
