# 07 Composite Node Rename Feature

## Problem Description

Composite nodes only displayed hex IDs in the node list, with no custom display name or rename functionality.

## Fix Solution

### 7.1 Add Rename Option in Context Menu

**File**: `ui/panels/node_list_context.py`

Added "Rename Composite Node" option in composite node context menu.

**Code Change**:
```python
rename_action = menu.addAction("重命名复合节点")
rename_action.triggered.connect(lambda: self._rename_composite_group(group_name))
```

### 7.2 New Rename Method

**File**: `ui/panels/node_list_context.py`

Added `_rename_composite_group()` method:
1. Running state protection: Running composite nodes cannot be renamed
2. Edit `display_name` via input dialog
3. Empty restores hex ID display
4. Refresh node list

**Code Change**:
```python
def _rename_composite_group(self, group_name):
    comp_id = group_name[len(CompositeNode.GROUP_PREFIX):]
    if mgr.is_running(comp_id):
        parent.show_toast("复合节点正在运行中，请先停止后再重命名", "warning")
        return
    current_name = mgr._composites.get(comp_id, {}).get("display_name", "")
    new_name = themed_input(self, "重命名复合节点", "...", current_name)
    if new_name is None:
        return
    mgr.rename(comp_id, new_name)
    self.update_node_list(self.nodes_data)
```

## Modified Files

| File | Change |
|------|--------|
| `ui/panels/node_list_context.py` | Added `_rename_composite_group()`; rename option in context menu |

## Verification

After fix:
- ✅ Context menu supports renaming composite nodes
- ✅ Running composite nodes cannot be renamed
- ✅ Custom display name editable, empty restores hex ID
- ✅ Node list auto-refreshes after rename

---

**Last Updated**: 2026-07-13
