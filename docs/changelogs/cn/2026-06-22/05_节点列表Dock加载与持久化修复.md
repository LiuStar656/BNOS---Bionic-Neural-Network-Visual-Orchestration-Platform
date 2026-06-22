# 节点列表 Dock 面板加载与持久化修复

## 一、问题概述

- **节点列表 Dock 面板 (`NodeListDockPanel`) 在启动后 / 切换打开后显示为空**，即便 `main_window.nodes_data` 中已经存在节点数据。
- **浮动面板正常加载，而 Dock 版不能**：两者的 `set_project_path` 都没有在加载分组后调用 `update_node_list` 刷新 UI，但浮动版因为其他更新路径（如 `toggle_node_list_panel`）被覆盖到，而 Dock 版在某些流程（如 project_open → project_refresh）中不会显式触发完整刷新。
- **分组信息（node_groups.json）无法持久化**：当面板被重新创建时，分组没有被重新加载。
- **潜在的空引用错误**：代码中仍残留对 `self.node_list_dock` 的引用（实际属性为 `self.node_list_panel`），在特定调用路径会导致 `AttributeError`。
- **仅更新 Dock 版，浮动版未同步**：project_manager.py 中的 `_apply_after_refresh` 只更新了 `node_list_panel`，没有考虑 `node_list_floating` 的同步。

## 二、根因分析

### 1. `NodeListDockPanel.__init__` 调用 `_init_ui` 之前，尝试修改还未存在的 `path_label`

在旧版的 `NodeListDockPanel.__init__` 中，直接在 `_init_ui` 调用前设置 `path_label.setText(...)`，但 `path_label` 仅在 `_init_ui` 中创建。**当项目存在节点时**：

```python
def __init__(self, parent=None):
    ...
    self.group_manager = NodeGroupManager(initial_project)
    # ❌ path_label 还未被创建，这里会 AttributeError
    if initial_project and parent.nodes_data:
        self.nodes_data = dict(parent.nodes_data)
        self.path_label.setText(...)  # ❌ path_label 还不存在

    self._init_ui()  # path_label 在这里才被创建
```

后果：创建面板时直接崩溃，Dock 面板不显示任何内容。

### 2. `NodeListDockPanel.set_project_path` 只更新了路径标签，未同步分组，也未刷新节点列表 UI

在 `ui/panels/node_list_dock.py` 中，`set_project_path` 原本只负责刷新顶部的项目路径标签，并没有调用 `NodeGroupManager.set_project_path`，也没有调用 `update_node_list` 重新渲染节点列表。

```python
def set_project_path(self, path):
    # ❌ 旧实现：只更新路径标签，分组永远不会被加载，也不会刷新节点
    if path:
        self.path_label.setText(...)
    else:
        self.path_label.setText(...)
```

即便 `update_node_list(nodes_data)` 在其他地方被调用，`self.group_manager.groups` 也会一直为空，用户之前组织的分组重启后丢失。

### 3. `NodeListPanel.set_project_path`（浮动版）同样没有刷新节点列表 UI

浮动版虽然在创建面板时有独立的初始化逻辑，但切换项目后同样只调用了 `group_manager.set_project_path(project_path)`，没有再次调用 `update_node_list`，导致分组信息不刷新，且当前项目的节点列表显示为空。

### 4. `project_manager._apply_after_refresh` 仅刷新 Dock 版，忽略了 `node_list_floating`

```python
def _apply_after_refresh(main_window, running_nodes):
    if main_window.node_list_panel:  # ❌ 只刷新 Dock 版
        main_window.node_list_panel.set_project_path(...)
        main_window.node_list_panel.update_node_list(...)
```

同样，在 `_on_finished` 中处理挂载节点锁定组 UI 时，也只考虑了 `node_list_panel`，没有将节点加入到浮动版面板的分组中。

### 5. `_refresh_panels` 里残留 `self.node_list_dock` 的未定义属性引用

在 `ui/main_window/panel.py` 中：

```python
if hasattr(self, 'node_list_dock') and self.node_list_dock:  # ❌ 从未被赋值
    self.node_list_dock.update_node_list(self.nodes_data)
```

主窗口上**实际属性名是 `self.node_list_panel`**（Dock 版），`node_list_dock` 从未被赋值，这段逻辑永远不会执行，并且在其他未加 `hasattr` 保护的地方会触发 `AttributeError`。

### 6. `__main__.py.update_node_status` 未做空引用保护

```python
self.node_list_panel.update_node_list(self.nodes_data)  # ❌ 当面板未创建时 AttributeError
```

## 三、修复方案

### 1. `NodeListDockPanel.__init__` 重排初始化顺序

- 先 `_init_ui()`，确保 `path_label` 等控件存在；
- 再从 `parent`（即主窗口）同步 `current_project_path` 和 `nodes_data`；
- 最后 `set_project_path(...)` → `update_node_list(...)`，一次性完成分组加载 + UI 渲染。

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.parent_window = parent
    self.nodes_data = {}
    self.selected_node_ids = []

    from ui.panels.node_group_manager import NodeGroupManager
    initial_project = None
    if parent is not None and hasattr(parent, 'current_project_path'):
        initial_project = parent.current_project_path
    self.group_manager = NodeGroupManager(initial_project)
    self.group_manager.on_changed = lambda: self.update_node_list(self.nodes_data)

    # 先初始化 UI，确保 path_label 等控件存在
    self._init_ui()

    # 若创建时已有项目数据，则填充一次，避免空面板
    initial_nodes = None
    if parent is not None and hasattr(parent, 'nodes_data') and parent.nodes_data:
        initial_nodes = dict(parent.nodes_data)
    if initial_project:
        self.set_project_path(initial_project)
    if initial_nodes:
        self.update_node_list(initial_nodes)

    # 订阅全局节点状态变化
    polling_manager.node_status_changed.connect(self._on_node_status_changed)
```

### 2. `NodeListDockPanel.set_project_path` 同步调用 `group_manager.set_project_path` 并刷新 UI

```python
def set_project_path(self, path):
    """设置项目路径，重新加载分组配置并刷新节点列表 UI"""
    if path:
        self.path_label.setText(f"{t('k_project')}: {os.path.basename(path)}")
    else:
        self.path_label.setText(t("k_node_no_project"))

    if hasattr(self, 'group_manager') and self.group_manager is not None:
        try:
            self.group_manager.set_project_path(path)
        except Exception as e:
            logger.warning("NodeListDockPanel.set_project_path 加载分组失败: %s", e)

    # 关键：在分组加载完成后，如果已有节点数据则刷新 UI
    if self.nodes_data:
        self.update_node_list(self.nodes_data)
```

这样，无论在什么时候调用 `set_project_path`（切换项目、刷新项目、自动打开上次项目等），分组都会被重新加载，持久化生效。

### 3. `NodeListPanel.set_project_path`（浮动版）同样刷新 UI

```python
def set_project_path(self, project_path):
    """设置项目路径，加载节点组配置，并刷新 UI"""
    self.group_manager.set_project_path(project_path)

    if project_path:
        self.path_label.setText(f"项目: {os.path.basename(project_path)}")
    else:
        self.path_label.setText(t("k_node_no_project"))

    if self.nodes_data:
        self.update_node_list(self.nodes_data)
```

### 4. `_apply_after_refresh` 统一刷新 Dock 版与浮动版

```python
def _apply_after_refresh(main_window, running_nodes):
    # 1) 更新节点列表面板（Dock版 + 浮动版）
    if hasattr(main_window, 'node_list_panel') and main_window.node_list_panel:
        main_window.node_list_panel.set_project_path(main_window.current_project_path)
        main_window.node_list_panel.update_node_list(main_window.nodes_data)

    if hasattr(main_window, 'node_list_floating') and main_window.node_list_floating:
        if hasattr(main_window.node_list_floating, 'set_project_path') and main_window.current_project_path:
            main_window.node_list_floating.set_project_path(main_window.current_project_path)
        main_window.node_list_floating.update_node_list(main_window.nodes_data)

    # 2) 画布：同步所有节点的显示状态
    _canvas_call(main_window, 'sync_all_nodes_display')

    # 3) 运行状态刷新
    if running_nodes:
        for name, pid in running_nodes:
            if hasattr(main_window, 'node_list_panel') and main_window.node_list_panel:
                main_window.node_list_panel.update_node_status(name, 'running')
            if hasattr(main_window, 'node_list_floating') and main_window.node_list_floating:
                main_window.node_list_floating.update_node_status(name, 'running')
            _canvas_call(main_window, 'update_node_status', name, 'running')
        main_window.show_toast(f"检测到 {len(running_nodes)} 个节点在后台运行", "info")
    else:
        main_window.show_toast(f"已刷新 {len(main_window.nodes_data)} 个节点", "success")
```

### 5. 挂载节点锁定组 UI 同时更新两个面板

在 `project_open` 和 `project_refresh` 两个流程的 `_on_finished` 中：

```python
for m in mounted_nodes:
    m_mount_root = m['mount_root']
    _panels_to_update = []
    if hasattr(main_window, 'node_list_panel') and main_window.node_list_panel:
        _panels_to_update.append(main_window.node_list_panel)
    if hasattr(main_window, 'node_list_floating') and main_window.node_list_floating:
        _panels_to_update.append(main_window.node_list_floating)
    for panel in _panels_to_update:
        gm = panel.group_manager
        if not gm.groups.get(m_mount_root):
            gm.create_group(m_mount_root, "#E67E22")
        gm.add_nodes_to_group(m_mount_root, [m['name']])
        gm.lock_group(m_mount_root)
```

### 6. 移除 `_refresh_panels` 中未定义的 `self.node_list_dock` 引用

`ui/main_window/panel.py` 的 `_refresh_panels`：

```python
def _refresh_panels(self):
    if hasattr(self, 'node_list_panel') and self.node_list_panel and hasattr(self, 'nodes_data'):
        if hasattr(self, 'current_project_path') and self.current_project_path:
            self.node_list_panel.set_project_path(self.current_project_path)
        self.node_list_panel.update_node_list(self.nodes_data)

    if hasattr(self, 'node_list_floating') and self.node_list_floating and hasattr(self, 'nodes_data'):
        self.node_list_floating.update_node_list(self.nodes_data)
```

### 7. `__main__.update_node_status` 加入 `hasattr` 保护

```python
def update_node_status(self, node_name, status):
    if node_name in self.nodes_data:
        self.nodes_data[node_name]['status'] = status
    if self.canvas:
        self.canvas.sync_node_display(node_name)
    if hasattr(self, 'node_list_panel') and self.node_list_panel:
        self.node_list_panel.update_node_list(self.nodes_data)
```

## 四、影响范围

| 文件 | 变更点 |
| --- | --- |
| `ui/panels/node_list_dock.py` | `__init__` 调整初始化顺序，同步 `current_project_path` / `nodes_data`；`set_project_path` 同步调用 `NodeGroupManager.set_project_path` 并刷新 UI |
| `ui/panels/node_list_panel.py` | `set_project_path` 同步调用 `NodeGroupManager.set_project_path` 并刷新 UI |
| `ui/main_window/panel.py` | `_refresh_panels` 移除 `self.node_list_dock` 空引用并增加 `set_project_path` 调用 |
| `ui/main_window/__main__.py` | `update_node_status` 增加 `hasattr` 保护 |
| `ui/core/project_manager.py` | `_apply_after_refresh` / 挂载节点锁定组 UI 统一更新 Dock 版与浮动版 |

## 五、验证

- **语法检查**：`python _check_syntax.py` 通过（覆盖 node_list_dock.py、node_list_panel.py、panel.py、project_manager.py、state.py、__main__.py、lifecycle.py、bnos_console.py）。
- **功能验证步骤（建议在真实运行环境执行）**：
  1. 启动 BNOS，打开一个项目并在节点列表中组织若干分组（拖入节点）。
  2. 关闭 BNOS 重新启动 → 验证分组仍然存在。
  3. 通过 `视图 → 节点列表` 切换 Dock 开/关 → 验证不会出现空面板。
  4. 使用**刷新节点**/打开新项目 → 验证节点列表与分组同步刷新。
  5. 同时打开浮动版和 Dock 版节点列表 → 验证两者同步刷新，显示一致。
