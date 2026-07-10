# 项目文件锁与 Bug 修复

## 更新概述

引入项目级文件锁防止多个 BNOS 实例同时打开同一项目导致数据损坏；修复了开发过程中暴露的多个运行时 Bug。

## 核心改动

### 1. 项目文件锁

修改 `ui/core/project_manager.py`：

- **写入锁文件**：打开项目时在项目根目录写入 `.bnos_project.lock`，包含 PID 和时间戳
- **PID 存活检测**：`_is_pid_alive()` 通过 Windows API `OpenProcess` + `GetExitCodeProcess` 双重确认进程是否真正运行中
- **过期锁清理**：`remove_project_lock()` 在关闭项目时清理锁文件
- **冲突提示**：检测到锁时弹出提示"项目正被另一个 BNOS 实例(PID:xxxxx)打开"

修改 `ui/core/canvas_host.py`：

- `remove_canvas_dock_by_path()` 关闭画布时自动清理锁文件

### 2. Bug 修复

#### GROUP_PREFIX AttributeError
- **文件**：`ui/core/composite_node.py`
- **根因**：模块级常量 `GROUP_PREFIX` / `GROUP_COLOR` 未提升为类属性，其他模块通过 `CompositeNode.GROUP_PREFIX` 访问 → `AttributeError`
- **修复**：将两个常量设为 `CompositeNode` 类属性

#### blockSignals 未恢复导致双击/右键失效
- **文件**：`ui/panels/node_list_dock.py`
- **根因**：`update_node_list` 中 `blockSignals(True)` 阻断信号后未恢复为 `False`
- **修复**：树构建完成后加 `blockSignals(False)` 恢复

#### clear_box_selection 方法名错误
- **文件**：`ui/canvas/mixins/canvas_batch_ops.py`
- **根因**：4 处调用 `clear_box_selection()`，实际方法名为 `clear_selection()`
- **修复**：统一改为 `clear_selection()`

#### node_list_context UnboundLocalError
- **文件**：`ui/panels/node_list_context.py`
- **根因**：`CompositeNode` 懒导入在 `if not mgr:` 分支内，三个解耦/启动/停止方法在分支外使用
- **修复**：提升为模块级导入

#### status_manager C++ 对象已删除 RuntimeError
- **文件**：`ui/canvas/items/node_components/status_manager.py`
- **根因**：节点删除后资源监测信号仍触发，`QGraphicsTextItem` C++ 对象已销毁
- **修复**：`_on_status_updated` 增加 `scene() is None` 存活检查

#### app_config 类型校验破坏 last_project
- **文件**：`ui/core/app_config.py`
- **根因**：S16 类型校验中 `None` 哨兵值拒绝后续写入的 `str` 类型
- **修复**：`None` 哨兵跳过类型校验
