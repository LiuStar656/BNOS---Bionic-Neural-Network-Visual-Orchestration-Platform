# dialog_utils.py pick 函数 UnboundLocalError 修复

## 概述

修复 `pick_folder`、`pick_file`、`pick_save_file` 三个对话框函数中的 `UnboundLocalError: cannot access local variable 'go_up' where it is not associated with a value` 错误。该 bug 会导致：

- **打开项目**（`File → 打开项目`）时崩溃
- **导出节点**（右键节点 → 导出为 `.bnos`）时崩溃
- **导出项目**时崩溃

---

## 根因分析

三个 pick 函数的代码结构相同，bug 模式一致：

```python
def pick_folder(parent, title="选择文件夹"):
    # ... 初始化 ...
    nav_bar, drive_combo, up_btn, _ = _create_nav_bar(
        parent, drives, lambda idx: load_tree(drive_combo.itemData(idx)), go_up
    )                                                         # ↑ 这里引用 go_up
    # ... 其他代码 ...
    def go_up():                                              # ← go_up 定义在后面
        """返回上一级"""
        current_path = os.path.normpath(tree_view.path)
        parent_dir = os.path.dirname(current_path)
        # ...
```

**问题**：在调用 `_create_nav_bar(..., go_up)` 的那一行，Python 解析器已经确定 `go_up` 是这个函数的局部变量（因为后面有 `def go_up()`），但此时它还没被赋值，于是触发 `UnboundLocalError`。这不是 `NameError`（全局未找到），而是 Python 前向引用的特有问题。

**为什么之前没暴露**：
- PyQt6 迁移前可能存在某种路径（`go_up` 不是每次都被调用）避开了此错误
- 节点创建/导出等功能在开发阶段更多通过快捷方式调用，未覆盖到这些对话框函数

---

## 修复方案（三个函数统一处理）

### 1. 将 `go_up` 的定义移至 `_create_nav_bar` 调用之前

```python
# 定义 go_up（在 _create_nav_bar 调用之前）
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

# 现在才调用 _create_nav_bar，go_up/sel_path 已可用
nav_bar, drive_combo, up_btn, _ = _create_nav_bar(
    parent, drives, lambda idx: load_tree(drive_combo.itemData(idx)), go_up
)
```

### 2. 删除重复的 `go_up` / `sel_path` 定义（原在函数尾部）

避免同名函数的二次定义，保持代码整洁。

---

## 变更文件清单

| 文件 | 修改点 |
|------|--------|
| [ui/core/utils/dialog_utils.py](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/utils/dialog_utils.py) | `pick_folder`（L127-227）：`go_up` / `sel_path` 定义前置 |
| [ui/core/utils/dialog_utils.py](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/utils/dialog_utils.py) | `pick_file`（L400-520）：`go_up` / `sel_path` 定义前置 |
| [ui/core/utils/dialog_utils.py](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/utils/dialog_utils.py) | `pick_save_file`（L540-660）：`go_up` / `sel_path` 定义前置 |

---

## 验证结果

| 操作 | 预期 | 结果 |
|------|------|------|
| `File → 打开项目` | 弹出文件夹选择对话框，可选路径 | ✅ 正常 |
| 右键节点 → 导出节点 | 弹出保存对话框，可选择目标 `.bnos` | ✅ 正常 |
| `File → 导出项目` | 弹出保存对话框 | ✅ 正常 |
| 右键节点 → 导入节点 | 弹出文件选择对话框，可选 `.bnos` | ✅ 正常 |
| 全量编译 | 无语法错误 | ✅ 169/169 通过 |
| 启动测试 | 主窗口、Dock、画布、IPC、终端正常 | ✅ 通过 |
