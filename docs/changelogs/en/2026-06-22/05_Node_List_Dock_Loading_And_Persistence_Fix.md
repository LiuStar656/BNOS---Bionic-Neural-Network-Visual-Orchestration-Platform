# Node List Dock Loading & Persistence Fix

## 1. Problem Overview

- **The Node List Dock panel (`NodeListDockPanel`) appears blank** after startup or when toggled from the menu, even when `main_window.nodes_data` already contains nodes.
- **Floating panel loads correctly while the Dock does not**: both `set_project_path` implementations used to skip `update_node_list` after reloading groups. Some call paths (e.g. `project_open → project_refresh`) only refreshed the Dock version, leaving the floating version stale.
- **Group information (`node_groups.json`) is not persisted**: after the panel is re-created, groups are not reloaded.
- **Potential `AttributeError`**: references to `self.node_list_dock` (the actual attribute is `self.node_list_panel`) were left in code paths.
- **Only the Dock version was refreshed, ignoring `node_list_floating`**: `_apply_after_refresh` inside `project_manager.py` only refreshed the Dock version of the node list panel.

## 2. Root Cause Analysis

### 2.1 `NodeListDockPanel.__init__` tried to update `path_label` before `_init_ui` created it

In the old `NodeListDockPanel.__init__`, code tried to call `path_label.setText(...)` **before** `_init_ui()` was executed, which is the only place where `path_label` is created:

```python
def __init__(self, parent=None):
    ...
    self.group_manager = NodeGroupManager(initial_project)
    # ❌ path_label does not exist yet -> AttributeError if project has nodes
    if initial_project and parent.nodes_data:
        self.nodes_data = dict(parent.nodes_data)
        self.path_label.setText(...)

    self._init_ui()  # path_label is only created here
```

### 2.2 `NodeListDockPanel.set_project_path` only updated the path label, not groups, not the node list UI

```python
def set_project_path(self, path):
    # ❌ Old implementation: only updates the path label
    if path:
        self.path_label.setText(...)
    else:
        self.path_label.setText(...)
```

Even when `update_node_list(nodes_data)` is called elsewhere, `self.group_manager.groups` remains empty and user-arranged groups are lost after restart.

### 2.3 `NodeListPanel.set_project_path` (Floating) also skipped UI refresh

The floating panel initializes with its own `_init_ui` flow, but `set_project_path` only called `group_manager.set_project_path(project_path)` without re-rendering the node list, causing stale group info / empty node list after project switch.

### 2.4 `project_manager._apply_after_refresh` only refreshed the Dock version

```python
def _apply_after_refresh(main_window, running_nodes):
    if main_window.node_list_panel:  # ❌ only the Dock version
        main_window.node_list_panel.set_project_path(...)
        main_window.node_list_panel.update_node_list(...)
```

Similarly, the mounted nodes lock-group UI inside `_on_finished` only updated `node_list_panel`, never adding nodes to the floating panel's groups.

### 2.5 `_refresh_panels` referenced an undefined `self.node_list_dock`

```python
if hasattr(self, 'node_list_dock') and self.node_list_dock:  # ❌ never set
    self.node_list_dock.update_node_list(self.nodes_data)
```

The real attribute on the main window is `self.node_list_panel` (Dock version).

### 2.6 `__main__.py.update_node_status` lacked null reference protection

## 3. Fix Summary

| File | Change |
| --- | --- |
| `ui/panels/node_list_dock.py` | `__init__` reorders initialization so `_init_ui` runs **before** `set_project_path` / `update_node_list`; `set_project_path` now calls `NodeGroupManager.set_project_path` and re-invokes `update_node_list` when nodes are available |
| `ui/panels/node_list_panel.py` | `set_project_path` now calls `NodeGroupManager.set_project_path` and re-invokes `update_node_list`, matching the Dock version |
| `ui/main_window/panel.py` | `_refresh_panels` removed the undefined `self.node_list_dock` reference and calls `set_project_path` before refresh |
| `ui/main_window/__main__.py` | `update_node_status` is now guarded by `hasattr` |
| `ui/core/project_manager.py` | `_apply_after_refresh` and the mounted-node lock-group UI now refresh **both** the Dock version (`node_list_panel`) and the floating version (`node_list_floating`) |

## 4. Verification Steps (manual)

1. Launch BNOS, open a project and organize nodes into groups (drag & drop).
2. Restart BNOS → groups should still appear.
3. Toggle `View → Node List` → panel is populated, never blank.
4. Invoke **Refresh Nodes** / switch to a different project → node list and groups are refreshed together.
5. Open both the floating panel and the Dock panel at the same time → both should stay in sync and show the same nodes / groups.
